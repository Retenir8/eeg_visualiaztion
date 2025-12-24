using UnityEngine;
using System.Collections.Generic;

/// <summary>
/// 3D大脑映射器 - 负责将8通道幅值传递给Shader进行空间插值渲染
/// 支持多个Mesh部位组成的复杂模型
/// </summary>
public class BrainMapper : MonoBehaviour
{
    [Header("渲染引用")]
    [SerializeField] private Renderer[] brainRenderers; // 修改为数组：支持拖入多个大脑部位
    [SerializeField] private Transform[] electrodePositions; // 场景中的Electrode_0-7

    [Header("映射设置")]
    [Range(0.1f, 10f)]
    [SerializeField] private float intensityScale = 1.0f; // 幅值缩放
    [SerializeField] private float animationSpeed = 5.0f; // 颜色过渡平滑度
    [SerializeField] private float minInputMicrovolts = -50f; // 归一化最小值
    [SerializeField] private float maxInputMicrovolts = 50f;  // 归一化最大值

    // 内部数据存储
    private float[] currentIntensities = new float[8]; 
    private float[] targetIntensities = new float[8];  
    private Vector4[] shaderPoints = new Vector4[8];   
    private List<Material> brainMaterials = new List<Material>(); // 存储所有子部位的材质
    private bool hasWarnedNoMaterials = false;
    private bool hasSetGlobalOnce = false;
    private string globalHeatName = "_GlobalHeat";

    void Start()
    {
        // 方案一：初始化时获取所有部位的实例材质
        if (brainRenderers != null && brainRenderers.Length > 0)
        {
            foreach (Renderer rend in brainRenderers)
            {
                if (rend != null)
                {
                    // 使用 .material 会自动创建实例，修改不会影响项目资源文件
                    brainMaterials.Add(rend.material);
                }
            }
        }

        // 输出每个材质的 shader 信息以及是否支持需要的属性
        foreach (var mat in brainMaterials)
        {
            if (mat == null) continue;
            string shaderName = mat.shader != null ? mat.shader.name : "<null>";
            bool hasElectro = mat.HasProperty("_ElectrodePoints");
            bool hasInts = mat.HasProperty("_Intensities");
            bool hasScale = mat.HasProperty("_IntensityScale");
            Debug.Log($"BrainMapper: material='{mat.name}', shader='{shaderName}', has _ElectrodePoints={hasElectro}, has _Intensities={hasInts}, has _IntensityScale={hasScale}");
        }

        // 输出材质数量与电极数组长度（带异常保护）
        int electrodeLen = 0;
        bool electrodeValid = true;
        try
        {
            electrodeLen = electrodePositions != null ? electrodePositions.Length : 0;
        }
        catch (System.Exception ex)
        {
            Debug.LogError($"BrainMapper: 读取 electrodePositions.Length 时发生异常: {ex.Message}");
            electrodeValid = false;
            electrodeLen = 0;
        }

        Debug.Log($"BrainMapper: 找到材质数量={brainMaterials.Count}, 电极引用长度={electrodeLen}");

        if (!electrodeValid || electrodePositions == null || electrodeLen < 8)
        {
            Debug.LogWarning("BrainMapper: electrodePositions 配置异常或长度小于8，某些电极坐标将为 (0,0,0)");
        }

        // 尝试修复材质上丢失的 shader（如果发现不是目标 shader）
        Shader target = Shader.Find("Custom/BrainHeatmap");
        foreach (var mat in brainMaterials)
        {
            if (mat == null) continue;
            if (mat.shader == null || mat.shader.name == "Hidden/InternalErrorShader")
            {
                if (target != null)
                {
                    mat.shader = target;
                    Debug.Log($"BrainMapper: 已将材质 '{mat.name}' 的 shader 设为 'Custom/BrainHeatmap'");
                }
                else
                {
                    Debug.LogWarning("BrainMapper: 未能找到 'Custom/BrainHeatmap' shader，请检查 Shader 文件是否存在并已编译。");
                }
            }
        }

        // 列出电极数组逐项状态，便于排查负长度/空引用问题
        if (electrodePositions != null && electrodeLen > 0)
        {
            int dumpCount = Mathf.Min(electrodeLen, 16);
            for (int i = 0; i < dumpCount; i++)
            {
                Transform t = electrodePositions[i];
                Debug.Log($"BrainMapper: electrodePositions[{i}] = {(t!=null? t.name : "<null>")}\n");
            }
        }

        UpdateElectrodeCoordinates();
    }

    void Update()
    {
        // 1. 平滑强度数据
        for (int i = 0; i < 8; i++)
            currentIntensities[i] = Mathf.Lerp(currentIntensities[i], targetIntensities[i], Time.deltaTime * animationSpeed);

        // 2. 为每个 Renderer 独立计算
        for (int i = 0; i < brainRenderers.Length; i++)
        {
            Renderer rend = brainRenderers[i];
            if (rend == null || i >= brainMaterials.Count) continue;

            Material mat = brainMaterials[i];
            if (mat == null) continue;

            Vector4[] localPoints = new Vector4[8];
            for (int j = 0; j < 8; j++)
            {
                // 核心修复：直接将电极的世界坐标传给材质，
                // 然后我们在 Shader 里把顶点的坐标也转成世界空间
                // 这样无论模型怎么缩放位移，坐标绝对一致！
                localPoints[j] = electrodePositions[j].position; 
            }

            mat.SetVectorArray("_ElectrodePoints", localPoints);
            mat.SetFloatArray("_Intensities", currentIntensities);
            mat.SetFloat("_IntensityScale", intensityScale);
        }
    }

    /// <summary>
    /// 被 VisualizationManager 调用，接收来自 UDP 的实时数据
    /// </summary>
    public void UpdateData(float[] data)
    {
        if (data == null || data.Length < 8) return;

        // 获取最新的样本
        int lastSampleIndex = data.Length - 8;

        for (int i = 0; i < 8; i++)
        {
            float rawValue = data[lastSampleIndex + i];
            targetIntensities[i] = Mathf.InverseLerp(minInputMicrovolts, maxInputMicrovolts, rawValue);
            if (i == 0)
            {
                Debug.Log($"BrainMapper.UpdateData: rawValues[{i}]={rawValue:F3}, target={targetIntensities[i]:F3}");
            }
        }
    }

    private void UpdateElectrodeCoordinates()
{
    if (brainRenderers == null || brainRenderers.Length == 0) return;

    for (int i = 0; i < 8; i++)
    {
        if (i < electrodePositions.Length && electrodePositions[i] != null)
        {
            // 【关键修改】：将电极的世界坐标转换为大脑模型的本地空间坐标
            // 这样 Shader 里的 localPos 才能和这个坐标对上
            Vector3 localP = brainRenderers[0].transform.InverseTransformPoint(electrodePositions[i].position);
            shaderPoints[i] = new Vector4(localP.x, localP.y, localP.z, 1f);
        }
    }
}
    public void ClearDisplay()
    {
        for (int i = 0; i < 8; i++)
        {
            targetIntensities[i] = 0;
            currentIntensities[i] = 0;
        }
    }
}