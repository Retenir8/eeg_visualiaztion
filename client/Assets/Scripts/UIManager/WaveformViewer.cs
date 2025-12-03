/*
Unity客户端波形显示组件
实时显示EEG波形数据
*/

using UnityEngine;
using UnityEngine.UI;
using System.Collections.Generic;
using TMPro;

/// <summary>
/// EEG波形显示组件
/// 使用LineRenderer实时显示多通道EEG波形
/// </summary>
public class WaveformViewer : MonoBehaviour
{
    [Header("显示设置")]
    [SerializeField] private int maxChannels = 8;
    [SerializeField] public int maxSamples = 256; // 显示的样本数量
    [SerializeField] private float displayDuration = 2.0f; // 显示时长（秒）
    [SerializeField] private float verticalSpacing = 1.5f; // 通道间垂直间距
    
    [Header("波形样式")]
    [SerializeField] private float lineWidth = 0.5f;
    [SerializeField] private Color[] channelColors;
    
    [Header("UI引用")]
    [SerializeField] private Canvas canvas;
    [SerializeField] private RectTransform waveformContainer;
    [SerializeField] private TextMeshProUGUI statusText;
    
    // 数据接收器引用
    private UDPDataReceiver dataReceiver;
    
    // 波形渲染器
    private List<LineRenderer> channelRenderers = new List<LineRenderer>();
    private List<GameObject> channelObjects = new List<GameObject>();
    
    // 数据存储
    private Queue<float[]> channelDataBuffers = new Queue<float[]>();
    private int currentSampleIndex = 0;
    
    // 显示参数
    private float sampleSpacing;
    private float amplitudeScale = 0.5f; // 振幅缩放因子
    
    void Start()
    {
        InitializeComponents();
        SetupWaveformDisplay();
    }
    
    void Update()
    {
        UpdateWaveformDisplay();
    }
    
    /// <summary>
    /// 初始化组件
    /// </summary>
    private void InitializeComponents()
    {
        // 查找数据接收器
        dataReceiver = FindObjectOfType<UDPDataReceiver>();
        if (dataReceiver != null)
        {
            dataReceiver.OnDataReceived += OnDataReceived;
        }
        
        // 初始化颜色数组
        if (channelColors == null || channelColors.Length == 0)
        {
            channelColors = new Color[]
            {
                Color.red, Color.green, Color.blue, Color.yellow,
                Color.cyan, Color.magenta, Color.white, Color.gray
            };
        }
        
        Debug.Log("波形显示组件初始化完成");
    }
    
    /// <summary>
    /// 设置波形显示
    /// </summary>
    private void SetupWaveformDisplay()
    {
        if (waveformContainer == null)
        {
            // 如果没有指定容器，创建一个
            waveformContainer = GetComponent<RectTransform>();
            if (waveformContainer == null)
            {
                Debug.LogError("未找到波形容器RectTransform");
                return;
            }
        }
        
        // 计算样本间距
        sampleSpacing = waveformContainer.rect.width / maxSamples;
        
        // 创建每个通道的LineRenderer
        for (int i = 0; i < maxChannels; i++)
        {
            CreateChannelRenderer(i);
        }
        
        // 初始化数据缓冲区
        for (int i = 0; i < displayDuration * 30; i++) // 假设30Hz采样率
        {
            channelDataBuffers.Enqueue(new float[maxChannels]);
        }
        
        UpdateStatusText("等待EEG数据...");
    }
    
    /// <summary>
    /// 创建通道渲染器
    /// </summary>
    private void CreateChannelRenderer(int channelIndex)
    {
        // 创建通道对象
        GameObject channelObject = new GameObject($"Channel_{channelIndex}");
        channelObject.transform.SetParent(waveformContainer);
        
        // 设置位置
        float yPosition = (maxChannels - 1 - channelIndex) * verticalSpacing - (maxChannels * verticalSpacing / 2);
        channelObject.transform.localPosition = new Vector3(0, yPosition, 0);
        
        // 创建LineRenderer
        LineRenderer lineRenderer = channelObject.AddComponent<LineRenderer>();
        lineRenderer.material = new Material(Shader.Find("UI/Default"));
        lineRenderer.startWidth = lineWidth;
        lineRenderer.endWidth = lineWidth;
        lineRenderer.positionCount = maxSamples;
        
        // 设置颜色
        if (channelIndex < channelColors.Length)
        {
            lineRenderer.startColor = channelColors[channelIndex];
            lineRenderer.endColor = channelColors[channelIndex];
        }
        else
        {
            lineRenderer.startColor = Color.white;
            lineRenderer.endColor = Color.white;
        }
        
        // 初始化位置
        Vector3[] positions = new Vector3[maxSamples];
        for (int i = 0; i < maxSamples; i++)
        {
            positions[i] = new Vector3(i * sampleSpacing, 0, 0);
        }
        lineRenderer.SetPositions(positions);
        
        // 存储引用
        channelRenderers.Add(lineRenderer);
        channelObjects.Add(channelObject);
    }
    
    /// <summary>
    /// 接收数据回调
    /// </summary>
    private void OnDataReceived(float[] data)
    {
        Debug.Log($"[WaveformViewer] OnDataReceived called length={data?.Length}");
        // 检查数据长度
        if (data == null || data.Length < maxChannels) return;
        
        // 数据格式：[s0_ch0, s0_ch1, ..., s0_ch7, s1_ch0, s1_ch1, ..., s_n_ch7]
        // 计算样本数
        int sampleCount = data.Length / maxChannels;
        
        lock (channelDataBuffers)
        {
            // 分解为各个通道的样本
            for (int sampleIdx = 0; sampleIdx < sampleCount; sampleIdx++)
            {
                float[] channelData = new float[maxChannels];
                for (int ch = 0; ch < maxChannels; ch++)
                {
                    int dataIndex = sampleIdx * maxChannels + ch;
                    if (dataIndex < data.Length)
                    {
                        channelData[ch] = data[dataIndex] * amplitudeScale; // 应用缩放
                    }
                }
                
                channelDataBuffers.Enqueue(channelData);
                
                // 限制缓冲区大小
                while (channelDataBuffers.Count > displayDuration * 30)
                {
                    channelDataBuffers.Dequeue();
                }
            }
        }
        
        // 更新状态文本
        if (statusText != null)
        {
            statusText.text = $"接收 {sampleCount} 样本 × {maxChannels} 通道";
        }
    }
    
    /// <summary>
    /// 更新波形显示
    /// </summary>
    private void UpdateWaveformDisplay()
    {
        if (channelRenderers.Count == 0 || channelDataBuffers.Count == 0) return;
        
        lock (channelDataBuffers)
        {
            // 转换队列为数组
            float[][] dataArray = new float[channelDataBuffers.Count][];
            int index = 0;
            foreach (float[] data in channelDataBuffers)
            {
                dataArray[index++] = data;
            }
            
            // 更新每个通道的LineRenderer
            for (int channel = 0; channel < channelRenderers.Count && channel < maxChannels; channel++)
            {
                UpdateChannelRenderer(channelRenderers[channel], dataArray, channel);
            }
        }
    }
    
    /// <summary>
    /// 更新单个通道的LineRenderer
    /// </summary>
    private void UpdateChannelRenderer(LineRenderer renderer, float[][] dataArray, int channelIndex)
    {
        if (renderer == null || dataArray.Length == 0) return;
        
        Vector3[] positions = new Vector3[maxSamples];
        int dataLength = dataArray.Length;
        
        // 如果数据不足，使用现有数据填充
        if (dataLength < maxSamples)
        {
            // 计算起始位置
            int startPos = maxSamples - dataLength;
            
            // 清空前面的位置
            for (int i = 0; i < startPos; i++)
            {
                positions[i] = new Vector3(i * sampleSpacing, 0, 0);
            }
            
            // 填充实际数据
            for (int i = 0; i < dataLength; i++)
            {
                float yValue = 0;
                if (channelIndex < dataArray[i].Length)
                {
                    yValue = dataArray[i][channelIndex];
                }
                
                positions[startPos + i] = new Vector3((startPos + i) * sampleSpacing, yValue, 0);
            }
        }
        else
        {
            // 数据足够，使用最新的maxSamples个点
            int startDataIndex = dataLength - maxSamples;
            
            for (int i = 0; i < maxSamples; i++)
            {
                float yValue = 0;
                if (channelIndex < dataArray[startDataIndex + i].Length)
                {
                    yValue = dataArray[startDataIndex + i][channelIndex];
                }
                
                positions[i] = new Vector3(i * sampleSpacing, yValue, 0);
            }
        }
        
        renderer.SetPositions(positions);
    }
    
    /// <summary>
    /// 清除波形
    /// </summary>
    public void ClearWaveform()
    {
        lock (channelDataBuffers)
        {
            channelDataBuffers.Clear();
            
            // 清空所有LineRenderer
            foreach (LineRenderer renderer in channelRenderers)
            {
                if (renderer != null)
                {
                    Vector3[] positions = new Vector3[maxSamples];
                    for (int i = 0; i < maxSamples; i++)
                    {
                        positions[i] = new Vector3(i * sampleSpacing, 0, 0);
                    }
                    renderer.SetPositions(positions);
                }
            }
        }
        
        UpdateStatusText("波形已清除");
    }
    
    /// <summary>
    /// 设置显示参数
    /// </summary>
    public void SetDisplayParameters(int newMaxSamples, float newAmplitudeScale)
    {
        maxSamples = Mathf.Max(50, newMaxSamples); // 最小50个样本
        amplitudeScale = Mathf.Max(0.001f, newAmplitudeScale); // 最小缩放
        
        // 重新设置样本间距
        if (waveformContainer != null)
        {
            sampleSpacing = waveformContainer.rect.width / maxSamples;
        }
        
        // 重新创建LineRenderer
        DestroyChannelRenderers();
        SetupWaveformDisplay();
    }
    
    /// <summary>
    /// 销毁通道渲染器
    /// </summary>
    private void DestroyChannelRenderers()
    {
        foreach (GameObject channelObject in channelObjects)
        {
            if (channelObject != null)
            {
                Destroy(channelObject);
            }
        }
        
        channelRenderers.Clear();
        channelObjects.Clear();
    }
    
    /// <summary>
    /// 更新状态文本
    /// </summary>
    private void UpdateStatusText(string message)
    {
        if (statusText != null)
        {
            statusText.text = message;
        }
    }
    
    /// <summary>
    /// 获取当前数据统计信息
    /// </summary>
    public string GetDataStatistics()
    {
        lock (channelDataBuffers)
        {
            int bufferSize = channelDataBuffers.Count;
            return $"缓冲区大小: {bufferSize}, 通道数: {channelRenderers.Count}, 样本数: {maxSamples}";
        }
    }
    
    void OnDestroy()
    {
        // 取消事件订阅
        if (dataReceiver != null)
        {
            dataReceiver.OnDataReceived -= OnDataReceived;
        }
        
        // 清理资源
        DestroyChannelRenderers();
    }
}