"""
UDP通信模块
负责与Unity客户端的UDP通信
"""

import json
import socket
import struct
import threading
import time
from typing import Callable, Dict, List, Optional, Any

# Try to import a project-specific logger, fall back to standard logging if unavailable
try:
    from utils.logger import system_logger
except Exception:
    import logging
    system_logger = logging.getLogger("system")
    if not system_logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        handler.setFormatter(formatter)
        system_logger.addHandler(handler)
    system_logger.setLevel(logging.DEBUG)

class UDPDataSender:
    """UDP数据发送器"""
    
    def __init__(self, target_ip: str = "127.0.0.1", target_port: int = 8888):
        """
        初始化UDP发送器
        
        Args:
            target_ip: 目标IP地址
            target_port: 目标端口
        """
        self.target_ip = target_ip
        self.target_port = target_port
        self.socket = None
        self.is_connected = False
        
        # 连接参数
        self.connection_attempts = 0
        self.max_connection_attempts = 3
        self.connection_delay = 1.0
        
        system_logger.info(f"UDPDataSender initialized for {target_ip}:{target_port}")
    
    def connect(self) -> bool:
        """
        建立UDP连接
        
        Returns:
            bool: 连接是否成功
        """
        try:
            if self.is_connected:
                system_logger.warning("Already connected to UDP target")
                return True
            
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.settimeout(5.0)  # 5秒超时
            
            # 测试连接
            test_data = json.dumps({"type": "connection_test", "timestamp": time.time()})
            self.socket.sendto(test_data.encode('utf-8'), (self.target_ip, self.target_port))
            
            self.is_connected = True
            self.connection_attempts = 0
            system_logger.info(f"Connected to UDP target {self.target_ip}:{self.target_port}")
            
            return True
            
        except Exception as e:
            system_logger.error(f"Failed to connect to UDP target: {e}")
            self.connection_attempts += 1
            
            if self.connection_attempts < self.max_connection_attempts:
                system_logger.info(f"Retrying connection in {self.connection_delay} seconds...")
                time.sleep(self.connection_delay)
                return self.connect()
            
            return False
    
    def send_data(self, data: Dict[str, Any]) -> bool:
        """
        发送数据（增强版：防自杀）
        """
        # 尝试自动重连（如果socket丢失）
        if not self.socket:
            system_logger.warning("Socket not initialized, attempting to reconnect...")
            if not self.connect():
                return False
        
        try:
            # 1. 准备数据
            data['timestamp'] = time.time()
            data['server_timestamp'] = data.get('timestamp', time.time())
            
            json_data = json.dumps(data)
            data_bytes = json_data.encode('utf-8')
            
            # 2. 检查包大小
            if len(data_bytes) > 65000:
                system_logger.warning(f"Data packet too large ({len(data_bytes)} bytes), splitting...")
                return self._send_large_data(data)
            
            # 3. 发送数据
            self.socket.sendto(data_bytes, (self.target_ip, self.target_port)) # type: ignore
            return True
            
        except ConnectionResetError:
            # [关键修复] Windows特有错误 (10054)
            # 当客户端(Unity)没启动或重启时，OS会报这个错。
            # 这不代表socket坏了，只代表"刚才那个包没送达"。
            # 我们绝对不能因此把 is_connected 设为 False！
            # system_logger.debug("Client not ready (ConnectionReset), keeping connection alive.")
            return False
            
        except Exception as e:
            # 对于其他错误，记录日志，但尽量不要杀死连接，除非是致命错误
            system_logger.error(f"Failed to send data: {e}")
            # self.is_connected = False  <-- [务必删除或注释掉这一行]
            return False
    
    def _send_large_data(self, data: Dict[str, Any]) -> bool:
        """
        发送大数据包（分块发送）
        
        Args:
            data: 要发送的数据
            
        Returns:
            bool: 发送是否成功
        """
        try:
            # 将大数组转换为字符串表示（压缩）
            if 'eeg_data' in data and len(data['eeg_data']) > 100:
                # 只发送最近100个样本
                data['eeg_data'] = data['eeg_data'][-100:]
                system_logger.debug("Truncated EEG data to fit UDP packet size")
            
            json_data = json.dumps(data)
            data_bytes = json_data.encode('utf-8')
            
            if len(data_bytes) <= 65000:
                sent_bytes = self.socket.sendto(data_bytes, (self.target_ip, self.target_port)) # type: ignore
                return sent_bytes > 0
            else:
                # 进一步缩减数据
                if 'eeg_data' in data:
                    data['eeg_data'] = data['eeg_data'][-50:]  # 只保留50个样本
                    json_data = json.dumps(data)
                    data_bytes = json_data.encode('utf-8')
                    
                    if len(data_bytes) <= 65000:
                        sent_bytes = self.socket.sendto(data_bytes, (self.target_ip, self.target_port)) # type: ignore
                        return sent_bytes > 0
            
            system_logger.error("Failed to reduce data size for UDP transmission")
            return False
            
        except Exception as e:
            system_logger.error(f"Error sending large data: {e}")
            return False
    
    def send_eeg_data(self, eeg_data: List[List[float]], 
                     features: Optional[Dict] = None,
                     metadata: Optional[Dict] = None) -> bool:
        """
        发送EEG数据
        
        Args:
            eeg_data: EEG数据，形状为 (n_samples, n_channels)
            features: 特征数据
            metadata: 元数据
            
        Returns:
            bool: 发送是否成功
        """
        data = {
            'type': 'eeg_data',
            'eeg_data': eeg_data,
            'sample_count': len(eeg_data),
            'channel_count': len(eeg_data[0]) if eeg_data else 0
        }
        
        if features:
            data['features'] = features
        
        if metadata:
            data['metadata'] = metadata
        
        return self.send_data(data)
    
    def send_features_only(self, features: Dict, metadata: Optional[Dict] = None) -> bool:
        """
        只发送特征数据（更轻量级）
        
        Args:
            features: 特征数据
            metadata: 元数据
            
        Returns:
            bool: 发送是否成功
        """
        data = {
            'type': 'eeg_features',
            'features': features,
            'timestamp': time.time()
        }
        
        if metadata:
            data['metadata'] = metadata
        
        return self.send_data(data)
    
    def send_status(self, status: str, message: str = "") -> bool:
        """
        发送状态信息
        
        Args:
            status: 状态 ('connected', 'disconnected', 'error', 'info')
            message: 状态消息
            
        Returns:
            bool: 发送是否成功
        """
        data = {
            'type': 'status',
            'status': status,
            'message': message,
            'timestamp': time.time()
        }
        
        return self.send_data(data)
    
    def disconnect(self):
        """断开连接"""
        if self.socket:
            self.socket.close()
            self.socket = None
        
        self.is_connected = False
        system_logger.info("UDP connection closed")

class UDPDataReceiver:
    """UDP数据接收器"""
    
    def __init__(self, listen_ip: str = "127.0.0.1", listen_port: int = 9999):
        """
        初始化UDP接收器
        
        Args:
            listen_ip: 监听IP地址
            listen_port: 监听端口
        """
        self.listen_ip = listen_ip
        self.listen_port = listen_port
        self.socket = None
        self.is_listening = False
        
        # 数据处理回调
        self.data_callback: Optional[Callable] = None
        self.status_callback: Optional[Callable] = None
        
        # 接收线程
        self.receive_thread = None
        self.stop_event = threading.Event()
        
        system_logger.info(f"UDPDataReceiver initialized for {listen_ip}:{listen_port}")
    
    def start_listening(self, data_callback: Callable[[Dict], None], 
                       status_callback: Optional[Callable[[str, str], None]] = None):
        """
        开始监听
        
        Args:
            data_callback: 数据接收回调函数
            status_callback: 状态接收回调函数
        """
        if self.is_listening:
            system_logger.warning("Already listening for UDP data")
            return
        
        self.data_callback = data_callback
        self.status_callback = status_callback
        
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.listen_ip, self.listen_port))
            self.socket.settimeout(1.0)  # 1秒超时用于检查停止事件
            
            self.is_listening = True
            self.stop_event.clear()
            
            # 启动接收线程
            self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.receive_thread.start()
            
            system_logger.info(f"Started listening for UDP data on {self.listen_ip}:{self.listen_port}")
            
        except Exception as e:
            system_logger.error(f"Failed to start UDP listening: {e}")
            self.is_listening = False
    
    def _receive_loop(self):
        """接收数据的主循环"""
        while not self.stop_event.is_set() and self.is_listening:
            try:
                # 接收数据
                data, address = self.socket.recvfrom(65507)  # type: ignore # 最大UDP包大小
                
                try:
                    # 解析JSON数据
                    json_str = data.decode('utf-8')
                    data_dict = json.loads(json_str)
                    
                    # 处理数据
                    self._process_received_data(data_dict)
                    
                except json.JSONDecodeError as e:
                    system_logger.error(f"Failed to decode JSON data: {e}")
                except Exception as e:
                    system_logger.error(f"Error processing received data: {e}")
                    
            except socket.timeout:
                # 超时，继续循环
                continue
            except Exception as e:
                if not self.stop_event.is_set():
                    system_logger.error(f"Error receiving UDP data: {e}")
                break
        
        system_logger.debug("UDP receive loop ended")
    
    def _process_received_data(self, data: Dict):
        """处理接收到的数据"""
        try:
            data_type = data.get('type', 'unknown')
            
            if data_type == 'status':
                status = data.get('status', '')
                message = data.get('message', '')
                
                if self.status_callback:
                    self.status_callback(status, message)
                    
                system_logger.info(f"Received status: {status} - {message}")
            
            elif data_type == 'eeg_data' or data_type == 'eeg_features':
                if self.data_callback:
                    self.data_callback(data)
                    
            else:
                system_logger.debug(f"Received unknown data type: {data_type}")
                
        except Exception as e:
            system_logger.error(f"Error processing received data: {e}")
    
    def stop_listening(self):
        """停止监听"""
        if not self.is_listening:
            return
        
        self.is_listening = False
        self.stop_event.set()
        
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        
        if self.receive_thread:
            self.receive_thread.join(timeout=2.0)
        
        system_logger.info("Stopped listening for UDP data")
    
    def get_stats(self) -> Dict:
        """获取接收统计信息"""
        return {
            'is_listening': self.is_listening,
            'listen_ip': self.listen_ip,
            'listen_port': self.listen_port,
            'socket_active': self.socket is not None and self.is_listening
        }

class UDPServer:
    """UDP服务器 - 整合发送和接收功能"""
    
    def __init__(self, config: Dict):
        """
        初始化UDP服务器
        
        Args:
            config: 配置字典
        """
        udp_config = config.get('udp', {})
        
        self.server_ip = udp_config.get('server_ip', '127.0.0.1')
        self.server_port = udp_config.get('server_port', 9999)
        self.client_ip = udp_config.get('client_ip', '127.0.0.1')
        self.client_port = udp_config.get('client_port', 8888)
        
        # 初始化发送器和接收器
        self.sender = UDPDataSender(self.client_ip, self.client_port)
        self.receiver = UDPDataReceiver(self.server_ip, self.server_port)
        
        system_logger.info("UDPServer initialized")
        system_logger.debug(f"UDPServer config: {config}")

    def connect_client(self) -> bool:
        """连接到客户端"""
        system_logger.debug("UDPServer.connect_client() called")
        result = self.sender.connect()
        system_logger.debug(f"UDPServer.connect_client result: {result}")
        return result
    
    def start_receiving(self, data_callback: Callable[[Dict], None]):
        """开始接收客户端数据"""
        self.receiver.start_listening(data_callback)
    
    def stop_receiving(self):
        """停止接收"""
        self.receiver.stop_listening()
    
    def send_data(self, data: Dict) -> bool:
        system_logger.debug(f"UDPServer.send_data payload size: {len(str(data))}")
        """发送数据到客户端"""
        return self.sender.send_data(data)
    
    def send_eeg_data(self, eeg_data: List[List[float]], 
                     features: Optional[Dict] = None,
                     metadata: Optional[Dict] = None) -> bool:
        """发送EEG数据"""
        system_logger.debug(f"UDPServer.send_eeg_data samples: {len(eeg_data)} features_present: {features is not None}")
        return self.sender.send_eeg_data(eeg_data, features, metadata)
    
    def send_status(self, status: str, message: str = "") -> bool:
        """发送状态信息"""
        system_logger.debug(f"UDPServer.send_status status={status} message={message}")
        return self.sender.send_status(status, message)
    
    def disconnect(self):
        system_logger.debug("UDPServer.disconnect() called")
        """断开所有连接"""
        self.receiver.stop_listening()
        self.sender.disconnect()
        system_logger.info("UDP server disconnected")
    
    def get_stats(self) -> Dict:
        """获取服务器统计信息"""
        return {
            'server': self.receiver.get_stats(),
            'client_connection': self.sender.is_connected,
            'configuration': {
                'server_address': f"{self.server_ip}:{self.server_port}",
                'client_address': f"{self.client_ip}:{self.client_port}"
            }
        }