"""
信号预处理模块
提供EEG信号的基本预处理功能：滤波、去噪等
"""

import numpy as np
from scipy import signal
from typing import List, Tuple, Optional, Dict
from utils.logger import system_logger

class EEGPreprocessor:
    """EEG信号预处理器"""
    
    def __init__(self, sample_rate: float = 250.0):
        """
        初始化预处理器
        
        Args:
            sample_rate: 采样率
        """
        self.sample_rate = sample_rate
        self.nyquist = sample_rate / 2.0
        
        # 滤波器
        self.bandpass_filter = None
        self.notch_filter = None
        
        self._setup_filters()
        system_logger.info(f"EEGPreprocessor initialized with sample_rate={sample_rate} Hz")
    
    def _setup_filters(self):
        """设置滤波器"""
        try:
            # 1-50Hz带通滤波器
            low_cutoff = 1.0
            high_cutoff = 50.0
            
            self.bandpass_filter = signal.butter(
                N=4, 
                Wn=[low_cutoff / self.nyquist, high_cutoff / self.nyquist], 
                btype='bandpass'
            )
            
            # 50Hz陷波滤波器（去除工频干扰）
            self.notch_filter = signal.iirnotch(
                w0=50.0, 
                Q=30.0, 
                fs=self.sample_rate
            )
            
            system_logger.debug("Filters set up successfully")
            
        except Exception as e:
            system_logger.error(f"Error setting up filters: {e}")
    
    def apply_bandpass_filter(self, data: np.ndarray) -> np.ndarray:
        """
        应用带通滤波器
        
        Args:
            data: 输入数据数组
            
        Returns:
            np.ndarray: 滤波后的数据
        """
        if self.bandpass_filter is None:
            system_logger.warning("Bandpass filter not available, returning original data")
            return data
        
        try:
            if data.ndim == 1:
                # 单通道数据
                filtered_data = signal.filtfilt(self.bandpass_filter[0], self.bandpass_filter[1], data)
            elif data.ndim == 2:
                # 多通道数据，对每个通道分别滤波
                filtered_data = np.zeros_like(data)
                for i in range(data.shape[1]):
                    filtered_data[:, i] = signal.filtfilt(
                        self.bandpass_filter[0], 
                        self.bandpass_filter[1], 
                        data[:, i]
                    )
            else:
                system_logger.warning("Invalid data dimension for filtering")
                return data
            
            return filtered_data
            
        except Exception as e:
            system_logger.error(f"Error applying bandpass filter: {e}")
            return data
    
    def apply_notch_filter(self, data: np.ndarray) -> np.ndarray:
        """
        应用陷波滤波器
        
        Args:
            data: 输入数据数组
            
        Returns:
            np.ndarray: 滤波后的数据
        """
        if self.notch_filter is None:
            system_logger.warning("Notch filter not available, returning original data")
            return data
        
        try:
            if data.ndim == 1:
                # 单通道数据
                filtered_data = signal.filtfilt(self.notch_filter[0], self.notch_filter[1], data)
            elif data.ndim == 2:
                # 多通道数据，对每个通道分别滤波
                filtered_data = np.zeros_like(data)
                for i in range(data.shape[1]):
                    filtered_data[:, i] = signal.filtfilt(
                        self.notch_filter[0], 
                        self.notch_filter[1], 
                        data[:, i]
                    )
            else:
                system_logger.warning("Invalid data dimension for filtering")
                return data
            
            return filtered_data
            
        except Exception as e:
            system_logger.error(f"Error applying notch filter: {e}")
            return data
    
    def apply_all_filters(self, data: np.ndarray) -> np.ndarray:
        """
        应用所有滤波器（顺序：陷波 -> 带通）
        
        Args:
            data: 输入数据数组
            
        Returns:
            np.ndarray: 滤波后的数据
        """
        try:
            # 首先应用陷波滤波器去除工频干扰
            filtered_data = self.apply_notch_filter(data)
            
            # 然后应用带通滤波器
            filtered_data = self.apply_bandpass_filter(filtered_data)
            
            return filtered_data
            
        except Exception as e:
            system_logger.error(f"Error applying all filters: {e}")
            return data
    
    def remove_artifacts(self, data: np.ndarray, threshold: float = 3.0) -> np.ndarray:
        """
        简单的伪迹移除（基于阈值）
        
        Args:
            data: 输入数据数组
            threshold: 阈值（标准差的倍数）
            
        Returns:
            np.ndarray: 清理后的数据
        """
        try:
            if data.ndim == 1:
                data = data.reshape(-1, 1)
            
            cleaned_data = data.copy()
            
            for channel in range(data.shape[1]):
                channel_data = data[:, channel]
                
                # 计算均值和标准差
                mean_val = np.mean(channel_data)
                std_val = np.std(channel_data)
                
                # 找出异常值
                threshold_val = threshold * std_val
                artifacts_mask = np.abs(channel_data - mean_val) > threshold_val
                
                # 用线性插值替换异常值
                artifacts_indices = np.where(artifacts_mask)[0]
                
                for idx in artifacts_indices:
                    if idx == 0:
                        # 第一个点，使用下一个值
                        cleaned_data[idx, channel] = channel_data[1] if len(channel_data) > 1 else mean_val
                    elif idx == len(channel_data) - 1:
                        # 最后一个点，使用前一个值
                        cleaned_data[idx, channel] = channel_data[-2]
                    else:
                        # 中间点，使用插值
                        prev_val = channel_data[idx - 1]
                        next_val = channel_data[idx + 1]
                        cleaned_data[idx, channel] = (prev_val + next_val) / 2
            
            return cleaned_data
            
        except Exception as e:
            system_logger.error(f"Error removing artifacts: {e}")
            return data
    
    def normalize_data(self, data: np.ndarray, method: str = 'zscore') -> np.ndarray:
        """
        数据标准化
        
        Args:
            data: 输入数据
            method: 标准化方法 ('zscore', 'minmax', 'robust')
            
        Returns:
            np.ndarray: 标准化后的数据
        """
        try:
            if method == 'zscore':
                # Z-score标准化
                return (data - np.mean(data)) / (np.std(data) + 1e-8)
            elif method == 'minmax':
                # Min-Max标准化
                data_min = np.min(data)
                data_max = np.max(data)
                if data_max - data_min > 1e-8:
                    return (data - data_min) / (data_max - data_min)
                else:
                    return data - data_min
            elif method == 'robust':
                # 鲁棒标准化（使用中位数和MAD）
                median = np.median(data)
                mad = np.median(np.abs(data - median))
                if mad > 1e-8:
                    return (data - median) / mad
                else:
                    return data - median
            else:
                system_logger.warning(f"Unknown normalization method: {method}")
                return data
                
        except Exception as e:
            system_logger.error(f"Error normalizing data: {e}")
            return data
    
    def calculate_snr(self, signal_data: np.ndarray, noise_data: Optional[np.ndarray] = None) -> float:
        """
        计算信噪比
        
        Args:
            signal_data: 信号数据
            noise_data: 噪声数据，如果为None则使用信号本身的方差估计
            
        Returns:
            float: 信噪比（dB）
        """
        try:
            signal_power = np.mean(signal_data ** 2)
            
            if noise_data is not None:
                noise_power = np.mean(noise_data ** 2)
            else:
                # 使用信号的低频部分估计噪声
                noise_power = np.var(signal_data)
            
            if noise_power > 0:
                snr_db = 10 * np.log10(signal_power / noise_power)
                return snr_db
            else:
                return float('inf')
                
        except Exception as e:
            system_logger.error(f"Error calculating SNR: {e}")
            return 0.0
    
    def get_filter_info(self) -> Dict:
        """获取滤波器信息"""
        return {
            'sample_rate': self.sample_rate,
            'nyquist_frequency': self.nyquist,
            'bandpass_range': [1.0, 50.0],
            'notch_frequency': 50.0,
            'filters_configured': self.bandpass_filter is not None and self.notch_filter is not None
        }

class SignalQualityAnalyzer:
    """信号质量分析器"""
    
    def __init__(self, sample_rate: float = 250.0):
        """
        初始化信号质量分析器
        
        Args:
            sample_rate: 采样率
        """
        self.sample_rate = sample_rate
        system_logger.info(f"SignalQualityAnalyzer initialized with sample_rate={sample_rate} Hz")
    
    def analyze_signal_quality(self, data: np.ndarray) -> Dict:
        """
        分析信号质量
        
        Args:
            data: EEG数据
            
        Returns:
            Dict: 信号质量指标
        """
        try:
            if data.ndim == 1:
                data = data.reshape(-1, 1)
            
            quality_metrics = {}
            
            for channel in range(data.shape[1]):
                channel_data = data[:, channel]
                
                # 计算各种质量指标
                metrics = {
                    'mean_amplitude': float(np.mean(np.abs(channel_data))),
                    'std_amplitude': float(np.std(channel_data)),
                    'max_amplitude': float(np.max(np.abs(channel_data))),
                    'variance': float(np.var(channel_data)),
                    'zero_crossing_rate': float(self._calculate_zero_crossing_rate(channel_data)),
                    'signal_range': float(np.max(channel_data) - np.min(channel_data))
                }
                
                quality_metrics[f'channel_{channel}'] = metrics
            
            # 整体质量评估
            all_amplitudes = np.abs(data.flatten())
            quality_metrics['overall'] = {
                'mean_amplitude': float(np.mean(all_amplitudes)),
                'std_amplitude': float(np.std(all_amplitudes)),
                'good_channels': self._assess_channel_quality(data)
            }
            
            return quality_metrics
            
        except Exception as e:
            system_logger.error(f"Error analyzing signal quality: {e}")
            return {}
    
    def _calculate_zero_crossing_rate(self, data: np.ndarray) -> float:
        """计算零交叉率"""
        try:
            sign_changes = np.sum(np.diff(np.sign(data)) != 0)
            return sign_changes / len(data)
        except:
            return 0.0
    
    def _assess_channel_quality(self, data: np.ndarray) -> int:
        """评估通道质量（好通道的数量）"""
        try:
            good_channels = 0
            
            for channel in range(data.shape[1]):
                channel_data = data[:, channel]
                
                # 简单的质量标准：
                # 1. 幅度不能太大（< 500uV）
                # 2. 标准差不能太小或太大
                max_amp = np.max(np.abs(channel_data))
                std_val = np.std(channel_data)
                
                if max_amp < 500.0 and 1.0 < std_val < 100.0:
                    good_channels += 1
            
            return good_channels
            
        except Exception as e:
            system_logger.error(f"Error assessing channel quality: {e}")
            return 0