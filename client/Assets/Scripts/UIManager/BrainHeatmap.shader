Shader "Custom/BrainHeatmap"
{
    Properties
    {
        _MainTex ("Base (RGB)", 2D) = "white" {}
        _IntensityScale ("Intensity Scale", Float) = 1.0
        _Spread ("Spread", Range(0.01, 100)) = 0.5 // 控制热力扩散范围
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" }
        LOD 200

        CGPROGRAM
        #pragma surface surf Standard fullforwardshadows
        #pragma target 3.0

        sampler2D _MainTex;
        float4 _ElectrodePoints[8]; // 对应C#中的坐标
        float _Intensities[8];      // 对应C#中的强度
        float _IntensityScale;
        // float _GlobalHeat; // 作为回退，方便调试
        float _Spread;

        struct Input
        {
            float2 uv_MainTex;
            float3 worldPos; // 系统会自动填充世界坐标
        };

        // 删除之前的 vert 函数，不需要它了

        void surf (Input IN, inout SurfaceOutputStandard o)
        {
            float heat = 0;
            for (int i = 0; i < 8; i++) {
                // 【核心修改】：直接使用 IN.worldPos 计算
                // 这样 C# 传过来的 electrodePositions[j].position (世界坐标) 
                // 就能跟这里的像素世界坐标完美匹配！
                float d = distance(IN.worldPos, _ElectrodePoints[i].xyz);
                
                // 使用更稳健的计算方式，防止由于距离过近导致的无限大
                float influence = exp(-(d * d) / (_Spread * _Spread + 0.0001));
                heat += _Intensities[i] * influence;
            }

            heat *= _IntensityScale;

            // 颜色插值保持不变...
            float3 cold = float3(0, 0, 0.5); // 稍微亮一点的蓝
            float3 mid = float3(0, 1, 0);
            float3 hot = float3(1, 0, 0);

            float3 color = lerp(cold, hot, saturate(heat));
            
            // 如果热力值很低，让它更偏蓝一点
            if(heat < 0.5) color = lerp(cold, mid, heat * 2.0);
            else color = lerp(mid, hot, (heat - 0.5) * 2.0);

            o.Albedo = color;
            o.Emission = color * heat * 0.3;
        }
        ENDCG
    }
    FallBack "Diffuse"
}