/* Unity客户端3D大脑映射组件
将EEG信号映射到3D大脑模型上 */

using UnityEngine;
using UnityEngine.UI;
using TMPro;
using System.Collections.Generic;

/// <summary>
/// 大脑映射器
/// 将EEG数据映射到3D大脑模型上显示
/// </summary>
public class BrainMapper : MonoBehaviour
{
    [Header("3D模型设置")]
    [SerializeField] private GameObject brainModel; // 3D大脑模型
    [SerializeField] private Transform[] electrodePositions; // 电极位置
    
    [Header("显示设置")]
    [SerializeField] private int maxChannels = 8;
    [SerializeField] private float animationSpeed = 2f;
    [SerializeField] private float intensityScale = 1f;
    
    [Header("颜色映射")]
    [SerializeField] private Gradient colorGradient;
    [SerializeField] private float minColorValue = -100f;
    [SerializeField] private float maxColorValue = 100f;
    
    [Header("UI引用")]
    [SerializeField] private TextMeshProUGUI channelInfoText;
    [SerializeField] private Dropdown channelSelectionDropdown;
    [SerializeField] private Slider intensitySlider;
    [SerializeField] private Toggle autoUpdateToggle;
    
    // 通道数据
    private float[] channelData = new float[8];
    private float[] channelIntensity = new float[8];
    private bool[] channelActive = new bool[8];
    
    // 渲染组件
    private Renderer[] electrodeRenderers;
    private Material[] electrodeMaterials;
    
    // 数据接收器
    private UDPDataReceiver dataReceiver;
    
    // 动画控制
    private bool isAnimating = false;
    private float lastUpdateTime = 0f;
    
    void Start()
    {
        InitializeBrainMapping();
        SetupUI();
    }
    
    void Update()
    {
        UpdateBrainMapping();
    }
    
    /// <summary>
    /// 初始化大脑映射
    /// </summary>
    private void InitializeBrainMapping()
    {
        // 查找数据接收器
        dataReceiver = FindObjectOfType<UDPDataReceiver>();
        if (dataReceiver != null)
        {
            dataReceiver.OnDataReceived += OnDataReceived;
        }
        
        // 设置电极位置
        SetupElectrodePositions();
        
        // 创建电极材质
        SetupElectrodeMaterials();
        
        // 初始化通道状态
        for (int i = 0; i < maxChannels; i++)
        {
            channelActive[i] = true;
            channelIntensity[i] = 0f;
        }
        
        Debug.Log("大脑映射器初始化完成");
    }
    
    /// <summary>
    /// 设置电极位置
    /// </summary>
    private void SetupElectrodePositions()
    {
        if (electrodePositions == null || electrodePositions.Length == 0)
        {
            // 如果没有指定位置，创建默认位置
            electrodePositions = CreateDefaultElectrodePositions();
        }
        
        // 确保电极数量正确
        if (electrodePositions.Length < maxChannels)
        {
            Debug.LogWarning($"电极位置数量 ({electrodePositions.Length}) 少于所需通道数 ({maxChannels})");
        }
    }
    
    /// <summary>
    /// 创建默认电极位置
    /// </summary>
    private Transform[] CreateDefaultElectrodePositions()
    {
        List<Transform> positions = new List<Transform>();
        
        // 在大脑模型周围创建8个默认位置
        for (int i = 0; i < maxChannels; i++)
        {
            GameObject electrode = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            electrode.name = $"DefaultElectrode_{i}";
            electrode.transform.localScale = Vector3.one * 0.05f; // 小球体
            
            // 设置位置（简单的圆形分布）
            float angle = (i / (float)maxChannels) * Mathf.PI * 2;
            float radius = 0.3f;
            
            electrode.transform.position = new Vector3(
                Mathf.Cos(angle) * radius,
                0.2f,
                Mathf.Sin(angle) * radius
            );
            
            // 添加发光效果
            Material electrodeMaterial = new Material(Shader.Find("Standard"));
            electrodeMaterial.SetColor("_EmissionColor", Color.black);
            electrodeMaterial.EnableKeyword("_EMISSION");
            electrode.GetComponent<Renderer>().material = electrodeMaterial;
            
            positions.Add(electrode.transform);
        }
        
        return positions.ToArray();
    }
    
    /// <summary>
    /// 设置电极材质
    /// </summary>
    private void SetupElectrodeMaterials()
    {
        if (electrodePositions == null) return;
        
        electrodeRenderers = new Renderer[maxChannels];
        electrodeMaterials = new Material[maxChannels];
        
        for (int i = 0; i < maxChannels; i++)
        {
            if (i < electrodePositions.Length)
            {
                Renderer renderer = electrodePositions[i].GetComponent<Renderer>();
                if (renderer != null)
                {
                    electrodeRenderers[i] = renderer;
                    electrodeMaterials[i] = renderer.material;
                    
                    // 设置初始颜色
                    SetElectrodeColor(i, Color.black);
                }
            }
        }
    }
    
    /// <summary>
    /// 设置UI组件
    /// </summary>
    private void SetupUI()
    {
        // 设置通道选择下拉菜单
        if (channelSelectionDropdown != null)
        {
            channelSelectionDropdown.ClearOptions();
            List<string> channelOptions = new List<string>();
            for (int i = 0; i < maxChannels; i++)
            {
                channelOptions.Add($"通道 {i + 1}");
            }
            channelSelectionDropdown.AddOptions(channelOptions);
            channelSelectionDropdown.onValueChanged.AddListener(OnChannelSelectionChanged);
        }
        
        // 设置强度滑块
        if (intensitySlider != null)
        {
            intensitySlider.minValue = 0.1f;
            intensitySlider.maxValue = 5f;
            intensitySlider.value = intensityScale;
            intensitySlider.onValueChanged.AddListener(OnIntensityChanged);
        }
        
        // 设置自动更新
        if (autoUpdateToggle != null)
        {
            autoUpdateToggle.isOn = true;
        }
    }
    
    /// <summary>
    /// 数据接收回调
    /// </summary>
    private void OnDataReceived(float[] data)
    {
        if (isPaused || data == null || data.Length == 0) return;
        
        // 数据格式：[s0_ch0, s0_ch1, ..., s0_ch7, s1_ch0, s1_ch1, ..., s_n_ch7]
        // 计算样本数
        int sampleCount = data.Length / maxChannels;
        
        // 使用最后一个样本的数据（最新数据）
        int lastSampleStartIndex = (sampleCount - 1) * maxChannels;
        
        // 更新通道数据
        for (int i = 0; i < maxChannels && i < data.Length; i++)
        {
            int dataIndex = lastSampleStartIndex + i;
            if (dataIndex < data.Length)
            {
                channelData[i] = data[dataIndex];
                
                // 计算强度值
                float normalizedValue = Mathf.InverseLerp(minColorValue, maxColorValue, channelData[i]);
                channelIntensity[i] = normalizedValue * intensityScale;
            }
        }
        
        isAnimating = true;
    }
    
    /// <summary>
    /// 更新大脑映射
    /// </summary>
    private void UpdateBrainMapping()
    {
        if (!isAnimating) return;
        
        float deltaTime = Time.deltaTime;
        
        for (int i = 0; i < maxChannels; i++)
        {
            if (i < electrodeMaterials.Length && electrodeMaterials[i] != null)
            {
                // 计算目标颜色
                float targetIntensity = channelActive[i] ? channelIntensity[i] : 0f;
                
                // 平滑过渡
                float currentIntensity = GetCurrentIntensity(i);
                float newIntensity = Mathf.Lerp(currentIntensity, targetIntensity, deltaTime * animationSpeed);
                
                // 更新材质
                SetElectrodeIntensity(i, newIntensity);
            }
        }
        
        // 检查动画是否完成
        if (IsAnimationComplete())
        {
            isAnimating = false;
        }
        
        // 更新UI信息
        UpdateChannelInfo();
    }
    
    /// <summary>
    /// 设置电极强度
    /// </summary>
    private void SetElectrodeIntensity(int channel, float intensity)
    {
        if (channel >= electrodeMaterials.Length || electrodeMaterials[channel] == null) return;
        
        // 获取颜色
        Color targetColor = colorGradient != null 
            ? colorGradient.Evaluate(intensity)
            : Color.Lerp(Color.blue, Color.red, intensity);
        
        // 设置材质颜色和发光
        SetElectrodeColor(channel, targetColor);
        
        // 设置发光强度
        if (electrodeMaterials[channel].HasProperty("_EmissionColor"))
        {
            Color emissionColor = targetColor * intensity * 0.5f;
            electrodeMaterials[channel].SetColor("_EmissionColor", emissionColor);
            electrodeMaterials[channel].EnableKeyword("_EMISSION");
        }
    }
    
    /// <summary>
    /// 设置电极颜色
    /// </summary>
    private void SetElectrodeColor(int channel, Color color)
    {
        if (channel >= electrodeMaterials.Length || electrodeMaterials[channel] == null) return;
        
        electrodeMaterials[channel].SetColor("_Color", color);
        
        // 确保材质支持发光
        if (color.r > 0.1f || color.g > 0.1f || color.b > 0.1f)
        {
            electrodeMaterials[channel].EnableKeyword("_EMISSION");
        }
        else
        {
            electrodeMaterials[channel].DisableKeyword("_EMISSION");
        }
    }
    
    /// <summary>
    /// 获取当前强度
    /// </summary>
    private float GetCurrentIntensity(int channel)
    {
        if (channel >= electrodeMaterials.Length || electrodeMaterials[channel] == null) return 0f;
        
        Color color = electrodeMaterials[channel].GetColor("_Color");
        return (color.r + color.g + color.b) / 3f;
    }
    
    /// <summary>
    /// 检查动画是否完成
    /// </summary>
    private bool IsAnimationComplete()
    {
        for (int i = 0; i < maxChannels; i++)
        {
            if (i < electrodeMaterials.Length && electrodeMaterials[i] != null)
            {
                float currentIntensity = GetCurrentIntensity(i);
                float targetIntensity = channelActive[i] ? channelIntensity[i] : 0f;
                
                if (Mathf.Abs(currentIntensity - targetIntensity) > 0.01f)
                {
                    return false;
                }
            }
        }
        return true;
    }
    
    /// <summary>
    /// 更新通道信息显示
    /// </summary>
    private void UpdateChannelInfo()
    {
        if (channelInfoText == null) return;
        
        string info = "大脑映射 - 通道状态:\n";
        for (int i = 0; i < maxChannels; i++)
        {
            string status = channelActive[i] ? "激活" : "关闭";
            float intensity = GetCurrentIntensity(i);
            info += $"Ch{i + 1}: {status} ({intensity:F2})\n";
        }
        
        channelInfoText.text = info;
    }
    
    /// <summary>
    /// 通道选择变化处理
    /// </summary>
    public void OnChannelSelectionChanged(int channel)
    {
        // 突出显示选择的通道
        HighlightSelectedChannel(channel);
    }
    
    /// <summary>
    /// 强度变化处理
    /// </summary>
    public void OnIntensityChanged(float newIntensity)
    {
        intensityScale = newIntensity;
    }
    
    /// <summary>
    /// 突出显示选择的通道
    /// </summary>
    private void HighlightSelectedChannel(int channel)
    {
        for (int i = 0; i < maxChannels; i++)
        {
            if (i < electrodeMaterials.Length && electrodeMaterials[i] != null)
            {
                // 为选择的通道设置不同的颜色
                if (i == channel)
                {
                    SetElectrodeIntensity(i, channelIntensity[i] * 2f); // 增强亮度
                }
                else
                {
                    SetElectrodeIntensity(i, channelIntensity[i] * 0.5f); // 降低亮度
                }
            }
        }
    }
    
    /// <summary>
    /// 切换通道状态
    /// </summary>
    public void ToggleChannel(int channel)
    {
        if (channel >= 0 && channel < maxChannels)
        {
            channelActive[channel] = !channelActive[channel];
        }
    }
    
    /// <summary>
    /// 清除显示
    /// </summary>
    public void ClearDisplay()
    {
        // 清除所有通道数据
        for (int i = 0; i < maxChannels; i++)
        {
            channelData[i] = 0f;
            channelIntensity[i] = 0f;
            SetElectrodeIntensity(i, 0f);
        }
        
        isAnimating = false;
    }
    
    /// <summary>
    /// 设置暂停状态
    /// </summary>
    public void SetPaused(bool paused)
    {
        isPaused = paused;
    }
    
    /// <summary>
    /// 重新定位电极
    /// </summary>
    public void RelocateElectrodes()
    {
        DestroyElectrodeObjects();
        electrodePositions = CreateDefaultElectrodePositions();
        SetupElectrodeMaterials();
    }
    
    /// <summary>
    /// 销毁电极对象
    /// </summary>
    private void DestroyElectrodeObjects()
    {
        if (electrodePositions != null)
        {
            foreach (Transform electrode in electrodePositions)
            {
                if (electrode != null)
                {
                    Destroy(electrode.gameObject);
                }
            }
        }
    }
    
    // 暂停控制
    private bool isPaused = false;
    
    void OnDestroy()
    {
        // 取消事件订阅
        if (dataReceiver != null)
        {
            dataReceiver.OnDataReceived -= OnDataReceived;
        }
        
        // 清理材质
        if (electrodeMaterials != null)
        {
            foreach (Material material in electrodeMaterials)
            {
                if (material != null)
                {
                    Destroy(material);
                }
            }
        }
    }
}