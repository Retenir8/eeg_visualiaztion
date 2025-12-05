"""
OpenBCI接口模块
提供与OpenBCI硬件设备的通信接口（基础版本使用模拟数据）
"""

import time
import numpy as np
import threading
from typing import Callable, List, Optional
from .data_buffer import MultiChannelBuffer
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

class OpenBCISimulator:
    """OpenBCI模拟器 - 基础版本使用模拟数据"""
    
    def __init__(self, port: str = "/dev/ttyUSB0", baud_rate: int = 115200, 
                 sample_rate: int = 250, num_channels: int = 8):
        """
        初始化OpenBCI模拟器
        
        Args:
            port: 串口端口
            baud_rate: 波特率
            sample_rate: 采样率（Hz）
            num_channels: 通道数
        """
        self.port = port
        self.baud_rate = baud_rate
        self.sample_rate = sample_rate
        self.num_channels = num_channels
        self.is_streaming = False
        self.data_callback: Optional[Callable] = None
        self.sample_interval = 1.0 / sample_rate
        self.last_sample_time = 0.0
        
        # 模拟数据参数
        self.base_frequencies = [10, 20, 30, 40, 25, 15, 35, 45]  # 每个通道的基础频率
        self.noise_level = 0.1  # 噪声水平
        self.artifacts_probability = 0.01  # 伪迹概率
        
        system_logger.info(f"OpenBCISimulator initialized: {num_channels} channels at {sample_rate} Hz")
    
    def connect(self) -> bool:
        """
        连接到OpenBCI设备（模拟）
        
        Returns:
            bool: 连接是否成功
        """
        try:
            system_logger.info(f"Connecting to OpenBCI device at {self.port}")
            # 模拟连接延迟
            time.sleep(0.5)
            
            system_logger.info("OpenBCI device connected successfully")
            return True
        except Exception as e:
            system_logger.error(f"Failed to connect to OpenBCI device: {e}")
            return False
    
    def disconnect(self):
        """断开OpenBCI设备连接"""
        if self.is_streaming:
            self.stop_streaming()
        
        system_logger.info("OpenBCI device disconnected")
    
    def start_streaming(self, callback: Callable[[List[float], float], None]):
        """
        开始数据流
        
        Args:
            callback: 数据回调函数，接收(通道数据, 时间戳)
        """
        if self.is_streaming:
            system_logger.warning("Already streaming, ignoring start request")
            return
        
        self.data_callback = callback
        self.is_streaming = True
        
        # 在独立线程中运行数据生成
        self.streaming_thread = threading.Thread(target=self._generate_data_stream, daemon=True)
        self.streaming_thread.start()
        
        system_logger.info("Started data streaming")
    
    def stop_streaming(self):
        """停止数据流"""
        if not self.is_streaming:
            return
        
        self.is_streaming = False
        
        # 等待线程结束
        if hasattr(self, 'streaming_thread'):
            self.streaming_thread.join(timeout=1.0)
        
        system_logger.info("Stopped data streaming")
    
    def _generate_data_stream(self):
        """生成模拟数据流"""
        self.last_sample_time = time.time()
        
        while self.is_streaming:
            current_time = time.time()
            
            # 确保按照正确的时间间隔生成数据
            if current_time - self.last_sample_time >= self.sample_interval:
                # 生成模拟EEG数据
                channels_data = self._generate_sample()
                timestamp = current_time
                
                # 调用回调函数
                if self.data_callback:
                    self.data_callback(channels_data, timestamp)
                
                self.last_sample_time = current_time
            
            # 短暂休眠，避免CPU占用过高
            time.sleep(0.001)
    
    def _generate_sample(self) -> List[float]:
        """
        生成一个模拟的EEG样本 - 8个通道，每个通道有不同的波形特征
        用于Unity可视化测试
        """
        sample = []
        current_time = time.time()
        
        for i in range(self.num_channels):
            # 为每个通道生成特定的频率成分
            t = current_time
            base_freq = self.base_frequencies[i]
            
            # Channel 0-1: Alpha频率 (10-12 Hz) - 视觉通道特征
            if i < 2:
                signal = np.sin(2 * np.pi * base_freq * t) * 50.0
                signal += np.sin(2 * np.pi * (base_freq * 0.5) * t) * 20.0
            
            # Channel 2-3: Beta频率 (15-20 Hz) - 运动通道特征
            elif i < 4:
                signal = np.sin(2 * np.pi * base_freq * t) * 40.0
                signal += np.sin(2 * np.pi * (base_freq * 1.2) * t) * 25.0
            
            # Channel 4-5: Theta频率 (4-8 Hz) - 认知通道特征
            elif i < 6:
                signal = np.sin(2 * np.pi * (base_freq * 0.5) * t) * 30.0
                signal += np.sin(2 * np.pi * (base_freq * 0.25) * t) * 15.0
            
            # Channel 6-7: Gamma频率 (30-45 Hz) - 高频活动
            else:
                signal = np.sin(2 * np.pi * base_freq * t) * 35.0
                signal += np.sin(2 * np.pi * (base_freq * 0.8) * t) * 20.0
            
            # 添加小幅随机噪声
            noise = np.random.normal(0, self.noise_level) * 5.0
            signal += noise
            
            # 偶尔添加伪迹
            if np.random.random() < self.artifacts_probability:
                artifact = np.random.normal(0, 50.0)
                signal += artifact
            
            # 限制信号范围在合理的脑电图范围内 (-500 to 500 microvolts)
            signal = np.clip(signal, -500.0, 500.0)
            
            sample.append(float(signal))
        
        return sample
    
    def get_device_info(self) -> dict:
        """获取设备信息"""
        return {
            'port': self.port,
            'baud_rate': self.baud_rate,
            'sample_rate': self.sample_rate,
            'num_channels': self.num_channels,
            'is_streaming': self.is_streaming,
            'device_type': 'OpenBCI Simulator'
        }
    
    def set_channel_settings(self, channel: int, gain: int = 24, enabled: bool = True):
        """
        设置通道参数
        
        Args:
            channel: 通道索引 (0-7)
            gain: 增益设置
            enabled: 是否启用通道
        """
        system_logger.info(f"Setting channel {channel}: gain={gain}, enabled={enabled}")
    
    def apply_test_signal(self, channel: int, signal_type: str = 'square'):
        """
        对指定通道应用测试信号
        
        Args:
            channel: 通道索引
            signal_type: 信号类型 ('square', 'sine', 'none')
        """
        system_logger.info(f"Applying {signal_type} test signal to channel {channel}")

class OpenBCIInterface:
    """OpenBCI接口类 - 统一的访问接口"""
    
    def __init__(self, config: dict):
        """
        初始化OpenBCI接口
        
        Args:
            config: 配置字典
        """
        self.config = config
        self.device = None
        self.data_buffer = None
        self.is_connected = False
        
        # 从配置中获取参数
        port = config.get('port', '/dev/ttyUSB0')
        baud_rate = config.get('baud_rate', 115200)
        sample_rate = config.get('sample_rate', 250)
        num_channels = config.get('num_channels', 8)
        
        # 初始化设备（基础版本使用模拟器）
        self.device = OpenBCISimulator(port, baud_rate, sample_rate, num_channels)
        
        # 初始化数据缓冲区
        buffer_size = int(sample_rate * 10)  # 存储10秒的数据
        self.data_buffer = MultiChannelBuffer(buffer_size, num_channels)
        
        system_logger.info("OpenBCIInterface initialized")
    
    def connect(self) -> bool:
        """连接到设备"""
        try:
            success = self.device.connect() # pyright: ignore[reportOptionalMemberAccess]
            if success:
                self.is_connected = True
                system_logger.info("Successfully connected to OpenBCI device")
            return success
        except Exception as e:
            system_logger.error(f"Failed to connect to OpenBCI device: {e}")
            return False
    
    def start_acquisition(self):
        """开始数据采集"""
        if not self.is_connected:
            system_logger.error("Device not connected")
            return False
        
        def data_callback(channels_data, timestamp):
            """数据回调函数"""
            try:
                # 添加数据到缓冲区
                self.data_buffer.push_sample(channels_data) # pyright: ignore[reportOptionalMemberAccess]
                
                # 记录采集信息（调试）
                # if len(channels_data) > 0:
                #     system_logger.debug(f"Acquired sample: {channels_data[0]:.2f} (ch1)")
            except Exception as e:
                system_logger.error(f"Error in data callback: {e}")
        
        self.device.start_streaming(data_callback) # pyright: ignore[reportOptionalMemberAccess]
        return True
    
    def stop_acquisition(self):
        """停止数据采集"""
        if self.device:
            self.device.stop_streaming()
        system_logger.info("Data acquisition stopped")
    
    def disconnect(self):
        """断开连接"""
        if self.device:
            self.device.disconnect()
        self.is_connected = False
        system_logger.info("Device disconnected")
    
    def get_latest_data(self, n_samples: int = 250) -> Optional[np.ndarray]:
        """
        获取最新的EEG数据
        
        Args:
            n_samples: 要获取的样本数
            
        Returns:
            np.ndarray: EEG数据，形状为 (n_samples, num_channels)
        """
        if not self.is_connected:
            return None
        
        return self.data_buffer.get_all_channels(n_samples) # pyright: ignore[reportOptionalMemberAccess]
    
    def get_channel_data(self, channel_idx: int, n_samples: int = 250) -> Optional[np.ndarray]:
        """
        获取指定通道的数据
        
        Args:
            channel_idx: 通道索引
            n_samples: 要获取的样本数
            
        Returns:
            np.ndarray: 通道数据
        """
        if not self.is_connected:
            return None
        
        return self.data_buffer.get_channel_data(channel_idx, n_samples) # pyright: ignore[reportOptionalMemberAccess]
    
    def get_device_info(self) -> dict:
        """获取设备信息"""
        if not self.device:
            return {}
        
        info = self.device.get_device_info()
        buffer_stats = self.data_buffer.get_stats() # pyright: ignore[reportOptionalMemberAccess]
        
        return {
            'device': info,
            'buffer': buffer_stats,
            'is_connected': self.is_connected
        }