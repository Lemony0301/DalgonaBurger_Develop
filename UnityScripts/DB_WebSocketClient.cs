using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.UI;
using WebSocketSharp;

// ───────── 서버 응답 매핑 ─────────
[System.Serializable]
public class ServerResponse
{
    public bool ack;
    public string error;
    public string received_text;
}

// ───────── 클라이언트 → 서버 페이로드 ─────────
[System.Serializable]
public class RunLog
{
    public string id;
    public string stage;
    public int tokens;
    public int clear_time;
    
}

public class DB_WebSocketClient : MonoBehaviour
{
    [Header("UI References")]
    public InputField idField;
    public InputField tokensField;
    public InputField clearTimeField;
    public InputField stageField;
    public Button sendButton;
    public Text logText;

    private WebSocket ws;

    private readonly System.Action<System.Action> EnqueueOnMain =
        action => UnityMainThreadDispatcher.Instance().Enqueue(action);

    void Start()
    {
        ws = new WebSocket("ws://192.168.55.82:8001/ws");

        ws.OnOpen += (_, __) => Debug.Log("✅ Connected to WebSocket Server");
        ws.OnMessage += (_, e) =>
        {
            var res = JsonUtility.FromJson<ServerResponse>(e.Data);
            EnqueueOnMain(() =>
            {
                if (res != null && res.ack)
                    logText.text = $"서버 ACK ✅\n메시지: {res.received_text}";
                else
                    logText.text = $"서버 거부 ❌\n원인: {res?.error ?? "unknown"}";
            });
        };
        ws.OnError += (_, e) => Debug.LogError($"WebSocket Error: {e.Message}");
        ws.OnClose += (_, e) => Debug.Log($"🔌 Disconnected: {e.Reason}");

        ws.ConnectAsync();
        sendButton.onClick.AddListener(SendRunLog);
    }

    private void SendRunLog()
    {
        

        if (ws.ReadyState != WebSocketState.Open)
        {
            logText.text = "⚠ 서버에 연결되어 있지 않습니다.";
            return;
        }

        string id = idField.text.Trim();
        if (string.IsNullOrEmpty(id))
        {
            logText.text = "⚠ ID를 입력하세요.";
            return;
        }

        if (!int.TryParse(tokensField.text, out int tokens) || tokens < 0)
        {
            logText.text = "⚠ 토큰 수가 올바르지 않습니다.";
            return;
        }

        if (!int.TryParse(clearTimeField.text, out int clearTime) || clearTime < 0)
        {
            logText.text = "⚠ 클리어 시간이 올바르지 않습니다.";
            return;
        }
        
        string stage = stageField.text.Trim();
        if (string.IsNullOrEmpty(stage))
        {
            logText.text = "⚠ 스테이지 번호가 올바르지 않습니다.";
            return;
        }

        RunLog payload = new RunLog
        {
            id = id,
            stage = stage,
            tokens = tokens,
            clear_time = clearTime
        };
        string json = JsonUtility.ToJson(payload);

        ws.Send(json);
        Debug.Log($"⇒ Sent: {json}");
    }

    void OnApplicationQuit()
    {
        ws?.Close();
        ws = null;
    }
}