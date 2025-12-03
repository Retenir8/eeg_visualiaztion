"""
脑机接口系统 - Python服务端主程序
整合所有模块，提供完整的EEG数据采集、处理和传输功能
"""

import os
import sys
import yaml
import time
import threading
import signal
import numpy as np
from typing import Dict, Optional

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# 导入自定义模块
from utils.logger import system_logger, Logger
from data_acquisition.openbci_interface import OpenBCIInterface
from signal_processing.preprocessor import EEGPreprocessor
from signal_processing.feature_extractor import RealTimeFeatureExtractor
from communication.unity_connector import UDPServer
from communication.data_serializer import RealTimeDataBuffer


class BrainComputerSystem:
    """脑机接口系统主类"""
    
    def __init__(self, config_path: str = "config/settings.yaml"):
        """
        初始化脑机接口系统
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.config = {}
        
        # 系统状态
        self.is_running = False
        self.is_initialized = False
        
        # 组件
        self.openbci_interface: Optional[OpenBCIInterface] = None
        self.preprocessor: Optional[EEGPreprocessor] = None
        self.feature_extractor: Optional[RealTimeFeatureExtractor] = None
        self.udp_server: Optional[UDPServer] = None
        self.data_buffer: Optional[RealTimeDataBuffer] = None
        
        # 线程
        self.processing_thread = None
        self.status_thread = None
        
        # 信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        system_logger.info("BrainComputerSystem initialized")
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        system_logger.info(f"Received signal {signum}, shutting down...")
        self.shutdown()
        sys.exit(0)
    
    def load_config(self) -> bool:
        """
        加载配置文件
        
        Returns:
            bool: 加载是否成功
        """
        try:
            if not os.path.exists(self.config_path):
                system_logger.error(f"Config file not found: {self.config_path}")
                return False
            
            with open(self.config_path, 'r', encoding='utf-8') as file:
                self.config = yaml.safe_load(file)
            
            system_logger.info("Configuration loaded successfully")
            return True
            
        except Exception as e:
            system_logger.error(f"Error loading configuration: {e}")
            return False
    
    def initialize_components(self) -> bool:
        """
        初始化系统组件
        
        Returns:
            bool: 初始化是否成功
        """
        try:
            # 获取配置参数
            openbci_config = self.config.get('openbci', {})
            sample_rate = openbci_config.get('sample_rate', 250)
            num_channels = openbci_config.get('num_channels', 8)
            
            # 获取通信配置
            comm_config = self.config.get('communication', {})
            data_rate = comm_config.get('data_rate', 30)
            
            # 计算合理的缓冲区大小：根据采样率和发送频率
            # 例如：250 Hz 采样, 30 Hz 发送 => 缓冲区 = 250/30 ≈ 8-9 样本
            buffer_size = max(8, int(sample_rate / data_rate))
            
            system_logger.info(f"Calculated buffer_size: {buffer_size} (sample_rate={sample_rate}, data_rate={data_rate})")
            
            # 初始化数据缓冲区
            self.data_buffer = RealTimeDataBuffer(data_rate, buffer_size)
            
            # 初始化OpenBCI接口
            self.openbci_interface = OpenBCIInterface(openbci_config)
            
            # 初始化信号预处理器
            self.preprocessor = EEGPreprocessor(sample_rate)
            
            # 初始化特征提取器
            feature_config = self.config.get('signal_processing', {}).get('feature_extraction', {})
            feature_window_size = feature_config.get('window_size', 256)
            self.feature_extractor = RealTimeFeatureExtractor(sample_rate, feature_window_size)
            
            # 初始化UDP服务器
            self.udp_server = UDPServer(self.config)
            
            self.is_initialized = True
            system_logger.info("All components initialized successfully")
            return True
            
        except Exception as e:
            system_logger.error(f"Error initializing components: {e}")
            return False
    
    def connect_hardware(self) -> bool:
        """
        连接硬件设备
        
        Returns:
            bool: 连接是否成功
        """
        try:
            if not self.is_initialized:
                system_logger.error("Components not initialized")
                return False
            
            # 连接OpenBCI设备
            system_logger.info("Connecting to OpenBCI device...")
            success = self.openbci_interface.connect() # pyright: ignore[reportOptionalMemberAccess]
            
            if success:
                system_logger.info("OpenBCI device connected successfully")
            else:
                system_logger.error("Failed to connect to OpenBCI device")
            
            return success
            
        except Exception as e:
            system_logger.error(f"Error connecting hardware: {e}")
            return False
    
    def start_data_acquisition(self) -> bool:
        """
        开始数据采集
        
        Returns:
            bool: 启动是否成功
        """
        try:
            if not self.openbci_interface or not self.openbci_interface.is_connected:
                system_logger.error("OpenBCI device not connected")
                return False
            
            # 开始数据采集
            self.openbci_interface.start_acquisition()
            system_logger.info("Data acquisition started")
            
            return True
            
        except Exception as e:
            system_logger.error(f"Error starting data acquisition: {e}")
            return False
    
    def start_communication(self) -> bool:
        """
        开始通信
        
        Returns:
            bool: 启动是否成功
        """
        try:
            # 连接客户端
            client_connected = self.udp_server.connect_client() # pyright: ignore[reportOptionalMemberAccess]
            
            if not client_connected:
                system_logger.warning("Could not connect to Unity client, but continuing...")
            else:
                system_logger.info("Connected to Unity client")
            
            # 开始接收客户端消息
            self.udp_server.start_receiving(self._handle_client_message) # pyright: ignore[reportOptionalMemberAccess]
            
            # 发送连接状态
            self.udp_server.send_status("server_connected", "Brain Computer System server is running") # pyright: ignore[reportOptionalMemberAccess]
            
            return True
            
        except Exception as e:
            system_logger.error(f"Error starting communication: {e}")
            return False
    
    def start_processing_threads(self):
        """启动处理线程"""
        try:
            # 启动数据处理线程
            self.processing_thread = threading.Thread(target=self._data_processing_loop, daemon=True)
            self.processing_thread.start()
            
            # 启动状态监控线程
            self.status_thread = threading.Thread(target=self._status_monitoring_loop, daemon=True)
            self.status_thread.start()
            
            system_logger.info("Processing threads started")
            
        except Exception as e:
            system_logger.error(f"Error starting processing threads: {e}")
    
    def _data_processing_loop(self):
        """数据处理主循环"""
        system_logger.info("_data_processing_loop started - sending 8-channel EEG data to Unity")
        
        loop_counter = 0
        last_log_time = time.time()
        
        while self.is_running:
            try:
                loop_counter += 1
                current_time = time.time()
                
                # 每5秒打印一次状态，避免日志过多
                if current_time - last_log_time >= 5.0:
                    system_logger.debug(f"_data_processing_loop: loop_counter={loop_counter}, buffer_stats={self.data_buffer.get_stats() if self.data_buffer else 'N/A'}")
                    last_log_time = current_time
                
                # 获取最新的EEG数据
                latest_data = self.openbci_interface.get_latest_data(32)  # pyright: ignore[reportOptionalMemberAccess]
                
                if latest_data is not None and len(latest_data) > 0:
                    # 对每个样本进行处理
                    for sample in latest_data:
                        timestamp = time.time()
                        
                        # 预处理数据
                        if self.preprocessor:
                            sample_array = np.array(sample).reshape(1, -1)
                            filtered_sample = self.preprocessor.apply_all_filters(sample_array)[0]
                        else:
                            filtered_sample = sample
                        
                        # 提取特征
                        features = None
                        if self.feature_extractor:
                            extracted_features = self.feature_extractor.process_sample(
                                filtered_sample.tolist(), timestamp
                            )
                            if extracted_features:
                                features = extracted_features
                        
                        # 添加到数据缓冲区
                        if self.data_buffer:
                            self.data_buffer.add_sample(filtered_sample.tolist(), timestamp, features)
                    
                    # 在处理完所有样本后，检查是否应该发送
                    if self.data_buffer and getattr(self.data_buffer, "should_send_data", lambda: False)():
                        eeg_data, features_data = self.data_buffer.get_data_for_transmission()
                        
                        if eeg_data is not None:
                            # 发送数据到Unity客户端
                            metadata = {
                                'processing_timestamp': time.time(),
                                'sample_count': len(eeg_data),
                                'channel_count': eeg_data.shape[1]
                            }
                            try:
                                # 检查数据格式
                                system_logger.info(f"准备发送数据: shape={eeg_data.shape}, "
                                                    f"type={type(eeg_data)}, "
                                                    f"first_sample={eeg_data[0].tolist()}")
                                sent = self.udp_server.send_eeg_data(eeg_data.tolist(), features_data, metadata) # pyright: ignore[reportOptionalMemberAccess, reportArgumentType]
                                if sent:
                                    # 更新缓冲区的发送时间
                                    self.data_buffer.last_send_time = time.time()
                                    system_logger.info(f"[EEG_SEND] Sent {len(eeg_data)} samples x {eeg_data.shape[1]} channels to Unity")
                                else:
                                    system_logger.warning("Failed to send EEG data to client")
                            except Exception as e:
                                system_logger.error(f"Error sending EEG data: {e}")
                
                # 短暂休眠
                time.sleep(0.01)  # 10ms
                
            except Exception as e:
                system_logger.error(f"Error in data processing loop: {e}")
                time.sleep(0.1)
    
    def _status_monitoring_loop(self):
        """状态监控循环"""
        system_logger.info("Starting status monitoring loop")
        
        while self.is_running:
            try:
                # 获取系统状态
                status_info = self._get_system_status()
                
                # 发送状态信息
                if self.udp_server:
                    self.udp_server.send_status("system_status", str(status_info))
                
                # 等待一段时间
                time.sleep(5.0)  # 每5秒发送一次状态
                
            except Exception as e:
                system_logger.error(f"Error in status monitoring loop: {e}")
                time.sleep(1.0)
    
    def _handle_client_message(self, message: Dict):
        """处理来自Unity客户端的消息"""
        try:
            system_logger.debug(f"_handle_client_message received: {message}")
            message_type = message.get('type', 'unknown')
            
            if message_type == 'request_data':
                # 客户端请求数据，发送最新的数据
                eeg_data = self.openbci_interface.get_latest_data(64) # pyright: ignore[reportOptionalMemberAccess]
                if eeg_data is not None:
                    self.udp_server.send_eeg_data(eeg_data.tolist()) # pyright: ignore[reportOptionalMemberAccess, reportArgumentType]
            
            elif message_type == 'ping':
                # 客户端ping，回应pong
                self.udp_server.send_status("pong", "Server is alive") # pyright: ignore[reportOptionalMemberAccess]
            
            elif message_type == 'get_status':
                # 客户端请求状态
                status_info = self._get_system_status()
                self.udp_server.send_status("system_status", str(status_info)) # pyright: ignore[reportOptionalMemberAccess]
            
            else:
                system_logger.debug(f"Received unknown message type: {message_type}")
                
        except Exception as e:
            system_logger.error(f"Error handling client message: {e}")
    
    def _get_system_status(self) -> Dict:
        """获取系统状态"""
        try:
            status = {
                'system_running': self.is_running,
                'hardware_connected': self.openbci_interface.is_connected if self.openbci_interface else False,
                'data_acquisition_active': self.openbci_interface.device.is_streaming if self.openbci_interface and self.openbci_interface.device else False,
                'client_connected': self.udp_server.sender.is_connected if self.udp_server else False,
                'buffer_stats': self.data_buffer.get_stats() if self.data_buffer else {},
                'timestamp': time.time()
            }
            
            return status
            
        except Exception as e:
            system_logger.error(f"Error getting system status: {e}")
            return {'error': str(e)}
    
    def start(self) -> bool:
        """
        启动系统
        
        Returns:
            bool: 启动是否成功
        """
        try:
            system_logger.info("Starting Brain Computer System...")
            system_logger.debug("start() called")
            
            # 加载配置
            if not self.load_config():
                system_logger.error("load_config() failed")
                return False
            system_logger.debug(f"config: {self.config}")
            
            # 初始化组件
            if not self.initialize_components():
                system_logger.error("initialize_components() failed")
                return False
            
            # 连接硬件
            if not self.connect_hardware():
                system_logger.error("connect_hardware() failed")
                return False
            
            # 开始数据采集
            if not self.start_data_acquisition():
                system_logger.error("start_data_acquisition() failed")
                return False
            
            # 开始通信
            if not self.start_communication():
                system_logger.error("start_communication() failed")
                return False
            
            # 启动处理线程
            self.start_processing_threads()
            system_logger.debug("Processing threads requested to start")
            
            self.is_running = True
            
            system_logger.info("Brain Computer System started successfully!")
            
            # 发送启动状态
            if self.udp_server:
                self.udp_server.send_status("system_started", "Server is ready")
                # 发送一次小的测试EEG包，帮助客户端验证接收和解析（调试用）
                try:
                    num_channels = self.config.get('openbci', {}).get('num_channels', 8)
                    test_samples = 5
                    test_eeg = [[0.0 for _ in range(num_channels)] for _ in range(test_samples)]
                    system_logger.debug("Sending initial test EEG packet to client for debug")
                    self.udp_server.send_eeg_data(test_eeg, None, {'note': 'initial_test_packet'})
                except Exception as e:
                    system_logger.error(f"Failed to send initial test EEG packet: {e}")
            
            return True
            
        except Exception as e:
            system_logger.error(f"Error starting system: {e}")
            return False
    
    def shutdown(self):
        """关闭系统"""
        if not self.is_running:
            return
        
        system_logger.info("Shutting down Brain Computer System...")
        
        self.is_running = False
        
        try:
            # 停止数据采集
            if self.openbci_interface:
                self.openbci_interface.stop_acquisition()
                self.openbci_interface.disconnect()
            
            # 停止通信
            if self.udp_server:
                self.udp_server.disconnect()
            
            # 等待线程结束
            if self.processing_thread and self.processing_thread.is_alive():
                self.processing_thread.join(timeout=2.0)
            
            if self.status_thread and self.status_thread.is_alive():
                self.status_thread.join(timeout=2.0)
            
            system_logger.info("Brain Computer System shutdown completed")
            
        except Exception as e:
            system_logger.error(f"Error during shutdown: {e}")
    
    def run(self):
        """运行系统主循环"""
        try:
            if not self.start():
                system_logger.error("Failed to start system")
                return False
            
            # 主循环
            while self.is_running:
                try:
                    time.sleep(1.0)
                    
                    # 检查系统状态
                    if self.openbci_interface and not self.openbci_interface.is_connected:
                        system_logger.warning("Hardware connection lost, attempting to reconnect...")
                        self.connect_hardware()
                    
                except KeyboardInterrupt:
                    system_logger.info("Received keyboard interrupt")
                    break
                except Exception as e:
                    system_logger.error(f"Error in main loop: {e}")
                    time.sleep(1.0)
            
            return True
            
        except Exception as e:
            system_logger.error(f"Error in run loop: {e}")
            return False
        finally:
            self.shutdown()

def main():
    """主函数"""
    # 创建系统实例
    system = BrainComputerSystem()
    
    try:
        # 运行系统
        success = system.run()
        
        if success:
            system_logger.info("System completed successfully")
        else:
            system_logger.error("System terminated with errors")
            
    except Exception as e:
        system_logger.error(f"Fatal error: {e}")
    
    finally:
        # 确保正确关闭
        system.shutdown()

if __name__ == "__main__":
    main()