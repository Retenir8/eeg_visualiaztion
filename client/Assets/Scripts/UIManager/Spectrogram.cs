/*
Unity客户端频谱图组件
显示EEG数据的频谱分析结果
*/

using UnityEngine;
using UnityEngine.UI;
using TMPro;
using System.Collections.Generic;

/// <summary>
/// 频谱图显示组件
/// 实时显示EEG数据的频谱分析
/// </summary>
public class Spectrogram : MonoBehaviour
{
    [Header("显示设置")]
    [SerializeField] private int spectrumWidth = 200;
    [SerializeField] private int spectrumHeight = 100;
    [SerializeField] private float updateInterval = 0.1f;
    
    [Header("频率设置")]
    [SerializeField] private float maxFrequency = 50.0f; // 最大显示频率
    [SerializeField] private int selectedChannel = 0; // 选择的通道
    
    [Header("UI引用")]
    [SerializeField] private RawImage spectrumImage;
    [SerializeField] private TextMeshProUGUI channelInfoText;
    [SerializeField] private Dropdown channelDropdown;
    [SerializeField] private Slider frequencyRangeSlider;
    
    // 频谱数据
    private float[] spectrumData;
    private float[] frequencyBands;
    private Texture2D spectrumTexture;
    private Color32[] spectrumPixels;
    
    // 更新控制
    private float lastUpdateTime = 0f;
    private Queue<float[]> spectrumHistory = new Queue<float[]>();
    private int maxHistoryFrames = 50;
    
    // 数据接收器
    private UDPDataReceiver dataReceiver;
    
    void Start()
    {
        InitializeSpectrumDisplay();
        SetupUI();
    }
    
    void Update()
    {
        UpdateSpectrumDisplay();
    }
    
    /// <summary>
    /// 初始化频谱显示
    /// </summary>
    private void InitializeSpectrumDisplay()
    {
        // 查找数据接收器
        dataReceiver = FindObjectOfType<UDPDataReceiver>();
        if (dataReceiver != null)
        {
            dataReceiver.OnDataReceived += OnDataReceived;
        }
        
        // 初始化频谱数据数组
        spectrumData = new float[spectrumWidth];
        frequencyBands = new float[spectrumWidth];
        
        // 计算频率对应的索引
        for (int i = 0; i < spectrumWidth; i++)
        {
            frequencyBands[i] = (i / (float)spectrumWidth) * maxFrequency;
        }
        
        // 创建纹理
        spectrumTexture = new Texture2D(spectrumWidth, spectrumHeight, TextureFormat.RGBA32, false);
        spectrumTexture.filterMode = FilterMode.Point;
        spectrumPixels = new Color32[spectrumWidth * spectrumHeight];
        
        // 清空纹理
        ClearSpectrumTexture();
        
        // 设置显示
        if (spectrumImage != null)
        {
            spectrumImage.texture = spectrumTexture;
        }
        
        Debug.Log("频谱图显示初始化完成");
    }
    
    /// <summary>
    /// 设置UI组件
    /// </summary>
    private void SetupUI()
    {
        // 设置通道下拉菜单
        if (channelDropdown != null)
        {
            channelDropdown.ClearOptions();
            List<string> channelOptions = new List<string>();
            for (int i = 0; i < 8; i++)
            {
                channelOptions.Add($"通道 {i + 1}");
            }
            channelDropdown.AddOptions(channelOptions);
            channelDropdown.onValueChanged.AddListener(OnChannelChanged);
            channelDropdown.value = selectedChannel;
        }
        
        // 设置频率范围滑块
        if (frequencyRangeSlider != null)
        {
            frequencyRangeSlider.minValue = 10f;
            frequencyRangeSlider.maxValue = 100f;
            frequencyRangeSlider.value = maxFrequency;
            frequencyRangeSlider.onValueChanged.AddListener(OnFrequencyRangeChanged);
        }
    }
    
    /// <summary>
    /// 数据接收回调
    /// </summary>
    private void OnDataReceived(float[] data)
    {
        Debug.Log($"[Spectrogram] OnDataReceived called length={data?.Length}");
        if (isPaused || data == null || data.Length == 0) return;
        
        // 数据格式：[s0_ch0, s0_ch1, ..., s0_ch7, s1_ch0, s1_ch1, ..., s_n_ch7]
        // 计算样本数
        int channels = 8; // 假设8通道
        int sampleCount = data.Length / channels;
        
        if (sampleCount == 0) return;
        
        // 计算频谱
        CalculateSpectrum(data, channels, sampleCount);
        
        // 添加到历史记录
        spectrumHistory.Enqueue(spectrumData);
        if (spectrumHistory.Count > maxHistoryFrames)
        {
            spectrumHistory.Dequeue();
        }
    }
    
    /// <summary>
    /// 计算频谱
    /// </summary>
    private void CalculateSpectrum(float[] allChannelData, int channels, int sampleCount)
    {
        if (allChannelData == null || allChannelData.Length == 0) return;
        
        // 提取选择通道的数据
        float[] selectedChannelData = new float[sampleCount];
        for (int i = 0; i < sampleCount; i++)
        {
            int dataIndex = i * channels + selectedChannel;
            if (dataIndex < allChannelData.Length)
            {
                selectedChannelData[i] = allChannelData[dataIndex];
            }
        }
        
        if (selectedChannelData.Length < 2) return;
        
        // 简化的频谱计算（实际应用中应该使用FFT）
        // 这里使用移动窗口平均值来模拟频谱
        int windowSize = Mathf.Max(2, selectedChannelData.Length / spectrumWidth);
        
        for (int i = 0; i < spectrumWidth; i++)
        {
            int startIndex = i * windowSize;
            int endIndex = Mathf.Min(startIndex + windowSize, selectedChannelData.Length);
            
            if (startIndex < endIndex)
            {
                float sum = 0f;
                for (int j = startIndex; j < endIndex; j++)
                {
                    sum += Mathf.Abs(selectedChannelData[j]);
                }
                spectrumData[i] = sum / (endIndex - startIndex);
            }
            else
            {
                spectrumData[i] = 0f;
            }
        }
        
        // 应用对数变换以增强可视化效果
        for (int i = 0; i < spectrumWidth; i++)
        {
            spectrumData[i] = Mathf.Log(spectrumData[i] + 0.001f);
        }
    }
    

    /// <summary>
    /// 更新频谱显示
    /// </summary>
    private void UpdateSpectrumDisplay()
    {
        if (Time.time - lastUpdateTime < updateInterval) return;
        lastUpdateTime = Time.time;
        
        if (spectrumHistory.Count == 0) return;
        
        // 清空纹理
        ClearSpectrumTexture();
        
        // 绘制频谱图（从历史记录构建热图）
        DrawSpectrogram();
        
        // 更新纹理
        spectrumTexture.SetPixels32(spectrumPixels);
        spectrumTexture.Apply();
        
        // 更新信息文本
        UpdateChannelInfo();
    }
    
    /// <summary>
    /// 绘制频谱图
    /// </summary>
    private void DrawSpectrogram()
    {
        int historyCount = spectrumHistory.Count;
        int maxHeight = spectrumHeight;
        
        // 从历史记录中获取数据并绘制
        List<float[]> historyList = new List<float[]>(spectrumHistory);
        
        for (int timeIndex = 0; timeIndex < historyCount && timeIndex < maxHeight; timeIndex++)
        {
            float[] currentSpectrum = historyList[historyCount - 1 - timeIndex]; // 最新的数据
            float maxValue = GetMaxValue(currentSpectrum);
            
            for (int freqIndex = 0; freqIndex < spectrumWidth; freqIndex++)
            {
                if (freqIndex < currentSpectrum.Length && maxValue > 0)
                {
                    float normalizedValue = currentSpectrum[freqIndex] / maxValue;
                    int pixelIndex = timeIndex * spectrumWidth + freqIndex;
                    
                    if (pixelIndex < spectrumPixels.Length)
                    {
                        // 根据值设置颜色（从蓝到红）
                        spectrumPixels[pixelIndex] = GetColorForValue(normalizedValue);
                    }
                }
            }
        }
    }
    
    /// <summary>
    /// 清空频谱纹理
    /// </summary>
    private void ClearSpectrumTexture()
    {
        for (int i = 0; i < spectrumPixels.Length; i++)
        {
            spectrumPixels[i] = new Color32(0, 0, 0, 255); // 黑色背景
        }
    }
    
    /// <summary>
    /// 根据值获取颜色
    /// </summary>
    private Color32 GetColorForValue(float value)
    {
        value = Mathf.Clamp01(value);
        
        // 简单的颜色映射：黑色 -> 蓝色 -> 绿色 -> 黄色 -> 红色
        if (value < 0.2f)
        {
            return new Color32(0, 0, (byte)(value * 5 * 255), 255);
        }
        else if (value < 0.4f)
        {
            float newValue = (value - 0.2f) * 5;
            return new Color32(0, (byte)(newValue * 255), (byte)((1 - newValue) * 255), 255);
        }
        else if (value < 0.6f)
        {
            float newValue = (value - 0.4f) * 5;
            return new Color32((byte)(newValue * 255), 255, 0, 255);
        }
        else if (value < 0.8f)
        {
            float newValue = (value - 0.6f) * 5;
            return new Color32(255, (byte)((1 - newValue) * 255), 0, 255);
        }
        else
        {
            float newValue = (value - 0.8f) * 5;
            return new Color32(255, 0, (byte)(newValue * 255), 255);
        }
    }
    
    /// <summary>
    /// 获取数组最大值
    /// </summary>
    private float GetMaxValue(float[] array)
    {
        if (array == null || array.Length == 0) return 1f;
        
        float max = float.MinValue;
        for (int i = 0; i < array.Length; i++)
        {
            if (array[i] > max) max = array[i];
        }
        
        return max > 0 ? max : 1f;
    }
    
    /// <summary>
    /// 更新通道信息显示
    /// </summary>
    private void UpdateChannelInfo()
    {
        if (channelInfoText == null) return;
        
        string info = $"频谱分析 - 通道 {selectedChannel + 1}\n" +
                     $"频率范围: 0 - {maxFrequency} Hz\n" +
                     $"帧数: {spectrumHistory.Count}\n" +
                     $"采样率: 约 250 Hz";
        
        channelInfoText.text = info;
    }
    
    /// <summary>
    /// 通道变化处理
    /// </summary>
    public void OnChannelChanged(int newChannel)
    {
        selectedChannel = newChannel;
        ClearHistory();
    }
    
    /// <summary>
    /// 频率范围变化处理
    /// </summary>
    public void OnFrequencyRangeChanged(float newRange)
    {
        maxFrequency = newRange;
        
        // 重新计算频率映射
        for (int i = 0; i < spectrumWidth; i++)
        {
            frequencyBands[i] = (i / (float)spectrumWidth) * maxFrequency;
        }
    }
    
    /// <summary>
    /// 清除历史记录
    /// </summary>
    public void ClearHistory()
    {
        spectrumHistory.Clear();
        ClearSpectrumTexture();
        if (spectrumImage != null && spectrumTexture != null)
        {
            spectrumTexture.SetPixels32(spectrumPixels);
            spectrumTexture.Apply();
        }
    }
    
    /// <summary>
    /// 清除显示
    /// </summary>
    public void ClearDisplay()
    {
        ClearHistory();
        
        if (spectrumImage != null)
        {
            spectrumImage.texture = null;
        }
    }
    
    // 暂停控制
    private bool isPaused = false;
    
    /// <summary>
    /// 设置暂停状态
    /// </summary>
    public void SetPaused(bool paused)
    {
        isPaused = paused;
    }
    
    /// <summary>
    /// 获取当前频谱数据
    /// </summary>
    public float[] GetCurrentSpectrum()
    {
        if (spectrumHistory.Count > 0)
        {
            List<float[]> historyList = new List<float[]>(spectrumHistory);
            return historyList[historyList.Count - 1];
        }
        return null;
    }
    
    void OnDestroy()
    {
        // 取消事件订阅
        if (dataReceiver != null)
        {
            dataReceiver.OnDataReceived -= OnDataReceived;
        }
        
        // 清理资源
        if (spectrumTexture != null)
        {
            Destroy(spectrumTexture);
        }
    }
}