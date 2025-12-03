"""
系统使用指南
提供详细的安装、配置和运行指导
"""

# 脑机接口系统使用指南

## 快速开始

### 1. 环境准备

**Python环境：**
```bash
# 安装Python依赖
pip install numpy scipy pyyaml matplotlib pygame

# 或使用requirements.txt
pip install -r requirements.txt
```

**Unity环境：**
- 下载并安装Unity Hub
- 安装Unity 2021.3或更新版本
- 创建新项目或导入现有项目

### 2. 配置设置

**服务端配置：**
```bash
# 编辑配置文件
nano server/config/settings.yaml

# 主要配置项：
# - OpenBCI设备端口
# - UDP通信端口
# - 采样率和通道数
# - 滤波器参数
```

**客户端配置：**
```csharp
// 在Unity中配置UDP连接参数
// DataReceiver.cs中设置：
private string serverIP = "127.0.0.1";  // 服务端IP
private int serverPort = 9999;          // 服务端端口
private int clientPort = 8888;          // 客户端端口
```

### 3. 运行系统

**启动Python服务端：**
```bash
cd server
python main.py
```

**预期输出：**
```
INFO - BrainComputerSystem initialized
INFO - Configuration loaded successfully
INFO - All components initialized successfully
INFO - OpenBCI device connected successfully
INFO - Started listening for UDP data on 127.0.0.1:9999
INFO - Brain Computer System started successfully!
```

**启动Unity客户端：**
1. 在Unity编辑器中打开项目
2. 播放场景
3. 检查连接状态

**预期结果：**
- Unity界面显示实时EEG波形
- 频谱图实时更新
- 3D大脑模型显示颜色变化

## 详细配置说明

### 硬件配置

**OpenBCI设备连接：**
```yaml
# config/settings.yaml
openbci:
  port: "/dev/ttyUSB0"        # Linux设备端口
  # port: "COM3"              # Windows设备端口
  # port: "/dev/tty.usbmodem" # macOS设备端口
  baud_rate: 115200
  sample_rate: 250
  num_channels: 8
```

**模拟模式（无硬件时）：**
```yaml
# 系统会自动使用模拟数据，无需特殊配置
# 模拟数据包含8个通道的合成EEG信号
```

### 网络配置

**UDP通信参数：**
```yaml
communication:
  udp:
    server_ip: "127.0.0.1"    # 服务端监听地址
    server_port: 9999         # 服务端监听端口
    client_ip: "127.0.0.1"    # 客户端地址
    client_port: 8888         # 客户端端口
    data_rate: 30             # 数据发送频率Hz
```

**网络诊断：**
```bash
# 检查端口是否被占用
netstat -an | grep 9999

# 测试UDP连接
nc -u 127.0.0.1 9999
```

### 信号处理配置

**滤波器设置：**
```yaml
signal_processing:
  bandpass_filter:
    low_cutoff: 1.0           # 高通滤波截止频率
    high_cutoff: 50.0         # 低通滤波截止频率
    order: 4                  # 滤波器阶数
  
  notch_filter:
    frequency: 50.0           # 工频陷波频率
    quality_factor: 30        # Q值
  
  # 自定义频带
  frequency_bands:
    delta: [1, 4]             # Delta波：1-4 Hz
    theta: [4, 8]             # Theta波：4-8 Hz
    alpha: [8, 13]            # Alpha波：8-13 Hz
    beta: [13, 30]            # Beta波：13-30 Hz
    gamma: [30, 50]           # Gamma波：30-50 Hz
```

**特征提取参数：**
```yaml
feature_extraction:
  window_size: 256            # 特征计算窗口大小
  overlap: 128                # 窗口重叠大小
```

## 功能测试

### 基础功能测试

**1. 数据采集测试：**
```bash
# 在服务端运行数据采集测试
cd server
python -c "
from data_acquisition.openbci_interface import OpenBCIInterface
from utils.logger import system_logger

# 创建接口实例
interface = OpenBCIInterface({'sample_rate': 250, 'num_channels': 8})

# 连接设备
if interface.connect():
    print('设备连接成功')
    interface.start_acquisition()
    
    # 获取数据样本
    for i in range(10):
        data = interface.get_latest_data(1)
        if data is not None:
            print(f'样本 {i+1}: {data[0]}')
        
        import time
        time.sleep(0.1)
    
    interface.stop_acquisition()
else:
    print('设备连接失败')
"
```

**2. 通信测试：**
```python
# 服务端发送测试数据
import json
import socket

# 发送测试数据包
test_data = {
    'type': 'eeg_data',
    'eeg_data': [[1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]],
    'timestamp': time.time()
}

json_data = json.dumps(test_data)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.sendto(json_data.encode('utf-8'), ('127.0.0.1', 8888))
```

**3. 信号处理测试：**
```python
# 测试滤波器和特征提取
import numpy as np
from signal_processing.preprocessor import EEGPreprocessor
from signal_processing.feature_extractor import FeatureExtractor

# 创建测试数据
test_data = np.random.randn(256, 8)

# 测试预处理
preprocessor = EEGPreprocessor(250)
filtered_data = preprocessor.apply_all_filters(test_data)

# 测试特征提取
extractor = FeatureExtractor(250)
features = extractor.extract_all_features(filtered_data)

print('特征提取结果：')
for key, value in features.items():
    print(f'{key}: {len(value)} 个特征')
```

### Unity客户端测试

**1. 连接测试：**
```csharp
// 在Unity中测试UDP连接
using UnityEngine;

public class ConnectionTest : MonoBehaviour
{
    void Start()
    {
        UDPDataReceiver receiver = FindObjectOfType<UDPDataReceiver>();
        if (receiver != null)
        {
            Debug.Log($"连接状态: {receiver.IsConnected}");
            Debug.Log($"缓冲区大小: {receiver.BufferSize}");
        }
    }
}
```

**2. 数据接收测试：**
```csharp
// 订阅数据接收事件
void Start()
{
    UDPDataReceiver receiver = FindObjectOfType<UDPDataReceiver>();
    receiver.OnDataReceived += OnDataReceived;
}

void OnDataReceived(float[] data)
{
    Debug.Log($"收到数据: {data.Length} 通道");
    for (int i = 0; i < Mathf.Min(data.Length, 3); i++)
    {
        Debug.Log($"通道 {i+1}: {data[i]:F2}");
    }
}
```

## 故障排除

### 常见问题及解决方案

**1. OpenBCI设备连接问题：**

**问题：**设备端口无法访问
```bash
# 检查设备列表
ls -l /dev/ttyUSB*

# 检查用户权限
sudo usermod -a -G dialout $USER

# 重启终端或重新登录
```

**问题：**波特率不匹配
```yaml
# 检查配置文件
openbci:
  baud_rate: 115200  # 确认为115200
```

**2. UDP通信问题：**

**问题：**端口被占用
```bash
# 查找占用端口的进程
lsof -i :9999

# 终止进程
kill -9 <PID>
```

**问题：**防火墙阻止
```bash
# Ubuntu/Debian
sudo ufw allow 9999

# CentOS/RHEL
sudo firewall-cmd --add-port=9999/udp --permanent
sudo firewall-cmd --reload
```

**3. Unity显示问题：**

**问题：**UI组件未连接
```csharp
// 检查组件引用
void Start()
{
    Debug.Log($"DataReceiver: {dataReceiver != null}");
    Debug.Log($"WaveformViewer: {waveformViewer != null}");
}
```

**问题：**数据格式不匹配
```csharp
// 添加数据验证
if (data != null && data.Length >= 8)
{
    // 处理数据
}
```

### 性能优化

**服务端优化：**
```yaml
# 调整缓冲区和线程设置
buffer:
  max_size: 500              # 减小缓冲区大小
communication:
  udp:
    data_rate: 20            # 降低数据率
```

**客户端优化：**
```csharp
// 减少UI更新频率
[SerializeField] private float updateInterval = 0.2f; // 增加到0.2秒

// 限制显示的数据量
[SerializeField] private int maxSamples = 100; // 减少到100样本
```

### 调试技巧

**启用详细日志：**
```yaml
# config/settings.yaml
logging:
  level: "DEBUG"             # 设置为DEBUG级别
  file_path: "./logs/debug.log"
```

**Unity调试模式：**
```csharp
// 启用调试信息
#define DEBUG_MODE

void OnDataReceived(float[] data)
{
    #if DEBUG_MODE
    Debug.Log($"数据详情: {string.Join(", ", data)}");
    #endif
}
```

**网络监控：**
```bash
# 使用Wireshark监控UDP流量
sudo wireshark -k -i lo udp port 9999
```

## 高级配置

### 自定义信号处理

**添加自定义滤波器：**
```python
# server/signal_processing/custom_filters.py
from scipy import signal
import numpy as np

class CustomPreprocessor(EEGPreprocessor):
    def __init__(self, sample_rate=250):
        super().__init__(sample_rate)
        self.setup_custom_filters()
    
    def setup_custom_filters(self):
        # 添加自定义滤波器
        self.custom_filter = signal.butter(4, [60/self.nyquist], btype='high')
    
    def apply_custom_filter(self, data):
        return signal.filtfilt(self.custom_filter[0], self.custom_filter[1], data)
```

**自定义特征提取：**
```python
# 自定义特征算法
def extract_custom_features(self, data):
    features = {}
    
    # 阿尔法波功率比
    alpha_power = self.get_band_power(data, 8, 13)
    beta_power = self.get_band_power(data, 13, 30)
    
    features['alpha_beta_ratio'] = alpha_power / (beta_power + 1e-10)
    
    return features
```

### 扩展可视化

**添加新的显示组件：**
```csharp
// 在Unity中创建新组件
public class CustomVisualizer : MonoBehaviour
{
    public void UpdateVisualization(float[] data)
    {
        // 实现自定义可视化逻辑
    }
}
```

### 性能监控

**添加性能统计：**
```python
import time
import psutil

class PerformanceMonitor:
    def __init__(self):
        self.start_time = time.time()
    
    def get_stats(self):
        return {
            'cpu_percent': psutil.cpu_percent(),
            'memory_percent': psutil.virtual_memory().percent,
            'uptime': time.time() - self.start_time
        }
```

## 系统监控

### 日志分析

**查看日志文件：**
```bash
# 实时查看日志
tail -f server/logs/system.log

# 搜索错误信息
grep "ERROR" server/logs/system.log

# 统计错误数量
grep "ERROR" server/logs/system.log | wc -l
```

**日志级别分析：**
```bash
# 按级别统计日志
grep -E "DEBUG|INFO|WARNING|ERROR" server/logs/system.log | \
awk '{print $4}' | sort | uniq -c
```

### 性能监控

**系统资源监控：**
```bash
# CPU和内存使用率
htop

# 网络活动
nethogs

# 磁盘使用
df -h
```

**应用性能监控：**
```python
# 在应用中集成性能监控
import cProfile

def run_with_profiling():
    cProfile.run('main()', 'performance_stats.prof')
```

## 维护指南

### 定期维护

**每日检查：**
- 检查系统运行状态
- 查看错误日志
- 监控资源使用

**每周检查：**
- 清理日志文件
- 更新依赖包
- 检查硬件连接

**每月检查：**
- 性能基准测试
- 数据备份
- 系统更新

### 备份策略

**配置备份：**
```bash
# 备份配置文件
cp -r server/config/ backup/config_$(date +%Y%m%d)/

# 备份日志文件
tar -czf backup/logs_$(date +%Y%m%d).tar.gz server/logs/
```

**数据备份：**
```bash
# 备份处理后的数据
if [ -d "data/processed" ]; then
    cp -r data/processed backup/processed_$(date +%Y%m%d)/
fi
```

### 故障恢复

**系统重启：**
```bash
# 优雅关闭
pkill -f "python main.py"

# 等待进程结束
sleep 5

# 重新启动
cd server && python main.py &
```

**配置重置：**
```bash
# 恢复默认配置
cp server/config/defaults.yaml server/config/settings.yaml

# 重启服务
./restart_system.sh
```

## 升级指南

### 版本升级

**检查当前版本：**
```python
# 在Python中检查版本
import pkg_resources
try:
    version = pkg_resources.get_distribution("brain-computer-system").version
    print(f"Current version: {version}")
except:
    print("Version info not available")
```

**升级步骤：**
1. 备份当前配置和数据
2. 下载新版本
3. 安装依赖更新
4. 更新配置文件
5. 测试系统功能

**兼容性检查：**
```bash
# 检查Python版本
python --version

# 检查依赖版本
pip list

# 检查配置文件格式
python -c "import yaml; yaml.safe_load(open('server/config/settings.yaml'))"
```

这个使用指南涵盖了脑机接口系统的各个方面，从基础配置到高级功能，为用户提供了完整的操作指导。