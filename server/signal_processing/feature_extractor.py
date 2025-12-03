"""
特征提取模块
从EEG信号中提取各种频域和时域特征
"""

import numpy as np
from scipy import signal, fft
from typing import Dict, List, Tuple, Optional
from utils.logger import system_logger

class FeatureExtractor:
    """EEG特征提取器"""
    
    def __init__(self, sample_rate: float = 250.0):
        """
        初始化特征提取器
        
        Args:
            sample_rate: 采样率
        """
        self.sample_rate = sample_rate
        
        # 定义标准EEG频带
        self.frequency_bands = {
            'delta': (1, 4),     # Delta波：1-4 Hz
            'theta': (4, 8),     # Theta波：4-8 Hz
            'alpha': (8, 13),    # Alpha波：8-13 Hz
            'beta': (13, 30),    # Beta波：13-30 Hz
            'gamma': (30, 50)    # Gamma波：30-50 Hz
        }
        
        system_logger.info(f"FeatureExtractor initialized with sample_rate={sample_rate} Hz")
    
    def extract_power_spectral_density(self, data: np.ndarray, window_size: int = 256) -> Dict:
        """
        提取功率谱密度特征
        
        Args:
            data: EEG数据，形状为 (n_samples, n_channels) 或 (n_samples,)
            window_size: 窗口大小
            
        Returns:
            Dict: 功率谱密度特征
        """
        try:
            if data.ndim == 1:
                data = data.reshape(-1, 1)
            
            n_samples, n_channels = data.shape
            psd_features = {}
            
            # 计算每个通道的PSD
            for channel in range(n_channels):
                channel_data = data[:, channel]
                
                # 使用Welch方法计算PSD
                frequencies, psd = signal.welch(
                    channel_data,
                    fs=self.sample_rate,
                    nperseg=min(window_size, len(channel_data)//2),
                    noverlap=None
                )
                
                # 存储频率和功率
                psd_features[f'channel_{channel}'] = {
                    'frequencies': frequencies,
                    'power_spectral_density': psd
                }
            
            return psd_features
            
        except Exception as e:
            system_logger.error(f"Error extracting PSD: {e}")
            return {}
    
    def extract_frequency_band_power(self, data: np.ndarray, window_size: int = 256) -> Dict:
        """
        提取频带功率特征
        
        Args:
            data: EEG数据，形状为 (n_samples, n_channels) 或 (n_samples,)
            window_size: 窗口大小
            
        Returns:
            Dict: 频带功率特征
        """
        try:
            if data.ndim == 1:
                data = data.reshape(-1, 1)
            
            n_samples, n_channels = data.shape
            band_power_features = {}
            
            # 计算每个通道的频带功率
            for channel in range(n_channels):
                channel_data = data[:, channel]
                
                # 使用Welch方法计算PSD
                frequencies, psd = signal.welch(
                    channel_data,
                    fs=self.sample_rate,
                    nperseg=min(window_size, len(channel_data)//2),
                    noverlap=None
                )
                
                band_powers = {}
                
                # 计算每个频带的功率
                for band_name, (low_freq, high_freq) in self.frequency_bands.items():
                    # 找到频带对应的频率索引
                    freq_mask = (frequencies >= low_freq) & (frequencies <= high_freq)
                    
                    if np.any(freq_mask):
                        # 计算频带内的功率（积分）
                        band_power = np.trapz(psd[freq_mask], frequencies[freq_mask])
                        band_powers[band_name] = float(band_power)
                    else:
                        band_powers[band_name] = 0.0
                
                band_power_features[f'channel_{channel}'] = band_powers
            
            return band_power_features
            
        except Exception as e:
            system_logger.error(f"Error extracting frequency band power: {e}")
            return {}
    
    def extract_relative_band_power(self, data: np.ndarray, window_size: int = 256) -> Dict:
        """
        提取相对频带功率特征（相对于总功率）
        
        Args:
            data: EEG数据
            window_size: 窗口大小
            
        Returns:
            Dict: 相对频带功率特征
        """
        try:
            # 获取绝对频带功率
            abs_band_power = self.extract_frequency_band_power(data, window_size)
            
            relative_band_power = {}
            
            for channel_key, band_powers in abs_band_power.items():
                total_power = sum(band_powers.values())
                
                relative_powers = {}
                if total_power > 0:
                    for band_name, power in band_powers.items():
                        relative_powers[band_name] = float(power / total_power)
                else:
                    for band_name in band_powers.keys():
                        relative_powers[band_name] = 0.0
                
                relative_band_power[channel_key] = relative_powers
            
            return relative_band_power
            
        except Exception as e:
            system_logger.error(f"Error extracting relative band power: {e}")
            return {}
    
    def extract_time_domain_features(self, data: np.ndarray) -> Dict:
        """
        提取时域特征
        
        Args:
            data: EEG数据，形状为 (n_samples, n_channels) 或 (n_samples,)
            
        Returns:
            Dict: 时域特征
        """
        try:
            if data.ndim == 1:
                data = data.reshape(-1, 1)
            
            n_samples, n_channels = data.shape
            time_features = {}
            
            for channel in range(n_channels):
                channel_data = data[:, channel]
                
                # 基本统计特征
                features = {
                    'mean': float(np.mean(channel_data)),
                    'std': float(np.std(channel_data)),
                    'variance': float(np.var(channel_data)),
                    'min': float(np.min(channel_data)),
                    'max': float(np.max(channel_data)),
                    'range': float(np.max(channel_data) - np.min(channel_data)),
                    'rms': float(np.sqrt(np.mean(channel_data**2))),
                    'skewness': float(self._calculate_skewness(channel_data)),
                    'kurtosis': float(self._calculate_kurtosis(channel_data)),
                    'zero_crossing_rate': float(self._calculate_zero_crossing_rate(channel_data)),
                    'waveform_length': float(np.sum(np.abs(np.diff(channel_data)))),
                    'mean_abs_deviation': float(np.mean(np.abs(channel_data - np.mean(channel_data))))
                }
                
                time_features[f'channel_{channel}'] = features
            
            return time_features
            
        except Exception as e:
            system_logger.error(f"Error extracting time domain features: {e}")
            return {}
    
    def extract_spectral_features(self, data: np.ndarray, window_size: int = 256) -> Dict:
        """
        提取频域特征
        
        Args:
            data: EEG数据
            window_size: 窗口大小
            
        Returns:
            Dict: 频域特征
        """
        try:
            if data.ndim == 1:
                data = data.reshape(-1, 1)
            
            n_samples, n_channels = data.shape
            spectral_features = {}
            
            for channel in range(n_channels):
                channel_data = data[:, channel]
                
                # 计算FFT
                fft_values = np.fft.fft(channel_data)
                frequencies = np.fft.fftfreq(len(channel_data), 1/self.sample_rate)
                
                # 只取正频率部分
                positive_freq_mask = frequencies > 0
                positive_frequencies = frequencies[positive_freq_mask]
                positive_fft_magnitude = np.abs(fft_values[positive_freq_mask])
                
                # 频域特征
                features = {
                    'spectral_centroid': float(self._calculate_spectral_centroid(positive_frequencies, positive_fft_magnitude)),
                    'spectral_bandwidth': float(self._calculate_spectral_bandwidth(positive_frequencies, positive_fft_magnitude)),
                    'spectral_rolloff': float(self._calculate_spectral_rolloff(positive_frequencies, positive_fft_magnitude)),
                    'spectral_energy': float(np.sum(positive_fft_magnitude**2)),
                    'mean_frequency': float(np.average(positive_frequencies, weights=positive_fft_magnitude)),
                    'spectral_flatness': float(self._calculate_spectral_flatness(positive_fft_magnitude))
                }
                
                spectral_features[f'channel_{channel}'] = features
            
            return spectral_features
            
        except Exception as e:
            system_logger.error(f"Error extracting spectral features: {e}")
            return {}
    
    def extract_all_features(self, data: np.ndarray, window_size: int = 256) -> Dict:
        """
        提取所有特征
        
        Args:
            data: EEG数据
            window_size: 窗口大小
            
        Returns:
            Dict: 所有特征
        """
        try:
            all_features = {}
            
            # 时域特征
            time_features = self.extract_time_domain_features(data)
            all_features['time_domain'] = time_features
            
            # 频域特征
            spectral_features = self.extract_spectral_features(data, window_size)
            all_features['spectral_domain'] = spectral_features
            
            # 频带功率特征
            band_power_features = self.extract_frequency_band_power(data, window_size)
            all_features['absolute_band_power'] = band_power_features
            
            relative_band_power_features = self.extract_relative_band_power(data, window_size)
            all_features['relative_band_power'] = relative_band_power_features
            
            return all_features
            
        except Exception as e:
            system_logger.error(f"Error extracting all features: {e}")
            return {}
    
    def _calculate_skewness(self, data: np.ndarray) -> float:
        """计算偏度"""
        try:
            mean_val = np.mean(data)
            std_val = np.std(data)
            if std_val > 0:
                return float(np.mean(((data - mean_val) / std_val) ** 3))
            return 0.0
        except:
            return 0.0
    
    def _calculate_kurtosis(self, data: np.ndarray) -> float:
        """计算峰度"""
        try:
            mean_val = np.mean(data)
            std_val = np.std(data)
            if std_val > 0:
                return float(np.mean(((data - mean_val) / std_val) ** 4))
            return 0.0
        except:
            return 0.0
    
    def _calculate_zero_crossing_rate(self, data: np.ndarray) -> float:
        """计算零交叉率"""
        try:
            sign_changes = np.sum(np.diff(np.sign(data)) != 0)
            return sign_changes / len(data)
        except:
            return 0.0
    
    def _calculate_spectral_centroid(self, frequencies: np.ndarray, magnitude: np.ndarray) -> float:
        """计算频谱重心"""
        try:
            return float(np.sum(frequencies * magnitude) / np.sum(magnitude))
        except:
            return 0.0
    
    def _calculate_spectral_bandwidth(self, frequencies: np.ndarray, magnitude: np.ndarray) -> float:
        """计算频谱带宽"""
        try:
            centroid = self._calculate_spectral_centroid(frequencies, magnitude)
            return float(np.sqrt(np.sum(((frequencies - centroid) ** 2) * magnitude) / np.sum(magnitude)))
        except:
            return 0.0
    
    def _calculate_spectral_rolloff(self, frequencies: np.ndarray, magnitude: np.ndarray) -> float:
        """计算频谱滚降点"""
        try:
            total_magnitude = np.sum(magnitude)
            cumulative_magnitude = np.cumsum(magnitude)
            rolloff_threshold = 0.85 * total_magnitude
            
            rolloff_index = np.where(cumulative_magnitude >= rolloff_threshold)[0]
            if len(rolloff_index) > 0:
                return float(frequencies[rolloff_index[0]])
            return float(frequencies[-1])
        except:
            return 0.0
    
    def _calculate_spectral_flatness(self, magnitude: np.ndarray) -> float:
        """计算频谱平坦度"""
        try:
            geometric_mean = np.exp(np.mean(np.log(magnitude + 1e-10)))
            arithmetic_mean = np.mean(magnitude)
            if arithmetic_mean > 0:
                return float(geometric_mean / arithmetic_mean)
            return 0.0
        except:
            return 0.0

class RealTimeFeatureExtractor:
    """实时特征提取器 - 专门用于连续流数据的特征提取"""
    
    def __init__(self, sample_rate: float = 250.0, window_size: int = 256):
        """
        初始化实时特征提取器
        
        Args:
            sample_rate: 采样率
            window_size: 特征计算窗口大小
        """
        self.sample_rate = sample_rate
        self.window_size = window_size
        self.feature_buffer = []
        self.max_buffer_size = window_size * 4  # 缓存4个窗口的数据
        
        self.feature_extractor = FeatureExtractor(sample_rate)
        
        system_logger.info(f"RealTimeFeatureExtractor initialized")
    
    def process_sample(self, sample: List[float], timestamp: float) -> Optional[Dict]:
        """
        处理单个样本
        
        Args:
            sample: 单个EEG样本
            timestamp: 时间戳
            
        Returns:
            Dict: 提取的特征，如果数据不足则返回None
        """
        try:
            # 添加样本到缓冲区
            self.feature_buffer.append((sample, timestamp))
            
            # 如果缓冲区大小不足，返回None
            if len(self.feature_buffer) < self.window_size:
                return None
            
            # 如果缓冲区太大，移除旧数据
            if len(self.feature_buffer) > self.max_buffer_size:
                self.feature_buffer = self.feature_buffer[-self.max_buffer_size:]
            
            # 提取特征
            features = self._extract_features_from_buffer()
            
            return features
            
        except Exception as e:
            system_logger.error(f"Error processing sample: {e}")
            return None
    
    def _extract_features_from_buffer(self) -> Dict:
        """从缓冲区提取特征"""
        try:
            # 获取最近的窗口数据
            recent_samples = self.feature_buffer[-self.window_size:]
            
            # 转换为numpy数组
            data_matrix = np.array([sample[0] for sample in recent_samples])
            timestamps = [sample[1] for sample in recent_samples]
            
            # 提取特征
            features = self.feature_extractor.extract_all_features(data_matrix)
            
            # 添加时间信息
            features['metadata'] = {
                'timestamp_range': [timestamps[0], timestamps[-1]],
                'sample_count': len(timestamps),
                'window_size': self.window_size
            }
            
            return features
            
        except Exception as e:
            system_logger.error(f"Error extracting features from buffer: {e}")
            return {}
    
    def reset(self):
        """重置缓冲区"""
        self.feature_buffer.clear()
        system_logger.debug("Feature buffer reset")