using UnityEngine;
using UnityEngine.UI;
using System.Collections.Generic;
using TMPro;
using System.Linq;

public class WaveformViewer : MonoBehaviour
{
    [Header("显示设置")]
    [SerializeField] private int maxChannels = 8;
    [SerializeField] public int maxSamples = 256; 
    [SerializeField] private float displayDuration = 2.0f;
    [SerializeField] private float verticalSpacing = 1.5f;
    [SerializeField] [Tooltip("通道间垂直间距比例，较小值会把通道压得更近（默认 0.6）")]
    private float channelSpacing = 0.6f;
    
    [Header("波形样式")]
    [SerializeField] private float lineWidth = 2f;
    [SerializeField] private Color[] channelColors;
    [SerializeField] private float amplitudeScale = 0.5f; // 添加amplitudeScale字段
    
    [Header("UI引用")]
    [SerializeField] private Canvas canvas;
    [SerializeField] private RectTransform waveformContainer;
    [SerializeField] private Text statusText;
    [SerializeField] private Material lineMaterial;
    
    // 数据接收器引用
    private UDPDataReceiver dataReceiver;
    
    // 使用UILineRenderer代替LineRenderer
    private List<UILineRenderer> channelRenderers = new List<UILineRenderer>();
    private List<RectTransform> channelTransforms = new List<RectTransform>();
    
    // 数据存储
    private Queue<float[]> channelDataBuffers = new Queue<float[]>();
    private float sampleSpacing;
    [SerializeField] private bool enableDebugLogs = true;
    private int updateLogCounter = 0;
    private int updateLogInterval = 60; // 每多少帧打印一次摘要
    private float channelPixelHeight = 0f;
    
    // 添加公共属性以便外部访问
    public int MaxSamples 
    { 
        get => maxSamples; 
        set
        {
            maxSamples = Mathf.Max(50, value);
            ReinitializeDisplay();
        }
    }
    
    public float AmplitudeScale 
    { 
        get => amplitudeScale; 
        set => amplitudeScale = Mathf.Max(0.001f, value); 
    }
    
    void Start()
    {
        InitializeComponents();
        SetupWaveformDisplay();
    }
    
    void Update()
    {
        UpdateWaveformDisplay();
    }
    
    private void InitializeComponents()
    {
        dataReceiver = FindObjectOfType<UDPDataReceiver>();
        if (dataReceiver != null)
        {
            dataReceiver.OnDataReceived += OnDataReceived;
        }
        
        // 初始化颜色
        if (channelColors == null || channelColors.Length == 0)
        {
            channelColors = new Color[]
            {
                Color.red, Color.green, Color.blue, Color.yellow,
                Color.cyan, Color.magenta, Color.white, Color.gray
            };
        }
        
        // 确保容器存在
        if (waveformContainer == null)
        {
            waveformContainer = GetComponent<RectTransform>();
            if (waveformContainer == null)
            {
                GameObject containerObj = new GameObject("WaveformContainer");
                containerObj.transform.SetParent(canvas.transform, false);
                waveformContainer = containerObj.AddComponent<RectTransform>();
                
                // 设置容器大小
                waveformContainer.anchorMin = new Vector2(0, 0);
                waveformContainer.anchorMax = new Vector2(1, 1);
                waveformContainer.offsetMin = new Vector2(10, 10);
                waveformContainer.offsetMax = new Vector2(-10, -10);
            }
        }

        // 强制更新布局，确保 RectTransform 的尺寸在 Start 时已计算完毕
        Canvas.ForceUpdateCanvases();
        UnityEngine.UI.LayoutRebuilder.ForceRebuildLayoutImmediate(waveformContainer);

        Debug.Log("波形显示组件初始化完成");
    }
    
    private void SetupWaveformDisplay()
    {
        // 清除现有通道
        ClearAllChannels();
        
        // 计算样本间距（基于容器宽度）
        float containerWidth = Mathf.Max(1f, waveformContainer.rect.width);
        float containerHeight = Mathf.Max(1f, waveformContainer.rect.height);
        sampleSpacing = containerWidth / maxSamples;

        // 计算每个通道在像素空间的高度，用于将 EEG 值缩放到像素坐标
        channelPixelHeight = containerHeight / Mathf.Max(1, maxChannels);

        if (enableDebugLogs)
        {
            Debug.Log($"[WaveformViewer] SetupWaveformDisplay: containerWidth={containerWidth}, containerHeight={containerHeight}, sampleSpacing={sampleSpacing}, channelPixelHeight={channelPixelHeight}");
        }

        if (enableDebugLogs)
        {
            Debug.Log($"[WaveformViewer] SetupWaveformDisplay: containerWidth={containerWidth}, sampleSpacing={sampleSpacing}, maxSamples={maxSamples}, maxChannels={maxChannels}");
        }
        
        // 创建每个通道的UI Line Renderer
        for (int i = 0; i < maxChannels; i++)
        {
            CreateUILineRenderer(i);
        }
        
        // 初始化数据缓冲区
        int bufferSize = Mathf.CeilToInt(displayDuration * 30); // 假设30Hz
        for (int i = 0; i < bufferSize; i++)
        {
            channelDataBuffers.Enqueue(new float[maxChannels]);
        }
        
        UpdateStatusText("等待EEG数据...");
    }
    
    private void CreateUILineRenderer(int channelIndex)
    {
        // 创建通道容器
        GameObject channelObject = new GameObject($"Channel_{channelIndex}");
        RectTransform channelRect = channelObject.AddComponent<RectTransform>();
        channelRect.SetParent(waveformContainer, false);
        
        // 设置通道位置和大小：让每个通道占满容器（使用锚点拉伸），通过 anchoredPosition 做垂直偏移
        channelRect.anchorMin = new Vector2(0, 0);
        channelRect.anchorMax = new Vector2(1, 1);
        channelRect.offsetMin = Vector2.zero;
        channelRect.offsetMax = Vector2.zero;
        channelRect.pivot = new Vector2(0, 0.5f);
        
        // 添加UILineRenderer组件
        UILineRenderer lineRenderer = channelObject.AddComponent<UILineRenderer>();
        lineRenderer.material = lineMaterial ?? new Material(Shader.Find("UI/Default"));
        // Ensure a CanvasRenderer exists so the Graphic can render
        if (channelObject.GetComponent<CanvasRenderer>() == null)
        {
            channelObject.AddComponent<CanvasRenderer>();
        }
        lineRenderer.raycastTarget = false;
        
        // 设置样式
        Color channelColor = channelIndex < channelColors.Length ? 
            channelColors[channelIndex] : Color.white;
        lineRenderer.color = channelColor;
        lineRenderer.lineWidth = lineWidth;
        
        // 初始化点数（y 值为 0 居中）
        lineRenderer.points = new Vector2[maxSamples];
        for (int i = 0; i < maxSamples; i++)
        {
            lineRenderer.points[i] = new Vector2(i * sampleSpacing, 0f);
        }
        
        // 更新几何
        lineRenderer.SetVerticesDirty();
        
        // 存储引用
        channelRenderers.Add(lineRenderer);
        channelTransforms.Add(channelRect);
        
        // 设置垂直偏移（基于通道像素高度和 channelSpacing 比例）
        float verticalOffset = (channelIndex - (maxChannels - 1) / 2f) * channelPixelHeight * channelSpacing;
        channelRect.anchoredPosition = new Vector2(0, verticalOffset);
    }
    
    private void OnDataReceived(float[] data)
    {
        if (data == null || data.Length < maxChannels) 
        {
            Debug.LogWarning($"数据长度不足: {data?.Length}, 需要至少{maxChannels}");
            return;
        }
        
        int sampleCount = data.Length / maxChannels;
        
        lock (channelDataBuffers)
        {
            for (int sampleIdx = 0; sampleIdx < sampleCount; sampleIdx++)
            {
                float[] channelData = new float[maxChannels];
                for (int ch = 0; ch < maxChannels; ch++)
                {
                    int dataIndex = sampleIdx * maxChannels + ch;
                    if (dataIndex < data.Length)
                    {
                        channelData[ch] = data[dataIndex] * amplitudeScale;
                    }
                }
                
                channelDataBuffers.Enqueue(channelData);
                
                // 保持缓冲区大小
                while (channelDataBuffers.Count > displayDuration * 30)
                {
                    channelDataBuffers.Dequeue();
                }
            }
        }
        
        UpdateStatusText($"接收 {sampleCount} 样本 × {maxChannels} 通道");

        if (enableDebugLogs)
        {
            float min = float.MaxValue, max = float.MinValue, sum = 0f;
            for (int i = 0; i < data.Length; i++)
            {
                float v = data[i];
                if (v < min) min = v;
                if (v > max) max = v;
                sum += v;
            }
            float mean = data.Length > 0 ? sum / data.Length : 0f;
            Debug.Log($"[WaveformViewer] OnDataReceived: dataLen={data?.Length}, sampleCount={sampleCount}, bufferCount={channelDataBuffers.Count}, min={min:F6}, max={max:F6}, mean={mean:F6}");
            // 打印前几个通道的第一个样本（如果存在），避免大量输出
            if (data != null && data.Length > 0)
            {
                int previewCount = Mathf.Min(8, data.Length);
                string preview = string.Join(",", data.Take(previewCount).Select(d => d.ToString("F3")));
                Debug.Log($"[WaveformViewer] OnDataReceived preview (first {previewCount} values): {preview}");
            }
        }
    }
    
    private void UpdateWaveformDisplay()
    {
        if (channelRenderers.Count == 0 || channelDataBuffers.Count == 0) 
            return;
        
        lock (channelDataBuffers)
        {
            // 获取最新数据
            float[][] dataArray = channelDataBuffers.ToArray();
            
            // 更新每个通道
            for (int channel = 0; channel < Mathf.Min(channelRenderers.Count, maxChannels); channel++)
            {
                UpdateChannelUILine(channelRenderers[channel], dataArray, channel);
            }

            // 周期性打印摘要，避免控制台刷屏
            if (enableDebugLogs)
            {
                updateLogCounter++;
                if (updateLogCounter % updateLogInterval == 0)
                {
                    Debug.Log($"[WaveformViewer] UpdateWaveformDisplay summary: bufferCount={channelDataBuffers.Count}, renderers={channelRenderers.Count}, sampleSpacing={sampleSpacing:F3}, channelPixelHeight={channelPixelHeight:F3}");
                    // 打印第一个通道的前几个点作为快照
                    if (channelRenderers.Count > 0 && channelRenderers[0].points != null)
                    {
                        var pts = channelRenderers[0].points;
                        int n = Mathf.Min(8, pts.Length);
                        string ptsPreview = string.Join(",", pts.Take(n).Select(p => $"({p.x:F1},{p.y:F3})"));
                        Debug.Log($"[WaveformViewer] Renderer[0] points preview: {ptsPreview}");
                    }
                }
            }
        }
    }
    
    private void UpdateChannelUILine(UILineRenderer renderer, float[][] dataArray, int channelIndex)
    {
        if (renderer == null || dataArray.Length == 0) 
            return;
        
        // 确保 sampleSpacing 有效（防止在布局尚未计算时为 0）
        if (sampleSpacing <= 0f && waveformContainer != null)
        {
            sampleSpacing = Mathf.Max(1f, waveformContainer.rect.width) / maxSamples;
        }

        Vector2[] points = new Vector2[maxSamples];
        int dataLength = dataArray.Length;

        // 计算该通道的绝对值最大值，用于自适应缩放（避免过大或过小）
        float maxAbs = 0f;
        for (int i = 0; i < dataLength; i++)
        {
            if (channelIndex < dataArray[i].Length)
            {
                float v = Mathf.Abs(dataArray[i][channelIndex]);
                if (v > maxAbs) maxAbs = v;
            }
        }
        float adaptiveScale = 1f;
        if (maxAbs > 1e-6f)
        {
            adaptiveScale = (channelPixelHeight * 0.4f) / maxAbs; // 将 maxAbs 映射到 channelPixelHeight*0.4
        }
        // 综合用户缩放与自适应缩放
        float finalScale = amplitudeScale * adaptiveScale;

        if (enableDebugLogs && channelIndex == 0)
        {
            Debug.Log($"[WaveformViewer] Channel {channelIndex} adaptiveScale={adaptiveScale:F6} finalScale={finalScale:F6} maxAbs={maxAbs:F6}");
        }
        
        if (dataLength < maxSamples)
        {
            int startPos = maxSamples - dataLength;
            
            // 填充空白区域
            for (int i = 0; i < startPos; i++)
            {
                points[i] = new Vector2(i * sampleSpacing, 0);
            }
            
            // 填充实际数据
            for (int i = 0; i < dataLength; i++)
            {
                float yValue = 0;
                if (channelIndex < dataArray[i].Length)
                {
                    yValue = dataArray[i][channelIndex];
                }
                // 把原始 EEG 值映射到像素高度（使用自适应缩放）
                float yPixel = yValue * finalScale;
                points[startPos + i] = new Vector2((startPos + i) * sampleSpacing, yPixel);
            }
        }
        else
        {
            // 使用最新数据
            int startDataIndex = dataLength - maxSamples;
            
            for (int i = 0; i < maxSamples; i++)
            {
                float yValue = 0;
                if (channelIndex < dataArray[startDataIndex + i].Length)
                {
                    yValue = dataArray[startDataIndex + i][channelIndex];
                }

                float yPixel = yValue * finalScale;
                points[i] = new Vector2(i * sampleSpacing, yPixel);
            }
        }
        
        renderer.points = points;
        renderer.SetVerticesDirty(); // 强制更新渲染

        if (enableDebugLogs && channelIndex == 0)
        {
            int previewN = Mathf.Min(6, points.Length);
            string preview = string.Join(",", points.Take(previewN).Select(p => $"({p.x:F1},{p.y:F3})"));
            // 同时打印原始数据值 -> 映射像素值 预览
            int samplePreviewN = Mathf.Min(6, dataLength);
            var mapParts = new List<string>();
            for (int i = 0; i < samplePreviewN; i++)
            {
                float raw = 0f;
                if (i < dataLength && channelIndex < dataArray[i].Length)
                    raw = dataArray[i][channelIndex];
                float mapped = raw * amplitudeScale * channelPixelHeight * 0.4f;
                mapParts.Add($"{raw:F3}->{mapped:F3}");
            }
            string mapPreview = string.Join(",", mapParts);
            Debug.Log($"[WaveformViewer] UpdateChannelUILine channel=0 dataLength={dataLength} pointsPreview={preview} mapPreview={mapPreview}");
        }
    }
    
    private void ClearAllChannels()
    {
        foreach (var renderer in channelRenderers)
        {
            if (renderer != null)
                Destroy(renderer.gameObject);
        }
        
        channelRenderers.Clear();
        channelTransforms.Clear();
    }
    
    public void ClearWaveform()
    {
        lock (channelDataBuffers)
        {
            channelDataBuffers.Clear();
            
            // 重置所有线条
            foreach (var renderer in channelRenderers)
            {
                if (renderer != null)
                {
                    for (int i = 0; i < renderer.points.Length; i++)
                    {
                        renderer.points[i] = new Vector2(i * sampleSpacing, 0);
                    }
                    renderer.SetVerticesDirty();
                }
            }
        }
        
        UpdateStatusText("波形已清除");
    }
    
    // 添加这个方法，与你的VisualizationManager兼容
    public void SetDisplayParameters(int newMaxSamples, float newAmplitudeScale)
    {
        MaxSamples = newMaxSamples;
        AmplitudeScale = newAmplitudeScale;
        
        // 重新计算样本间距
        if (waveformContainer != null)
        {
            sampleSpacing = waveformContainer.rect.width / maxSamples;
        }
        
        // 重新初始化显示
        ReinitializeDisplay();
    }
    
    // 重新初始化显示
    private void ReinitializeDisplay()
    {
        ClearAllChannels();
        SetupWaveformDisplay();
    }
    
    private void UpdateStatusText(string message)
    {
        if (statusText != null)
        {
            statusText.text = message;
        }
    }
    
    // 添加获取数据统计的方法
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
        if (dataReceiver != null)
        {
            dataReceiver.OnDataReceived -= OnDataReceived;
        }
        ClearAllChannels();
    }
}

// 自定义UI Line Renderer组件保持不变
public class UILineRenderer : MaskableGraphic
{
    [SerializeField] private Vector2[] _points;
    [SerializeField] private float _lineWidth = 1f;
    
    public Vector2[] points
    {
        get => _points;
        set
        {
            _points = value;
            SetVerticesDirty();
        }
    }
    
    public float lineWidth
    {
        get => _lineWidth;
        set
        {
            _lineWidth = value;
            SetVerticesDirty();
        }
    }
    
    protected override void OnPopulateMesh(VertexHelper vh)
    {
        vh.Clear();
        
        if (_points == null || _points.Length < 2)
            return;
        
        for (int i = 0; i < _points.Length - 1; i++)
        {
            AddLineSegment(vh, _points[i], _points[i + 1], i);
        }
    }
    
    private void AddLineSegment(VertexHelper vh, Vector2 start, Vector2 end, int index)
    {
        Vector2 direction = (end - start).normalized;
        Vector2 perpendicular = new Vector2(-direction.y, direction.x) * _lineWidth * 0.5f;

        UIVertex v0 = UIVertex.simpleVert;
        UIVertex v1 = UIVertex.simpleVert;
        UIVertex v2 = UIVertex.simpleVert;
        UIVertex v3 = UIVertex.simpleVert;

        v0.position = new Vector3(start.x - perpendicular.x, start.y - perpendicular.y, 0f);
        v1.position = new Vector3(start.x + perpendicular.x, start.y + perpendicular.y, 0f);
        v2.position = new Vector3(end.x + perpendicular.x, end.y + perpendicular.y, 0f);
        v3.position = new Vector3(end.x - perpendicular.x, end.y - perpendicular.y, 0f);

        v0.color = v1.color = v2.color = v3.color = color;
        v0.uv0 = v1.uv0 = v2.uv0 = v3.uv0 = Vector2.zero;

        int baseIndex = vh.currentVertCount;
        vh.AddVert(v0);
        vh.AddVert(v1);
        vh.AddVert(v2);
        vh.AddVert(v3);

        vh.AddTriangle(baseIndex, baseIndex + 1, baseIndex + 2);
        vh.AddTriangle(baseIndex + 2, baseIndex + 3, baseIndex);
    }
}