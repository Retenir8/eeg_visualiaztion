"""
数据校验工具模块
用于验证数据的完整性和有效性
"""

import numpy as np
from typing import Union, List, Tuple

class DataValidator:
    """数据校验器"""
    
    @staticmethod
    def validate_eeg_channels(data: Union[List, np.ndarray], expected_channels: int = 8) -> bool:
        """
        验证EEG数据通道数
        
        Args:
            data: EEG数据数组
            expected_channels: 期望的通道数
            
        Returns:
            bool: 数据是否有效
        """
        try:
            data = np.array(data)
            if data.ndim == 1:
                return True  # 单通道数据
            
            if data.ndim == 2:
                return data.shape[1] == expected_channels
            
            return False
        except Exception:
            return False
    
    @staticmethod
    def validate_sample_rate(sample_rate: Union[int, float]) -> bool:
        """
        验证采样率
        
        Args:
            sample_rate: 采样率值
            
        Returns:
            bool: 采样率是否有效
        """
        try:
            rate = float(sample_rate)
            return 1.0 <= rate <= 10000.0  # 合理的EEG采样率范围
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_data_range(data: Union[List, np.ndarray], 
                          min_val: float = -1000.0, 
                          max_val: float = 1000.0) -> bool:
        """
        验证数据值范围
        
        Args:
            data: 数据数组
            min_val: 最小值
            max_val: 最大值
            
        Returns:
            bool: 数据是否在合理范围内
        """
        try:
            data = np.array(data)
            if data.size == 0:
                return False
            
            return bool(np.all((data >= min_val) & (data <= max_val)))
        except Exception:
            return False
    
    @staticmethod
    def detect_artifacts(data: Union[List, np.ndarray], 
                        threshold: float = 500.0) -> List[int]:
        """
        检测可能的伪迹（异常值）
        
        Args:
            data: EEG数据
            threshold: 阈值，超过此值被认为是伪迹
            
        Returns:
            List[int]: 伪迹样本的索引列表
        """
        try:
            data = np.array(data)
            if data.ndim == 1:
                data = data.reshape(-1, 1)
            
            artifacts = []
            for i, sample in enumerate(data):
                if np.any(np.abs(sample) > threshold):
                    artifacts.append(i)
            
            return artifacts
        except Exception:
            return []
    
    @staticmethod
    def clean_artifacts(data: Union[List, np.ndarray], 
                       artifacts: List[int]) -> np.ndarray:
        """
        清除伪迹（使用插值）
        
        Args:
            data: 原始EEG数据
            artifacts: 伪迹索引列表
            
        Returns:
            np.ndarray: 清理后的数据
        """
        try:
            data = np.array(data)
            if data.ndim == 1:
                data = data.reshape(-1, 1)
            
            cleaned_data = data.copy()
            
            for artifact_idx in artifacts:
                if artifact_idx == 0:
                    # 第一个点，使用下一个值
                    cleaned_data[artifact_idx] = data[min(1, len(data)-1)]
                elif artifact_idx == len(data) - 1:
                    # 最后一个点，使用前一个值
                    cleaned_data[artifact_idx] = data[max(0, len(data)-2)]
                else:
                    # 中间点，使用线性插值
                    cleaned_data[artifact_idx] = (
                        data[artifact_idx - 1] + data[artifact_idx + 1]
                    ) / 2
            
            return cleaned_data
        except Exception:
            return np.array(data)
    
    @staticmethod
    def validate_frequency_band(band: str) -> bool:
        """
        验证频带名称
        
        Args:
            band: 频带名称
            
        Returns:
            bool: 频带名称是否有效
        """
        valid_bands = ['delta', 'theta', 'alpha', 'beta', 'gamma']
        return band.lower() in valid_bands
    
    @staticmethod
    def validate_udp_data(data_dict: dict) -> bool:
        """
        验证UDP接收的数据结构
        
        Args:
            data_dict: UDP数据字典
            
        Returns:
            bool: 数据结构是否有效
        """
        required_keys = ['timestamp', 'channels', 'sample_rate']
        
        try:
            # 检查必要键
            if not all(key in data_dict for key in required_keys):
                return False
            
            # 检查数据类型
            if not isinstance(data_dict['timestamp'], (int, float)):
                return False
            
            if not isinstance(data_dict['channels'], list):
                return False
            
            if not isinstance(data_dict['sample_rate'], (int, float)):
                return False
            
            return True
        except Exception:
            return False