/*
Unity客户端数据接收模块
负责接收Python服务端发送的EEG数据
*/

using UnityEngine;
using System;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Collections.Generic;
using System.Threading;
using UnityEngine.UI;
using Newtonsoft.Json.Linq;
using PimDeWitte.UnityMainThreadDispatcher;

/// <summary>
/// UDP数据接收器 - 从Python服务端接收EEG数据
/// </summary>
public class UDPDataReceiver : MonoBehaviour
{
    [Header("UDP设置")]
    [SerializeField] private string serverIP = "127.0.0.1";
    [SerializeField] private int serverPort = 9999;
    [SerializeField] private int clientPort = 8888;

    [Header("可选 - 屏幕状态显示")]
    [SerializeField] private Text statusText;

    [Header("数据设置")]
    [SerializeField] private int maxChannelCount = 8;
    [SerializeField] private int maxDataBufferSize = 1000;
    
    // UDP相关
    private UdpClient udpClient;
    private Thread receiveThread;
    private bool isReceiving = false;
    
    // 数据存储
    private List<float[]> dataBuffer = new List<float[]>();
    private List<float> timestamps = new List<float>();
    private System.Object dataLock = new System.Object();
    
    // 事件
    public System.Action<float[]> OnDataReceived;
    public System.Action<string, string> OnStatusReceived;
    
    // 连接状态
    private bool isConnected = false;
    private string lastError = "";
    
    void OnEnable()
    {
        Debug.Log("[UDPDataReceiver] OnEnable");
    }

    void Start()
    {
        Debug.Log("[UDPDataReceiver] Start called");
        InitializeUDP();
        StartReceiving();
        UpdateStatusText("Started");
    }
    
    void OnDisable()
    {
        Debug.Log("[UDPDataReceiver] OnDisable");
        StopReceiving();
        CloseUDP();
        UpdateStatusText("Disabled");
    }
    void OnDestroy()
    {
        Debug.Log("[UDPDataReceiver] OnDestroy");
        StopReceiving();
        CloseUDP();
    
    }
    
    /// <summary>
    /// 初始化UDP连接
    /// </summary>
    private void InitializeUDP()
    {
        try
        {
            Debug.Log($"[UDPDataReceiver] InitializeUDP binding port {clientPort}");
            udpClient = new UdpClient(clientPort);
            udpClient.Client.ReceiveBufferSize = 65536; // 64KB缓冲区
            
            isConnected = true;
            Debug.Log($"UDP接收器初始化成功 - 监听端口: {clientPort}");
            UpdateStatusText($"Listening {clientPort}");
        }
        catch (Exception e)
        {
            lastError = $"UDP初始化失败: {e.Message}";
            Debug.LogError(lastError);
            isConnected = false;
            UpdateStatusText("Init Failed: " + e.Message);
        }
    }
    
    /// <summary>
    /// 开始接收数据
    /// </summary>
    public void StartReceiving()
    {
        if (isReceiving || !isConnected)
        {
            Debug.Log($"[UDPDataReceiver] StartReceiving skipped isReceiving={isReceiving} isConnected={isConnected}");
            return;
        }
        
        isReceiving = true;
        receiveThread = new Thread(ReceiveData);
        receiveThread.IsBackground = true;
        receiveThread.Start();
        
        Debug.Log("开始接收UDP数据");
        Debug.Log($"[UDPDataReceiver] expecting data from {serverIP}:{serverPort} -> local {clientPort}");
        UpdateStatusText("Receiving");
    }
    
    /// <summary>
    /// 停止接收数据
    /// </summary>
    public void StopReceiving()
    {
        isReceiving = false;
        
        if (receiveThread != null && receiveThread.IsAlive)
        {
            receiveThread.Join(1000); // 等待1秒
        }
        
        Debug.Log("停止接收UDP数据");
    }
    
    /// <summary>
    /// 关闭UDP连接
    /// </summary>
    private void CloseUDP()
    {
        try
        {
            if (udpClient != null)
            {
                udpClient.Close();
            }
            
            isConnected = false;
            Debug.Log("UDP连接已关闭");
        }
        catch (Exception e)
        {
            Debug.LogError($"关闭UDP连接失败: {e.Message}");
        }
    }
    
    /// <summary>
    /// 接收数据的主循环
    /// </summary>
    private void ReceiveData()
    {
        IPEndPoint remoteEP = new IPEndPoint(IPAddress.Any, 0);
        
        while (isReceiving)
        {
            try
            {
                if (udpClient == null)
                {
                    Debug.LogError("[UDPDataReceiver] udpClient is null in ReceiveData");
                    Thread.Sleep(100);
                    continue;
                }
                
                if (udpClient.Available > 0)
                {
                    byte[] data = udpClient.Receive(ref remoteEP);
                    string jsonString = Encoding.UTF8.GetString(data);
                    Debug.Log($"[UDPDataReceiver] raw json received from {remoteEP.Address}:{remoteEP.Port} len={data.Length}");
                    
                    ProcessReceivedData(jsonString);
                }
                else
                {
                    Thread.Sleep(10); // 避免CPU占用过高
                }
            }
            catch (SocketException)
            {
                // Socket异常通常表示没有更多数据，继续循环
                Thread.Sleep(10);
            }
            catch (Exception e)
            {
                if (isReceiving) // 只在正在接收时才记录错误
                {
                    Debug.LogError($"UDP接收数据错误: {e.Message}");
                }
                Thread.Sleep(100);
                Debug.LogError($"[UDPDataReceiver] ReceiveData exception: {e}");
            }
        }
    }
    
    /// <summary>
    /// 处理接收到的数据
    /// </summary>
    private void ProcessReceivedData(string jsonString)
    {

        try
        {
            JObject jsonData = JObject.Parse(jsonString);
            string dataType = jsonData["type"]?.ToString();
            Debug.Log($"[UDPDataReceiver] message type: {dataType}");
            Debug.Log($"[UDPDataReceiver] ProcessReceivedData json length: {jsonString?.Length}");
                    Debug.Log($"[UDP] 接收原始数据: {jsonString.Length} 字符");
                    Debug.Log($"[UDP] 数据类型: {dataType}");

                    if (dataType == "eeg_data")
                    {           
                        Debug.Log($"[UDP] EEG数据数组: {(jsonData["eeg_data"] as JArray)?.Count} 样本");
                    }
            
            // 提取EEG数据
            JArray eegDataArray = jsonData["eeg_data"] as JArray;
            if (eegDataArray != null && eegDataArray.Count > 0)
            {
                Debug.Log($"[UDPDataReceiver] ProcessEEGData arrays: {eegDataArray.Count}");
                // 转换为一维数组（所有通道数据）
                List<float> allChannels = new List<float>();
                
                foreach (var sampleArray in eegDataArray)
                {
                    JArray sample = sampleArray as JArray;
                    if (sample != null)
                    {
                        Debug.Log($"[UDPDataReceiver] Sample has {sample.Count} channels");
                        foreach (var channelValue in sample)
                        {
                            allChannels.Add(channelValue.Value<float>());
                        }
                    }
                }
            }
            switch (dataType)
            {
                case "connection_test":
                    Debug.Log("[UDPDataReceiver] connection_test received from server");
                    UpdateStatusText("connection_test");
                    break;
                case "eeg_data":
                    ProcessEEGData(jsonData);
                    break;
                    
                case "eeg_features":
                    ProcessFeaturesData(jsonData);
                    break;
                    
                case "status":
                    ProcessStatusData(jsonData);
                    break;
                    
                default:
                    Debug.LogWarning($"未知数据类型: {dataType}");
                    break;
            }
        }
        catch (Exception e)
        {
            Debug.LogError($"处理JSON数据错误: {e.Message}");
            UpdateStatusText("JSON parse error");
        }
    }
    
    /// <summary>
    /// 处理EEG数据
    /// </summary>
    private void ProcessEEGData(JObject jsonData)
    {
        try
        {
            // 提取EEG数据
            JArray eegDataArray = jsonData["eeg_data"] as JArray;
            if (eegDataArray != null && eegDataArray.Count > 0)
            {
                Debug.Log($"[UDPDataReceiver] ProcessEEGData arrays: {eegDataArray.Count}");
                // 转换为一维数组（所有通道数据）
                List<float> allChannels = new List<float>();
                
                foreach (var sampleArray in eegDataArray)
                {
                    JArray sample = sampleArray as JArray;
                    if (sample != null)
                    {
                        foreach (var channelValue in sample)
                        {
                            allChannels.Add(channelValue.Value<float>());
                        }
                    }
                }
                
                // 存储数据
                float[] channelData = allChannels.ToArray();
                float timestamp = jsonData["timestamp"]?.Value<float>() ?? Time.time;
                
                lock (dataLock)
                {
                    dataBuffer.Add(channelData);
                    timestamps.Add(timestamp);
                    
                    // 限制缓冲区大小
                    while (dataBuffer.Count > maxDataBufferSize)
                    {
                        dataBuffer.RemoveAt(0);
                        timestamps.RemoveAt(0);
                    }
                }
                
                // 触发事件（在主线程调用回调以避免 Unity API 在后台线程被调用）
                var capturedData = channelData;
                PimDeWitte.UnityMainThreadDispatcher.UnityMainThreadDispatcher.Instance()?.Enqueue(() => {
                    try
                    {
                        OnDataReceived?.Invoke(capturedData);
                    }
                    catch (Exception e)
                    {
                        Debug.LogError($"[UDPDataReceiver] Exception in OnDataReceived callback: {e}");
                    }
                });

                Debug.Log($"[UDPDataReceiver] Enqueued OnDataReceived. bufferSize={dataBuffer.Count}");
                UpdateStatusText($"Recv {dataBuffer.Count}");
            }
            else
            {
                Debug.LogWarning("[UDPDataReceiver] eeg_data empty or null");
            }
        }
        catch (Exception e)
        {
            Debug.LogError($"处理EEG数据错误: {e.Message}");
            UpdateStatusText("EEG process error");
        }
    }
    private void UpdateStatusText(string s)    {
        if (statusText != null)
        {
            // 在主线程更新 UI：使用 Unity 的主线程调度
            PimDeWitte.UnityMainThreadDispatcher.UnityMainThreadDispatcher.Instance()?.Enqueue(() => statusText.text = $"UDP: {s}");
        }
    }

    /// <summary>
    /// 处理特征数据
    /// </summary>
    private void ProcessFeaturesData(JObject jsonData)
    {
        try
        {
            // 这里可以处理特征数据
            JObject features = jsonData["features"] as JObject;
            if (features != null)
            {
                Debug.Log("收到EEG特征数据");
                // 可以在这里更新UI或保存特征数据
            }
        }
        catch (Exception e)
        {
            Debug.LogError($"处理特征数据错误: {e.Message}");
        }
    }
    
    /// <summary>
    /// 处理状态数据
    /// </summary>
    private void ProcessStatusData(JObject jsonData)
    {
        try
        {
            string status = jsonData["status"]?.ToString();
            string message = jsonData["message"]?.ToString();
            
            // 在主线程触发状态回调
            var s = status;
            var m = message;
            PimDeWitte.UnityMainThreadDispatcher.UnityMainThreadDispatcher.Instance()?.Enqueue(() => {
                try
                {
                    OnStatusReceived?.Invoke(s, m);
                }
                catch (Exception e)
                {
                    Debug.LogError($"[UDPDataReceiver] Exception in OnStatusReceived callback: {e}");
                }
            });

            Debug.Log($"状态信息: {status} - {message}");
        }
        catch (Exception e)
        {
            Debug.LogError($"处理状态数据错误: {e.Message}");
        }
    }
    
    /// <summary>
    /// 获取最新的EEG数据
    /// </summary>
    /// <param name="maxSamples">最大样本数</param>
    /// <returns>EEG数据数组</returns>
    public float[][] GetLatestData(int maxSamples = 100)
    {
        lock (dataLock)
        {
            if (dataBuffer.Count == 0) return null;
            
            int startIndex = Mathf.Max(0, dataBuffer.Count - maxSamples);
            float[][] result = new float[dataBuffer.Count - startIndex][];
            
            for (int i = startIndex; i < dataBuffer.Count; i++)
            {
                result[i - startIndex] = new float[dataBuffer[i].Length];
                Array.Copy(dataBuffer[i], result[i - startIndex], dataBuffer[i].Length);
            }
            
            return result;
        }
    }
    
    /// <summary>
    /// 获取特定通道的数据
    /// </summary>
    /// <param name="channelIndex">通道索引</param>
    /// <param name="maxSamples">最大样本数</param>
    /// <returns>通道数据</returns>
    public float[] GetChannelData(int channelIndex, int maxSamples = 100)
    {
        lock (dataLock)
        {
            if (dataBuffer.Count == 0 || channelIndex < 0) return null;
            
            int startIndex = Mathf.Max(0, dataBuffer.Count - maxSamples);
            List<float> channelData = new List<float>();
            
            for (int i = startIndex; i < dataBuffer.Count; i++)
            {
                if (channelIndex < dataBuffer[i].Length)
                {
                    channelData.Add(dataBuffer[i][channelIndex]);
                }
            }
            
            return channelData.ToArray();
        }
    }
    
    /// <summary>
    /// 清除数据缓冲区
    /// </summary>
    public void ClearBuffer()
    {
        lock (dataLock)
        {
            dataBuffer.Clear();
            timestamps.Clear();
        }
        
        Debug.Log("数据缓冲区已清除");
    }
    
    /// <summary>
    /// 发送消息到服务器
    /// </summary>
    /// <param name="message">消息内容</param>
    public void SendMessageToServer(string message)
    {
        try
        {
            if (!isConnected) return;
            
            // 这里可以添加发送消息的逻辑
            // 例如：ping、请求数据等
        }
        catch (Exception e)
        {
            Debug.LogError($"发送消息失败: {e.Message}");
        }
    }
    
    // 获取连接状态
    public bool IsConnected => isConnected && isReceiving;
    public string LastError => lastError;
    public int BufferSize => dataBuffer.Count;
}
