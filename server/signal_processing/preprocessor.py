"""
信号预处理模块
提供EEG信号的基本预处理功能：实时滤波、去噪等
(已修改为支持逐样本实时处理)
"""

import numpy as np
from scipy import signal
from typing import List, Tuple, Optional, Dict
from utils.logger import system_logger

class EEGPreprocessor:
    """EEG信号预处理器 - 实时滤波优化版"""
    
    def __init__(self, sample_rate: float = 250.0):
        """
        初始化预处理器
        
        Args:
            sample_rate: 采样率
        """
        self.sample_rate = sample_rate
        self.nyquist = sample_rate / 2.0
        
        # 滤波器系数 (b, a)
        self.bandpass_coeff = None
        self.notch_coeff = None
        
        # 滤波器实时状态 (State)
        # 字典结构: {'notch': np.array, 'bandpass': np.array}
        # 状态将在第一次收到数据时根据通道数自动初始化
        self.filter_states = {}
        
        self._setup_filters()
        system_logger.info(f"EEGPreprocessor (Real-time) initialized with sample_rate={sample_rate} Hz")
    
    def _setup_filters(self):
        """设置滤波器系数"""
        try:
            # 1-50Hz带通滤波器
            low_cutoff = 1.0
            high_cutoff = 50.0
            
            # 这里的 b, a 是滤波器系数
            self.bandpass_coeff = signal.butter(
                N=4, 
                Wn=[low_cutoff / self.nyquist, high_cutoff / self.nyquist], 
                btype='bandpass'
            )
            
            # 50Hz陷波滤波器（去除工频干扰）
            self.notch_coeff = signal.iirnotch(
                w0=50.0, 
                Q=30.0, 
                fs=self.sample_rate
            )
            
            system_logger.debug("Filter coefficients setup successfully")
            
        except Exception as e:
            system_logger.error(f"Error setting up filters: {e}")
    
    def _get_filter_state(self, filter_name: str, n_channels: int, b, a):
        """
        获取或初始化滤波器状态 zi
        filtfilt 是无状态的，但 lfilter 需要 zi 来保持连续性
        """
        state_key = f"{filter_name}_{n_channels}"
        
        if state_key not in self.filter_states:
            # 计算滤波器的稳态初始条件
            zi_init = signal.lfilter_zi(b, a)
            
            # 扩展状态以匹配通道数 (n_channels, order-1)
            self.filter_states[state_key] = np.tile(zi_init, (n_channels, 1))
            
            system_logger.debug(f"Initialized {filter_name} filter state for {n_channels} channels")
            
        return self.filter_states[state_key]

    def _apply_realtime_filter(self, data: np.ndarray, filter_name: str, b, a) -> np.ndarray:
        """
        应用实时滤波（带状态保持）
        """
        if b is None or a is None:
            return data
            
        try:
            # 确保数据是 2D 数组 (n_samples, n_channels)
            input_data = data
            original_shape = data.shape
            
            # 如果是一维数组，我们需要判断它是 (samples,) 还是 (channels,)
            # 在此系统中，单样本通常是 (n_channels,) 或者 (1, n_channels)
            if data.ndim == 1:
                # 假设它是单时刻的多通道数据，转为 (1, n_channels)
                input_data = data.reshape(1, -1)
            
            n_samples, n_channels = input_data.shape
            
            # 获取当前通道数的滤波器状态
            zi = self._get_filter_state(filter_name, n_channels, b, a)
            
            output_data = np.zeros_like(input_data)
            
            # 对每个通道分别进行滤波并更新状态
            for i in range(n_channels):
                # lfilter 返回: (filtered_data, new_state)
                filtered, new_zi = signal.lfilter(b, a, input_data[:, i], zi=zi[i])
                output_data[:, i] = filtered
                zi[i] = new_zi  # 重要：更新状态以供下一个样本使用
            
            return output_data.reshape(original_shape)
            
        except Exception as e:
            system_logger.error(f"Error in realtime filter ({filter_name}): {e}")
            return data

    def apply_notch_filter(self, data: np.ndarray) -> np.ndarray:
        """应用陷波滤波器 (实时)"""
        return self._apply_realtime_filter(
            data, 'notch', self.notch_coeff[0], self.notch_coeff[1] # type: ignore
        )
    
    def apply_bandpass_filter(self, data: np.ndarray) -> np.ndarray:
        """应用带通滤波器 (实时)"""
        return self._apply_realtime_filter(
            data, 'bandpass', self.bandpass_coeff[0], self.bandpass_coeff[1] # type: ignore
        )
    
    def apply_all_filters(self, data: np.ndarray) -> np.ndarray:
        """应用所有滤波器"""
        # 级联滤波：先陷波，再带通
        d = self.apply_notch_filter(data)
        return self.apply_bandpass_filter(d)
    
    def remove_artifacts(self, data: np.ndarray, threshold: float = 3.0) -> np.ndarray:
        """
        简单的伪迹移除（基于阈值）
        注意：此方法是无状态的，对于单样本流可能效果有限，但在平稳信号中可用
        """
        try:
            if data.ndim == 1:
                data = data.reshape(-1, 1)
            
            cleaned_data = data.copy()
            
            # 针对单样本流，很难计算动态均值/方差。
            # 这里简单保留原逻辑，如果是单样本，mean=val, std=0，不会触发阈值
            # 这是一个妥协，如果要更精确需要维护滑动窗口统计量
            if data.shape[0] > 1: 
                for channel in range(data.shape[1]):
                    channel_data = data[:, channel]
                    mean_val = np.mean(channel_data)
                    std_val = np.std(channel_data)
                    
                    if std_val > 1e-6: # 避免除零
                        threshold_val = threshold * std_val
                        artifacts_mask = np.abs(channel_data - mean_val) > threshold_val
                        
                        # 简单的置零或保持上一值策略（这里简化为保持原值或限制幅度）
                        # 实际应用中建议使用滑动窗口去除伪迹
                        if np.any(artifacts_mask):
                            # 简单钳位
                            cleaned_data[artifacts_mask, channel] = \
                                np.sign(channel_data[artifacts_mask]) * (mean_val + threshold_val)
            
            return cleaned_data
            
        except Exception as e:
            system_logger.error(f"Error removing artifacts: {e}")
            return data
    
    def normalize_data(self, data: np.ndarray, method: str = 'zscore') -> np.ndarray:
        """数据标准化"""
        # 注意：对于单样本流，无法计算统计量进行标准化。
        # 建议在客户端进行基于窗口的标准化，或者在服务端维护滑动窗口。
        # 为防止报错，如果是单样本直接返回。
        if data.shape[0] <= 1:
            return data

        try:
            if method == 'zscore':
                return (data - np.mean(data)) / (np.std(data) + 1e-8)
            elif method == 'minmax':
                data_min = np.min(data)
                data_max = np.max(data)
                if data_max - data_min > 1e-8:
                    return (data - data_min) / (data_max - data_min)
                return data - data_min
            else:
                return data
        except Exception as e:
            system_logger.error(f"Error normalizing data: {e}")
            return data
    
    def calculate_snr(self, signal_data: np.ndarray, noise_data: Optional[np.ndarray] = None) -> float:
        """计算信噪比"""
        try:
            signal_power = np.mean(signal_data ** 2)
            if noise_data is not None:
                noise_power = np.mean(noise_data ** 2)
            else:
                noise_power = np.var(signal_data)
            
            if noise_power > 0:
                return 10 * np.log10(signal_power / noise_power)
            return float('inf')
        except Exception:
            return 0.0
    
    def get_filter_info(self) -> Dict:
        return {
            'sample_rate': self.sample_rate,
            'nyquist_frequency': self.nyquist,
            'bandpass_range': [1.0, 50.0],
            'notch_frequency': 50.0,
            'mode': 'real-time'
        }

class SignalQualityAnalyzer:
    """信号质量分析器"""
    
    def __init__(self, sample_rate: float = 250.0):
        self.sample_rate = sample_rate
        system_logger.info(f"SignalQualityAnalyzer initialized with sample_rate={sample_rate} Hz")
    
    def analyze_signal_quality(self, data: np.ndarray) -> Dict:
        """分析信号质量"""
        try:
            if data.ndim == 1:
                data = data.reshape(-1, 1)
            
            quality_metrics = {}
            for channel in range(data.shape[1]):
                channel_data = data[:, channel]
                metrics = {
                    'mean_amplitude': float(np.mean(np.abs(channel_data))),
                    'std_amplitude': float(np.std(channel_data)),
                    'max_amplitude': float(np.max(np.abs(channel_data))),
                    'variance': float(np.var(channel_data)),
                    'signal_range': float(np.max(channel_data) - np.min(channel_data))
                }
                quality_metrics[f'channel_{channel}'] = metrics
            
            # 整体质量
            all_amplitudes = np.abs(data.flatten())
            quality_metrics['overall'] = {
                'mean_amplitude': float(np.mean(all_amplitudes)),
                'std_amplitude': float(np.std(all_amplitudes)),
                'good_channels': self._assess_channel_quality(data)
            }
            return quality_metrics
            
        except Exception as e:
            # 日志过于频繁，仅在非长度错误时记录，或者降低级别
            # system_logger.error(f"Error analyzing signal quality: {e}")
            return {}
    
    def _assess_channel_quality(self, data: np.ndarray) -> int:
        """评估通道质量"""
        try:
            good_channels = 0
            for channel in range(data.shape[1]):
                channel_data = data[:, channel]
                max_amp = np.max(np.abs(channel_data))
                std_val = np.std(channel_data)
                # 简单判断：幅度不过大且不是直线
                if max_amp < 1000.0 and std_val > 0.1:
                    good_channels += 1
            return good_channels
        except Exception:
            return 0