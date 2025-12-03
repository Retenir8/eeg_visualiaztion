# 脑机接口系统

基于OpenBCI硬件的实时脑电信号采集、处理与可视化系统

## 项目概述

本项目是一个完整的脑机接口（BCI）系统，提供实时脑电信号采集、处理和可视化功能。系统采用Python服务端 + Unity客户端的架构，通过UDP通信实现数据的实时传输。

## 系统架构

```
brain-computer-system/
├── server/                  # Python服务端
│   ├── main.py             # 主程序入口
│   ├── config/             # 配置文件
│   ├── data_acquisition/   # 数据采集模块
│   ├── signal_processing/  # 信号处理模块
│   ├── communication/      # 通信模块
│   └── utils/              # 工具模块
├── client/                 # Unity客户端
│   ├── Assets/Scripts/     # C#脚本
│   │   ├── UIManager/     # UI组件
│   │   └── 其他脚本
│   └── ProjectSettings/    # Unity设置
├── docs/                   # 文档目录
└── tests/                  # 测试用例
```

## 功能特性

### 1. 数据采集模块
- **OpenBCI接口**：支持与OpenBCI硬件设备通信
- **模拟模式**：当没有硬件时提供模拟数据
- **多通道支持**：支持最多8通道EEG数据采集
- **数据缓冲**：高效的环形缓冲区管理

### 2. 信号处理模块
- **实时滤波**：带通滤波和陷波滤波
- **伪迹去除**：自动检测和处理EEG伪迹
- **特征提取**：
  - 频域特征：功率谱密度、频带功率
  - 时域特征：均值、标准差、零交叉率
  - 频谱特征：频谱重心、频谱带宽

### 3. 通信模块
- **UDP通信**：低延迟数据传输
- **数据序列化**：JSON格式，支持压缩
- **双向通信**：支持客户端请求和服务端推送
- **错误处理**：网络异常自动重连

### 4. Unity客户端
- **实时波形显示**：多通道EEG波形可视化
- **频谱图**：EEG信号频域分析显示
- **3D大脑映射**：将EEG信号映射到3D大脑模型
- **交互控制**：用户可调节显示参数

## 安装和使用

### 系统要求

**Python服务端：**
- Python 3.8+
- 依赖包：`pip install -r requirements.txt`

**Unity客户端：**
- Unity 2021.3+
- .NET Framework 4.7.1+

### 安装步骤

1. **安装Python依赖**
```bash
cd brain-computer-system/server
pip install -r requirements.txt
```

2. **配置系统参数**
编辑 `server/config/settings.yaml`：
```yaml
# OpenBCI设备设置
openbci:
  port: "/dev/ttyUSB0"  # 设备端口
  baud_rate: 115200     # 波特率
  sample_rate: 250      # 采样率

# 通信设置
communication:
  udp:
    server_ip: "127.0.0.1"    # 服务端IP
    server_port: 9999         # 服务端端口
    client_ip: "127.0.0.1"    # 客户端IP
    client_port: 8888         # 客户端端口
```

3. **启动系统**

**启动Python服务端：**
```bash
cd server
python main.py
```

**启动Unity客户端：**
1. 在Unity中打开 `client` 目录
2. 构建并运行项目
3. 确保UDP端口配置正确

## 使用说明

### 基础操作

1. **连接硬件**：系统启动后自动连接OpenBCI设备（模拟模式下使用模拟数据）
2. **数据采集**：实时采集EEG信号并进行处理
3. **数据传输**：处理后的数据通过UDP发送到Unity客户端
4. **可视化显示**：Unity客户端实时显示EEG波形、频谱图和3D大脑映射

### 客户端功能

**波形显示：**
- 实时显示8通道EEG波形
- 可调节振幅缩放和显示时长
- 支持通道开关控制

**频谱分析：**
- 实时频谱图显示
- 通道选择和频率范围调节
- 颜色编码的频谱强度

**3D大脑映射：**
- 将EEG信号映射到3D大脑模型
- 颜色表示信号强度
- 支持电极位置自定义

### 控制面板

- **开始/暂停**：控制数据采集
- **清除数据**：清空所有缓冲区
- **通道控制**：单独控制各通道显示
- **参数调节**：实时调节显示参数

## 配置说明

### 核心配置文件

`server/config/settings.yaml` 包含所有系统配置：

```yaml
# 数据采集配置
openbci:
  sample_rate: 250        # 采样率 Hz
  num_channels: 8         # 通道数
  port: "/dev/ttyUSB0"    # 设备端口

# 信号处理配置
signal_processing:
  bandpass_filter:
    low_cutoff: 1.0       # 低频截止 Hz
    high_cutoff: 50.0     # 高频截止 Hz
  notch_filter:
    frequency: 50.0       # 陷波频率 Hz
  
# 频带定义
frequency_bands:
  delta: [1, 4]          # Delta波
  theta: [4, 8]          # Theta波
  alpha: [8, 13]         # Alpha波
  beta: [13, 30]         # Beta波
  gamma: [30, 50]        # Gamma波

# 通信配置
communication:
  udp:
    data_rate: 30         # 数据发送频率 Hz
    buffer_size: 1024     # 缓冲区大小
```

## API参考

### Python服务端API

#### 核心类

**BrainComputerSystem**
```python
class BrainComputerSystem:
    def start() -> bool:      # 启动系统
    def shutdown():          # 关闭系统
    def get_status() -> dict: # 获取系统状态
```

**OpenBCIInterface**
```python
class OpenBCIInterface:
    def connect() -> bool:           # 连接设备
    def start_acquisition():         # 开始采集
    def get_latest_data(n) -> array: # 获取数据
```

**EEGPreprocessor**
```python
class EEGPreprocessor:
    def apply_all_filters(data):     # 应用所有滤波器
    def remove_artifacts(data):      # 去除伪迹
```

**FeatureExtractor**
```python
class FeatureExtractor:
    def extract_frequency_band_power(data):  # 频带功率
    def extract_time_domain_features(data):  # 时域特征
```

### Unity客户端API

#### 主要组件

**UDPDataReceiver**
```csharp
public class UDPDataReceiver : MonoBehaviour
{
    public event System.Action<float[]> OnDataReceived;
    public void StartReceiving();  // 开始接收
    public void StopReceiving();   // 停止接收
}
```

**WaveformViewer**
```csharp
public class WaveformViewer : MonoBehaviour
{
    public void SetDisplayParameters(int samples, float scale);
    public void ClearWaveform();   // 清除波形
}
```

**VisualizationManager**
```csharp
public class VisualizationManager : MonoBehaviour
{
    public void StartVisualization();  // 开始可视化
    public void StopVisualization();   // 停止可视化
    public void ClearAllData();        // 清除所有数据
}
```

## 故障排除

### 常见问题

1. **OpenBCI设备连接失败**
   - 检查设备端口设置
   - 确认设备权限
   - 验证波特率设置

2. **UDP通信问题**
   - 检查防火墙设置
   - 确认IP地址和端口正确
   - 验证网络连接

3. **数据质量差**
   - 检查电极接触
   - 调整滤波参数
   - 设置合适的采样率

4. **Unity客户端显示异常**
   - 检查渲染设置
   - 验证UI组件连接
   - 确认数据类型匹配

### 调试模式

启用详细日志：
```yaml
# config/settings.yaml
logging:
  level: "DEBUG"  # 详细级别
```

Unity客户端日志：
- Console窗口显示所有调试信息
- UI状态文本显示连接状态

## 开发指南

### 扩展功能

**添加新的信号处理算法：**
1. 在 `signal_processing/` 目录创建新模块
2. 继承基础处理类
3. 在主程序中注册新算法

**添加新的可视化组件：**
1. 在 `client/Assets/Scripts/` 创建新脚本
2. 继承基础可视化类
3. 在 `VisualizationManager` 中注册

**添加新的通信协议：**
1. 在 `communication/` 目录创建新模块
2. 实现标准通信接口
3. 更新配置和主程序

### 测试

**单元测试：**
```bash
cd tests/unit_tests
python test_signal_processing.py
python test_communication.py
```

**集成测试：**
```bash
cd tests/integration_tests
python test_full_system.py
```

## 技术规范

### 性能要求

- **延迟**：端到端延迟 < 100ms
- **采样率**：250Hz（可配置）
- **通道数**：最多8通道
- **数据率**：30Hz（可配置）

### 兼容性

- **Python**：3.8+
- **Unity**：2021.3+
- **操作系统**：Windows/Linux/macOS
- **OpenBCI**：Cyton/Daisy系列

### 数据格式

**EEG数据格式：**
```json
{
  "type": "eeg_data",
  "eeg_data": [[ch1, ch2, ...], ...],  // 多通道数据
  "features": {...},                    // 特征数据
  "timestamp": 1634567890.123
}
```

## 贡献指南

欢迎贡献代码和建议！请遵循以下步骤：

1. Fork项目仓库
2. 创建功能分支
3. 提交代码变更
4. 创建Pull Request

## 许可证

本项目采用MIT许可证，详见LICENSE文件。

## 联系方式

- 项目维护者：[您的联系信息]
- 技术支持：[邮箱或论坛链接]

## 更新日志

### v1.0.0 (当前版本)
- 完整的EEG数据采集系统
- 实时信号处理和特征提取
- Unity客户端可视化界面
- UDP双向通信

### 计划功能
- [ ] 高级机器学习算法
- [ ] 云端数据存储
- [ ] 多用户支持
- [ ] Web界面版本