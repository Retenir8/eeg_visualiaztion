"""
数据缓存模块
提供高效的实时数据缓存和环形缓冲区功能
"""

import numpy as np
import threading
from collections import deque
from typing import List, Optional, Tuple
from utils.logger import system_logger

class DataBuffer:
    """环形数据缓冲区"""
    
    def __init__(self, max_size: int = 1000):
        """
        初始化数据缓冲区
        
        Args:
            max_size: 最大缓冲区大小
        """
        self.max_size = max_size
        self.buffer = np.zeros(max_size)
        self.head = 0
        self.tail = 0
        self.count = 0
        self.lock = threading.Lock()
        system_logger.info(f"DataBuffer initialized with max_size={max_size}")
    
    def push(self, data):
        """添加数据到缓冲区"""
        with self.lock:
            if self.count == self.max_size:
                # 缓冲区满，移除最旧的数据
                self.tail = (self.tail + 1) % self.max_size
            else:
                self.count += 1
            
            self.buffer[self.head] = data
            self.head = (self.head + 1) % self.max_size
    
    def push_array(self, data_array: np.ndarray):
        """批量添加数据数组"""
        with self.lock:
            for data in data_array:
                self.push(data)
    
    def get_recent(self, n: int) -> np.ndarray:
        """获取最近的n个数据点"""
        with self.lock:
            if n > self.count:
                n = self.count
            
            if n == 0:
                return np.array([])
            
            # 计算起始索引
            start_idx = (self.head - n) % self.max_size
            
            if start_idx < self.tail:
                # 数据跨越缓冲区边界
                return np.concatenate([
                    self.buffer[start_idx:self.max_size],
                    self.buffer[0:self.head]
                ])
            else:
                # 数据在连续区域内
                return self.buffer[start_idx:self.head]
    
    def get_all(self) -> np.ndarray:
        """获取所有数据"""
        return self.get_recent(self.count)
    
    def clear(self):
        """清空缓冲区"""
        with self.lock:
            self.buffer.fill(0)
            self.head = 0
            self.tail = 0
            self.count = 0
            system_logger.info("Data buffer cleared")
    
    def get_stats(self) -> dict:
        """获取缓冲区统计信息"""
        with self.lock:
            return {
                'max_size': self.max_size,
                'current_size': self.count,
                'head': self.head,
                'tail': self.tail,
                'utilization': self.count / self.max_size
            }

class MultiChannelBuffer:
    """多通道EEG数据缓冲区"""
    
    def __init__(self, max_size: int = 1000, num_channels: int = 8):
        """
        初始化多通道数据缓冲区
        
        Args:
            max_size: 每个通道的最大缓冲区大小
            num_channels: 通道数
        """
        self.num_channels = num_channels
        self.buffers = [DataBuffer(max_size) for _ in range(num_channels)]
        self.sample_counter = 0
        self.lock = threading.Lock()
        system_logger.info(f"MultiChannelBuffer initialized with {num_channels} channels, max_size={max_size}")
    
    def push_sample(self, channels_data: List[float]):
        """
        添加一个多通道样本
        
        Args:
            channels_data: 通道数据列表，长度应为num_channels
        """
        if len(channels_data) != self.num_channels:
            raise ValueError(f"Expected {self.num_channels} channels, got {len(channels_data)}")
        
        with self.lock:
            for i, channel_data in enumerate(channels_data):
                self.buffers[i].push(channel_data)
            
            self.sample_counter += 1
    
    def push_samples(self, samples_data: np.ndarray):
        """
        批量添加多通道样本
        
        Args:
            samples_data: 形状为 (n_samples, num_channels) 的数组
        """
        if samples_data.ndim != 2:
            raise ValueError("Input must be 2D array (samples, channels)")
        
        if samples_data.shape[1] != self.num_channels:
            raise ValueError(f"Expected {self.num_channels} channels, got {samples_data.shape[1]}")
        
        with self.lock:
            for sample in samples_data:
                for i, channel_data in enumerate(sample):
                    self.buffers[i].push(channel_data)
            
            self.sample_counter += samples_data.shape[0]
    
    def get_channel_data(self, channel_idx: int, n_samples: int = None) -> np.ndarray: # type: ignore
        """
        获取指定通道的数据
        
        Args:
            channel_idx: 通道索引
            n_samples: 要获取的样本数，None表示获取所有数据
            
        Returns:
            np.ndarray: 通道数据
        """
        if channel_idx >= self.num_channels:
            raise ValueError(f"Channel index {channel_idx} out of range (0-{self.num_channels-1})")
        
        if n_samples is None:
            return self.buffers[channel_idx].get_all()
        else:
            return self.buffers[channel_idx].get_recent(n_samples)
    
    def get_all_channels(self, n_samples: int = None) -> np.ndarray: # pyright: ignore[reportArgumentType]
        """
        获取所有通道的数据
        
        Args:
            n_samples: 要获取的样本数，None表示获取所有数据
            
        Returns:
            np.ndarray: 形状为 (n_samples, num_channels) 的数据数组
        """
        if n_samples is None:
            n_samples = self.buffers[0].count
        
        # 获取每个通道的数据
        channel_data = []
        for i in range(self.num_channels):
            channel_data.append(self.buffers[i].get_recent(n_samples))
        
        return np.column_stack(channel_data)
    
    def clear_all(self):
        """清空所有通道的缓冲区"""
        with self.lock:
            for buffer in self.buffers:
                buffer.clear()
            self.sample_counter = 0
            system_logger.info("All channel buffers cleared")
    
    def get_stats(self) -> dict:
        """获取缓冲区统计信息"""
        with self.lock:
            channel_stats = [buffer.get_stats() for buffer in self.buffers]
            
            return {
                'num_channels': self.num_channels,
                'total_samples': self.sample_counter,
                'channel_stats': channel_stats
            }

class TimeSeriesBuffer:
    """时间序列数据缓冲区，用于存储带时间戳的数据"""
    
    def __init__(self, max_duration_seconds: float = 60.0, sample_rate: float = 250.0):
        """
        初始化时间序列缓冲区
        
        Args:
            max_duration_seconds: 最大存储时长（秒）
            sample_rate: 采样率（Hz）
        """
        self.max_duration_seconds = max_duration_seconds
        self.sample_rate = sample_rate
        self.max_samples = int(max_duration_seconds * sample_rate)
        
        # 使用deque来高效存储时间序列数据
        self.timestamps = deque(maxlen=self.max_samples)
        self.data_buffer = deque(maxlen=self.max_samples)
        
        self.lock = threading.Lock()
        system_logger.info(f"TimeSeriesBuffer initialized with max_duration={max_duration_seconds}s")
    
    def add_sample(self, timestamp: float, data: List[float]):
        """
        添加一个时间戳样本
        
        Args:
            timestamp: 时间戳
            data: 数据值列表
        """
        with self.lock:
            self.timestamps.append(timestamp)
            self.data_buffer.append(data)
    
    def get_recent_data(self, duration_seconds: float) -> Tuple[List[float], np.ndarray]:
        """
        获取最近指定时长的数据
        
        Args:
            duration_seconds: 时长（秒）
            
        Returns:
            Tuple[List[float], np.ndarray]: (时间戳列表, 数据数组)
        """
        with self.lock:
            if len(self.timestamps) == 0:
                return [], np.array([])
            
            current_time = self.timestamps[-1]
            cutoff_time = current_time - duration_seconds
            
            # 找到需要的数据范围
            valid_indices = [i for i, ts in enumerate(self.timestamps) if ts >= cutoff_time]
            
            if not valid_indices:
                return [], np.array([])
            
            # 获取有效的数据
            recent_timestamps = [self.timestamps[i] for i in valid_indices]
            recent_data = np.array([self.data_buffer[i] for i in valid_indices])
            
            return recent_timestamps, recent_data
    
    def clear(self):
        """清空缓冲区"""
        with self.lock:
            self.timestamps.clear()
            self.data_buffer.clear()
            system_logger.info("TimeSeriesBuffer cleared")
    
    def get_stats(self) -> dict:
        """获取缓冲区统计信息"""
        with self.lock:
            return {
                'max_duration_seconds': self.max_duration_seconds,
                'current_duration': 0 if len(self.timestamps) == 0 else self.timestamps[-1] - self.timestamps[0],
                'sample_count': len(self.timestamps),
                'sample_rate': self.sample_rate
            }