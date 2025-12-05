"""
数据序列化工具模块
提供数据压缩、序列化和反序列化功能
"""

import json
import struct
import zlib
import base64
import numpy as np
from typing import Dict, List, Any, Union, Optional, Tuple
from utils.logger import system_logger

class DataSerializer:
    """数据序列化器"""
    
    def __init__(self, compression_level: int = 6):
        """
        初始化序列化器
        
        Args:
            compression_level: 压缩级别 (1-9)
        """
        self.compression_level = max(1, min(9, compression_level))
        system_logger.info(f"DataSerializer initialized with compression_level={compression_level}")
    
    def serialize_eeg_data(self, eeg_data: Union[List, np.ndarray], 
                          metadata: Optional[Dict] = None) -> str:
        """
        序列化EEG数据
        
        Args:
            eeg_data: EEG数据数组
            metadata: 元数据
            
        Returns:
            str: 序列化的JSON字符串
        """
        try:
            # 转换为numpy数组确保一致性
            data_array = np.array(eeg_data)
            
            # 创建数据字典
            data_dict = {
                'type': 'eeg_data',
                'data_type': 'eeg_data',
                'shape': list(data_array.shape),
                'dtype': str(data_array.dtype),
                'data': data_array.flatten().tolist()  # 扁平化为列表以便JSON序列化
            }
            
            # 添加元数据
            if metadata:
                data_dict['metadata'] = metadata
            
            # 转换为JSON字符串
            json_str = json.dumps(data_dict)
            
            # 压缩数据（如果启用）
            compressed_str = self._compress_data(json_str)
            
            return compressed_str
            
        except Exception as e:
            system_logger.error(f"Error serializing EEG data: {e}")
            return json.dumps({'error': str(e)})
    
    def deserialize_eeg_data(self, serialized_data: str) -> Tuple[Optional[np.ndarray], Optional[Dict]]:
        """
        反序列化EEG数据
        
        Args:
            serialized_data: 序列化的数据字符串
            
        Returns:
            Tuple[Optional[np.ndarray], Optional[Dict]]: (EEG数据数组, 元数据)
        """
        try:
            # 解压缩数据
            json_str = self._decompress_data(serialized_data)
            
            # 解析JSON
            data_dict = json.loads(json_str)
            
            # 检查数据类型
            if data_dict.get('type') != 'eeg_data':
                system_logger.error("Invalid data type for EEG data deserialization")
                return None, None
            
            # 重建数组
            shape = data_dict['shape']
            flattened_data = data_dict['data']
            
            data_array = np.array(flattened_data).reshape(shape)
            
            # 转换数据类型
            dtype = data_dict.get('dtype', 'float64')
            data_array = data_array.astype(dtype)
            
            metadata = data_dict.get('metadata', {})
            
            return data_array, metadata
            
        except Exception as e:
            system_logger.error(f"Error deserializing EEG data: {e}")
            return None, None
    
    def serialize_features(self, features: Dict, 
                          metadata: Optional[Dict] = None) -> str:
        """
        序列化特征数据
        
        Args:
            features: 特征字典
            metadata: 元数据
            
        Returns:
            str: 序列化的JSON字符串
        """
        try:
            # 创建数据字典
            data_dict = {
                'type': 'eeg_features',
                'data_type': 'eeg_features',
                'features': features
            }
            
            # 添加元数据
            if metadata:
                data_dict['metadata'] = metadata
            
            # 添加时间戳
            import time
            data_dict['timestamp'] = time.time()
            
            # 转换为JSON字符串
            json_str = json.dumps(data_dict, default=str)  # default=str处理numpy类型
            
            # 压缩数据
            compressed_str = self._compress_data(json_str)
            
            return compressed_str
            
        except Exception as e:
            system_logger.error(f"Error serializing features: {e}")
            return json.dumps({'error': str(e)})
    
    def deserialize_features(self, serialized_data: str) -> Tuple[Optional[Dict], Optional[Dict]]:
        """
        反序列化特征数据
        
        Args:
            serialized_data: 序列化的数据字符串
            
        Returns:
            Tuple[Optional[Dict], Optional[Dict]]: (特征字典, 元数据)
        """
        try:
            # 解压缩数据
            json_str = self._decompress_data(serialized_data)
            
            # 解析JSON
            data_dict = json.loads(json_str)
            
            # 检查数据类型
            if data_dict.get('type') != 'eeg_features':
                system_logger.error("Invalid data type for features deserialization")
                return None, None
            
            features = data_dict.get('features', {})
            metadata = data_dict.get('metadata', {})
            
            return features, metadata
            
        except Exception as e:
            system_logger.error(f"Error deserializing features: {e}")
            return None, None
    
    def serialize_simple_data(self, data: Dict, data_type: str = 'simple_data') -> str:
        """
        序列化简单数据
        
        Args:
            data: 数据字典
            data_type: 数据类型标识
            
        Returns:
            str: 序列化的JSON字符串
        """
        try:
            data_dict = {
                'type': data_type,
                'data': data,
                'timestamp': __import__('time').time()
            }
            
            json_str = json.dumps(data_dict, default=str)
            return self._compress_data(json_str)
            
        except Exception as e:
            system_logger.error(f"Error serializing simple data: {e}")
            return json.dumps({'error': str(e)})
    
    def _compress_data(self, json_str: str) -> str:
        """
        压缩JSON字符串
        
        Args:
            json_str: JSON字符串
            
        Returns:
            str: 压缩后的字符串（Base64编码）
        """
        try:
            # 压缩
            compressed_data = zlib.compress(json_str.encode('utf-8'), self.compression_level)
            
            # Base64编码
            encoded_data = base64.b64encode(compressed_data).decode('utf-8')
            
            return encoded_data
            
        except Exception as e:
            system_logger.error(f"Error compressing data: {e}")
            return json_str  # 返回原始数据
    
    def _decompress_data(self, compressed_str: str) -> str:
        """
        解压缩数据
        
        Args:
            compressed_str: 压缩后的字符串
            
        Returns:
            str: 解压后的JSON字符串
        """
        try:
            # 检查是否为有效的压缩数据
            if not self._is_compressed_data(compressed_str):
                # 如果不是压缩数据，直接返回原始字符串
                return compressed_str
            
            # Base64解码
            compressed_data = base64.b64decode(compressed_str.encode('utf-8'))
            
            # 解压
            json_str = zlib.decompress(compressed_data).decode('utf-8')
            
            return json_str
            
        except Exception as e:
            system_logger.error(f"Error decompressing data: {e}")
            # 如果解压失败，假设是原始JSON字符串
            return compressed_str
    
    def _is_compressed_data(self, data_str: str) -> bool:
        """
        检查数据是否为压缩数据
        
        Args:
            data_str: 数据字符串
            
        Returns:
            bool: 是否为压缩数据
        """
        try:
            # 尝试Base64解码和zlib解压缩
            base64.b64decode(data_str.encode('utf-8'))
            return True
        except:
            return False

class CompactDataPackager:
    """紧凑数据打包器 - 用于轻量级数据传输"""
    
    def __init__(self, max_packet_size: int = 1400):  # 一般UDP包大小限制
        """
        初始化紧凑数据打包器
        
        Args:
            max_packet_size: 最大包大小
        """
        self.max_packet_size = max_packet_size
        self.serializer = DataSerializer(compression_level=6)
        
        system_logger.info(f"CompactDataPackager initialized with max_packet_size={max_packet_size}")
    
    def package_eeg_for_transmission(self, eeg_data: np.ndarray, 
                                    features: Optional[Dict] = None,
                                    metadata: Optional[Dict] = None) -> List[str]:
        """
        打包EEG数据用于传输
        
        Args:
            eeg_data: EEG数据
            features: 特征数据
            metadata: 元数据
            
        Returns:
            List[str]: 数据包列表
        """
        try:
            packets = []
            
            # 创建基础数据包
            base_packet = {
                'type': 'transmission_header',
                'total_samples': eeg_data.shape[0],
                'channels': eeg_data.shape[1],
                'has_features': features is not None,
                'timestamp': __import__('time').time()
            }
            
            if metadata:
                base_packet['metadata'] = metadata
            
            header_packet = self.serializer.serialize_simple_data(base_packet, 'transmission_header')
            packets.append(header_packet)
            
            # 如果数据量不大，直接发送完整数据
            full_data = {
                'eeg_data': eeg_data.tolist(),
                'features': features
            }
            
            serialized_data = self.serializer.serialize_eeg_data(
                eeg_data, 
                {'features': features} if features else {}
            )
            
            # 检查数据包大小
            if len(serialized_data.encode('utf-8')) <= self.max_packet_size:
                packets.append(serialized_data)
            else:
                # 需要分块发送
                packets.extend(self._split_and_package_eeg_data(eeg_data, features, metadata))
            
            system_logger.debug(f"Packaged {len(packets)} packets for transmission")
            return packets
            
        except Exception as e:
            system_logger.error(f"Error packaging EEG data: {e}")
            return []
    
    def _split_and_package_eeg_data(self, eeg_data: np.ndarray, 
                                   features: Optional[Dict] = None,
                                   metadata: Optional[Dict] = None) -> List[str]:
        """分块打包EEG数据"""
        try:
            packets = []
            
            # 计算每个块的大小
            chunk_size = self.max_packet_size // (eeg_data.shape[1] * 8)  # 估算每个样本的字节数
            
            # 分块发送数据
            for i in range(0, eeg_data.shape[0], chunk_size):
                end_idx = min(i + chunk_size, eeg_data.shape[0])
                chunk_data = eeg_data[i:end_idx]
                
                chunk_info = {
                    'type': 'eeg_chunk',
                    'start_sample': i,
                    'end_sample': end_idx,
                    'total_samples': eeg_data.shape[0],
                    'eeg_data': chunk_data.tolist()
                }
                
                if i == 0 and features:  # 第一块包含特征数据
                    chunk_info['features'] = features
                
                serialized_chunk = self.serializer.serialize_simple_data(chunk_info, 'eeg_chunk')
                packets.append(serialized_chunk)
            
            return packets
            
        except Exception as e:
            system_logger.error(f"Error splitting EEG data: {e}")
            return []

class RealTimeDataBuffer:
    """实时数据缓冲区 - 用于高效的数据打包和发送"""
    
    def __init__(self, target_sample_rate: int = 30, buffer_size: int = 256):
        """
        初始化实时数据缓冲区
        
        Args:
            target_sample_rate: 目标发送频率 (Hz)
            buffer_size: 缓冲区大小（样本数）
        """
        self.target_sample_rate = target_sample_rate
        self.buffer_size = buffer_size
        self.sample_interval = 1.0 / target_sample_rate
        
        # 数据缓冲区
        self.data_buffer = []
        # 初始化为负值，确保第一次立即发送
        self.last_send_time = -float('inf')
        
        self.packager = CompactDataPackager()
        
        system_logger.info(f"RealTimeDataBuffer initialized for {target_sample_rate} Hz")
    
    def add_sample(self, sample: List[float], timestamp: float, 
                  features: Optional[Dict] = None):
        """
        添加样本到缓冲区
        
        Args:
            sample: EEG样本
            timestamp: 时间戳
            features: 特征数据
        """
        self.data_buffer.append({
            'sample': sample,
            'timestamp': timestamp,
            'features': features
        })
        
        # 检查是否需要发送数据
        # NOTE: 不在这里更新 last_send_time，避免在添加样本时阻止随后立即发送。
        # last_send_time 应在实际发送后由发送方更新。
    
    def get_data_for_transmission(self) -> Tuple[Optional[np.ndarray], Optional[Dict]]:
        """
        获取待传输的数据
        
        Returns:
            Tuple[Optional[np.ndarray], Optional[Dict]]: (EEG数据数组, 特征数据)
        """
        if not self.data_buffer:
            return None, None
        
        try:
            # 提取数据
            samples = [item['sample'] for item in self.data_buffer]
            eeg_data = np.array(samples)
            
            # 查找特征数据（使用最新的）
            features = None
            for item in reversed(self.data_buffer):
                if item['features']:
                    features = item['features']
                    break
            
            # 清空缓冲区
            self.data_buffer.clear()

            try:
                system_logger.debug(f"RealTimeDataBuffer.get_data_for_transmission: prepared samples={eeg_data.shape}")
            except Exception:
                pass
            
            return eeg_data, features
            
        except Exception as e:
            system_logger.error(f"Error preparing data for transmission: {e}")
            return None, None
    
    def clear(self):
        """清空缓冲区"""
        self.data_buffer.clear()
        system_logger.debug("Real-time data buffer cleared")
    
    def get_stats(self) -> Dict:
        """获取缓冲区统计信息"""
        current_time = __import__('time').time()
        
        return {
            'buffer_size': len(self.data_buffer),
            'max_buffer_size': self.buffer_size,
            'target_sample_rate': self.target_sample_rate,
            'sample_interval': self.sample_interval,
            'time_since_last_send': current_time - self.last_send_time,
            'buffer_utilization': len(self.data_buffer) / self.buffer_size
        }
    
    def should_send_data(self) -> bool:
        """
        判断是否满足发送数据的条件
        """
        import time
        current_time = time.time()
        
        # 条件1: 缓冲区为空则不发送
        if not self.data_buffer:
            return False
            
        # 条件2: 距离上次发送已经超过了设定的时间间隔 (比如 1/30秒)
        # 注意：self.last_send_time 初始化为负无穷，所以第一次必然满足
        if (current_time - self.last_send_time) >= self.sample_interval:
            return True
            
        # 条件3: 缓冲区积压过多（保护机制），强制发送
        if len(self.data_buffer) >= self.buffer_size:
            return True
            
        return False