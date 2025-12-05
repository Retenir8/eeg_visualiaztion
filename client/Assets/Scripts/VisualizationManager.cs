/*
Unity客户端可视化总控制器
管理所有可视化组件的协调工作
*/

using UnityEngine;
using UnityEngine.UI;
using TMPro;

/// <summary>
/// 可视化总控制器
/// 统一管理EEG数据的显示和用户交互
/// </summary>
public class VisualizationManager : MonoBehaviour
{
    [Header("组件引用")]
    [SerializeField] private UDPDataReceiver dataReceiver;
    [SerializeField] private WaveformViewer waveformViewer;
    [SerializeField] private Spectrogram spectrogram;
    [SerializeField] private BrainMapper brainMapper;
    
    [Header("UI引用")]
    [SerializeField] private Canvas mainCanvas;
    [SerializeField] private TextMeshProUGUI connectionStatusText;
    [SerializeField] private TextMeshProUGUI dataInfoText;
    [SerializeField] private TextMeshProUGUI systemInfoText;
    [SerializeField] private Button clearDataButton;
    [SerializeField] private Button pauseButton;
    [SerializeField] private Slider amplitudeSlider;
    [SerializeField] private Toggle[] channelToggles;
    
    [Header("显示设置")]
    [SerializeField] private bool autoStart = true;
    [SerializeField] private float updateInterval = 0.1f; // UI更新间隔
    
    // 状态管理
    private bool isRunning = false;
    private bool isPaused = false;
    private bool isConnected = false;
    
    // 统计信息
    private float lastDataTime = 0f;
    private int totalDataCount = 0;
    private int currentChannelCount = 0;
    
    // 更新计时器
    private float lastUIUpdate = 0f;
    
    // 事件处理
    private System.Action<string, string> onStatusMessage;
    
    void Start()
    {
        InitializeComponents();
        SetupEventHandlers();
        
        if (autoStart)
        {
            StartVisualization();
        }
    }
    
    void Update()
    {
        // 增加最后数据接收的时间计数
        lastDataTime += Time.deltaTime;
        
        UpdateUI();
    }
    
    /// <summary>
    /// 初始化组件
    /// </summary>
    private void InitializeComponents()
    {
        // 查找组件
        if (dataReceiver == null)
            dataReceiver = FindObjectOfType<UDPDataReceiver>();
            
        if (waveformViewer == null)
            waveformViewer = FindObjectOfType<WaveformViewer>();
            
        if (spectrogram == null)
            spectrogram = FindObjectOfType<Spectrogram>();
            
        if (brainMapper == null)
            brainMapper = FindObjectOfType<BrainMapper>();
        
        // 设置UI按钮事件
        if (clearDataButton != null)
            clearDataButton.onClick.AddListener(ClearAllData);
            
        if (pauseButton != null)
            pauseButton.onClick.AddListener(TogglePause);
            
        if (amplitudeSlider != null)
            amplitudeSlider.onValueChanged.AddListener(OnAmplitudeChanged);
        
        // 初始化连接状态
        if (dataReceiver != null)
        {
            isConnected = dataReceiver.IsConnected;
        }
        
        Debug.Log("可视化管理器初始化完成");
    }
    
    /// <summary>
    /// 设置事件处理器
    /// </summary>
    private void SetupEventHandlers()
    {
        if (dataReceiver != null)
        {
            // 订阅状态消息
            dataReceiver.OnStatusReceived += OnStatusReceived;
            
            // [新增] 订阅数据消息
            dataReceiver.OnDataReceived += OnEEGDataReceived;
        }
    }
    
    /// <summary>
    /// 开始可视化
    /// </summary>
    public void StartVisualization()
    {
        if (isRunning) return;
        
        isRunning = true;
        isPaused = false;
        
        // 开始数据接收
        if (dataReceiver != null && !dataReceiver.IsConnected)
        {
            dataReceiver.StartReceiving();
        }
        
        UpdateUIButtonStates();
        UpdateStatusText("系统运行中");
        
        Debug.Log("可视化系统已启动");
    }
    
    /// <summary>
    /// 停止可视化
    /// </summary>
    public void StopVisualization()
    {
        if (!isRunning) return;
        
        isRunning = false;
        
        // 停止数据接收
        if (dataReceiver != null)
        {
            dataReceiver.StopReceiving();
        }
        
        UpdateUIButtonStates();
        UpdateStatusText("系统已停止");
        
        Debug.Log("可视化系统已停止");
    }
    
    /// <summary>
    /// 暂停/恢复可视化
    /// </summary>
    public void TogglePause()
    {
        isPaused = !isPaused;
        
        if (isPaused)
        {
            if (dataReceiver != null)
            {
                dataReceiver.StopReceiving();
            }
            UpdateStatusText("系统已暂停");
        }
        else
        {
            if (dataReceiver != null)
            {
                dataReceiver.StartReceiving();
            }
            UpdateStatusText("系统已恢复");
        }
        
        UpdateUIButtonStates();
    }
    
    /// <summary>
    /// 清除所有数据
    /// </summary>
    public void ClearAllData()
    {
        // 清除数据接收器的缓冲区
        if (dataReceiver != null)
        {
            dataReceiver.ClearBuffer();
        }
        
        // 清除各个可视化组件
        if (waveformViewer != null)
        {
            waveformViewer.ClearWaveform();
        }
        
        if (spectrogram != null)
        {
            spectrogram.ClearDisplay();
        }
        
        if (brainMapper != null)
        {
            brainMapper.ClearDisplay();
        }
        
        // 重置统计信息
        totalDataCount = 0;
        currentChannelCount = 0;
        lastDataTime = 0f;
        
        UpdateStatusText("所有数据已清除");
        Debug.Log("所有可视化数据已清除");
    }
    
    /// <summary>
    /// 处理连接状态变化
    /// </summary>
    private void OnStatusReceived(string status, string message)
    {
        isConnected = status.Contains("connected") || status == "server_connected";
        
        UpdateStatusText($"状态: {status} - {message}");
        
        // 根据状态更新UI
        switch (status)
        {
            case "server_connected":
                UpdateConnectionStatus("已连接", Color.green);
                break;
                
            case "server_disconnected":
                UpdateConnectionStatus("连接断开", Color.red);
                break;
                
            case "system_started":
                UpdateSystemInfo("服务器就绪");
                break;
                
            case "ping":
            case "pong":
                // 心跳消息，不需要特殊处理
                break;
                
            default:
                UpdateSystemInfo($"系统信息: {message}");
                break;
        }
    }
    
    /// <summary>
    /// 处理幅度变化
    /// </summary>
    private void OnAmplitudeChanged(float value)
    {
        if (waveformViewer != null)
        {
            waveformViewer.SetDisplayParameters(
                waveformViewer.GetComponent<WaveformViewer>().maxSamples, 
                value
            );
        }
    }
    
    /// <summary>
    /// 更新UI显示
    /// </summary>
    private void UpdateUI()
    {
        if (Time.time - lastUIUpdate < updateInterval) return;
        lastUIUpdate = Time.time;
        
        // 更新数据信息
        UpdateDataInfo();
        
        // 更新系统信息
        UpdateSystemInfo();
        
        // 更新连接状态
        if (dataReceiver != null)
        {
            bool newConnectionStatus = dataReceiver.IsConnected;
            if (newConnectionStatus != isConnected)
            {
                isConnected = newConnectionStatus;
                UpdateConnectionStatus(isConnected ? "已连接" : "未连接", 
                                     isConnected ? Color.green : Color.red);
            }
        }
    }
    
    /// <summary>
    /// 更新数据信息显示
    /// </summary>
    private void UpdateDataInfo()
    {
        if (dataInfoText == null) return;
        
        string info = $"数据统计:\n" +
                     $"总样本数: {totalDataCount}\n" +
                     $"当前通道: {currentChannelCount}\n" +
                     $"最后更新: {lastDataTime:F1}s 前\n" +
                     $"缓冲区: {dataReceiver?.BufferSize ?? 0}";
        
        dataInfoText.text = info;
    }
    
    /// <summary>
    /// 更新系统信息显示
    /// </summary>
    private void UpdateSystemInfo(string additionalInfo = "")
    {
        if (systemInfoText == null) return;
        
        string info = $"系统状态:\n" +
                     $"运行: {isRunning}\n" +
                     $"暂停: {isPaused}\n" +
                     $"连接: {isConnected}\n" +
                     $"FPS: {1f / Time.unscaledDeltaTime:F1}\n";
        
        if (!string.IsNullOrEmpty(additionalInfo))
        {
            info += $"消息: {additionalInfo}\n";
        }
        
        systemInfoText.text = info;
    }
    
    /// <summary>
    /// 更新连接状态显示
    /// </summary>
    private void UpdateConnectionStatus(string status, Color color)
    {
        if (connectionStatusText == null) return;
        
        connectionStatusText.text = $"连接状态: {status}";
        connectionStatusText.color = color;
    }
    
    /// <summary>
    /// 更新状态文本
    /// </summary>
    private void UpdateStatusText(string message)
    {
        Debug.Log($"系统状态: {message}");
        // 可以在这里添加状态栏更新逻辑
    }
    
    /// <summary>
    /// 更新UI按钮状态
    /// </summary>
    private void UpdateUIButtonStates()
    {
        if (pauseButton != null)
        {
            pauseButton.GetComponentInChildren<TextMeshProUGUI>().text = isPaused ? "恢复" : "暂停";
        }
        
        // 更新其他按钮状态
        // 可以根据运行状态启用/禁用某些功能
    }
    
    /// <summary>
    /// 通道显示控制
    /// </summary>
    public void ToggleChannel(int channelIndex)
    {
        if (channelToggles != null && channelIndex < channelToggles.Length && channelToggles[channelIndex] != null)
        {
            bool isEnabled = channelToggles[channelIndex].isOn;
            
            // 更新波形显示
            if (waveformViewer != null)
            {
                // 这里可以添加通道特定的显示控制逻辑
            }
            
            // 更新脑图显示
            if (brainMapper != null)
            {
                // 这里可以添加脑图通道控制逻辑
            }
        }
    }
    
    /// <summary>
    /// 获取系统状态信息
    /// </summary>
    public SystemInfo GetSystemInfo()
    {
        return new SystemInfo
        {
            IsRunning = isRunning,
            IsPaused = isPaused,
            IsConnected = isConnected,
            TotalDataCount = totalDataCount,
            CurrentChannelCount = currentChannelCount,
            BufferSize = dataReceiver?.BufferSize ?? 0,
            Fps = 1f / Time.unscaledDeltaTime
        };
    }
    
    /// <summary>
    /// 系统信息数据结构
    /// </summary>
    [System.Serializable]
    public struct SystemInfo
    {
        public bool IsRunning;
        public bool IsPaused;
        public bool IsConnected;
        public int TotalDataCount;
        public int CurrentChannelCount;
        public int BufferSize;
        public float Fps;
    }

    /// <summary>
    /// 处理接收到的EEG数据包
    /// </summary>
    /// <param name="data">包含所有通道数据的一维数组</param>
    private void OnEEGDataReceived(float[] data)
    {
        // 1. 更新统计数据
        if (data != null && data.Length > 0)
        {
            // 假设这里接收的是单帧或多帧的扁平化数据
            // 如果要精确计算样本数（Timepoints），需要知道通道数。
            // 暂时简单处理：每次回调视为收到一批数据，更新最后时间
            
            // 这里的 totalDataCount 简单累加接收到的数据点总数，或者您可以定义为样本包数量
            totalDataCount += data.Length; 
            lastDataTime = 0f; // 重置"最后更新"计时
            
            // 尝试推断通道数（如果有 WaveformViewer 设置，或者根据数据长度）
            // 这是一个估算，实际应该从配置读取
            if (dataReceiver != null && currentChannelCount == 0)
            {
                // 尝试获取通道数据的逻辑（此处仅为示例，实际可能需要从配置获取）
                 currentChannelCount = 8; // 默认OpenBCI通道数
            }
        }

        // 2. 将数据传递给可视化组件 (波形图)
        if (waveformViewer != null && isRunning && !isPaused)
        {
            // 注意：WaveformViewer 需要根据您的具体实现来调用更新方法
            // 假设 WaveformViewer 有一个 UpdateData 或类似方法
            // waveformViewer.UpdateData(data); 
            
            // 如果 WaveformViewer 是基于拉取(Pull)模式的（即在Update中自己去dataReceiver取数据），
            // 那么这一步可能不需要。但通常是推(Push)模式效率更高。
        }

        // 3. 传递给其他组件 (如脑图、频谱)
        // if (brainMapper != null) brainMapper.UpdateData(data);
    }
    
    void OnDestroy()
    {
        // 清理事件订阅
        if (dataReceiver != null)
        {
            dataReceiver.OnStatusReceived -= OnStatusReceived;
            
            // [新增] 取消订阅
            dataReceiver.OnDataReceived -= OnEEGDataReceived;
        }
    }
}