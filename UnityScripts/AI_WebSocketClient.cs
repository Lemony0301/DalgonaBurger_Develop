using UnityEngine;
using UnityEngine.UI;
using WebSocketSharp;
using System.Collections.Generic;

// ───────────────────────────────────
// ① (단일) 동작 응답 모델 ★
// ───────────────────────────────────
[System.Serializable]
public class ActionResponse
{
    public string code;                             // 동작 종류 (예: "Jump")
    public int promptLen;                           // 프롬프트 문자열 길이
    public string error;                            // 오류 메시지(null = 정상)
}

// ───────────────────────────────────
// ② 클라이언트 → AI 서버 제출 모델 (변경 없음)
// ───────────────────────────────────
[System.Serializable] public class PromptRequest
{
    public string userId;                           // 플레이어 ID
    public string stageId;                          // 스테이지 ID(옵션)
    public string prompt;                           // 프롬프트
}

public class AI_WebSocketClient : MonoBehaviour
{
    [Header("API Base")]
    public string wsUrl = "ws://192.168.55.82:8002/ws";

    [Header("UI References")]
    // ── UI 컴포넌트 참조 ──
    public InputField userIdField;                  // 유저 ID 입력란
    public InputField stageIdField;                 // 스테이지 ID 입력란
    public InputField promptField;                  // 프롬프트 입력란
    public Button sendButton;                       // “전송” 버튼
    public Text logText;                            // 로그 출력 UI

    // ── 네트워크 객체 ──
    private WebSocket ws;                           // WebSocket 세션

    // Main Thread 디스패처 (UI 업데이트)
    private readonly System.Action<System.Action> EnqueueOnMain =
        action => UnityMainThreadDispatcher.Instance().Enqueue(action);

    // ──────────────────
    // 1) 연결 및 이벤트 바인딩
    // ──────────────────
    void Start()
    {
        ws = new WebSocket(wsUrl);     // AI 서버 주소

        ws.OnOpen    += (_, __) => Debug.Log("✅ Connected to AI WebSocket Server");
        ws.OnMessage += (_,  e) => HandleServerMessage(e.Data);
        ws.OnError   += (_,  e) => Debug.LogError($"WebSocket Error: {e.Message}");
        ws.OnClose   += (_,  e) => Debug.Log($"🔌 Disconnected: {e.Reason}");

        ws.ConnectAsync();
        sendButton.onClick.AddListener(SendPrompt);
    }

    // ──────────────────
    // 2) 프롬프트 전송
    // ──────────────────
    private void SendPrompt()
    {
        if (ws.ReadyState != WebSocketState.Open)
        {
            logText.text = "⚠ 서버에 연결되어 있지 않습니다.";
            return;
        }

        string userId  = userIdField.text.Trim();
        string stageId = stageIdField.text.Trim();
        string prompt  = promptField.text.Trim();

        if (string.IsNullOrEmpty(userId))
        {
            logText.text = "⚠ 유저 ID를 입력하세요.";
            return;
        }
        if (string.IsNullOrEmpty(stageId))
        {
            logText.text = "⚠ Stage를 입력하세요.";
            return;
        }
        if (string.IsNullOrEmpty(prompt))
        {
            logText.text = "⚠ 프롬프트를 입력하세요.";
            return;
        }

        PromptRequest req = new PromptRequest
        {
            userId  = userId,
            stageId = string.IsNullOrEmpty(stageId) ? null : stageId,
            prompt  = prompt
        };

        ws.Send(JsonUtility.ToJson(req));           // 직렬화 후 전송
    }

    // ──────────────────
    // 3) 서버 응답 처리 ★
    // ──────────────────
    private void HandleServerMessage(string json)
    {
        var res = JsonUtility.FromJson<ActionResponse>(json); // 단순 구조

        EnqueueOnMain(() =>
        {
            if (!string.IsNullOrEmpty(res.error))
            {
                logText.text = $"❌ 에러: {res.error}";
                return;
            }

            // 로그 예시 출력
            logText.text =
                $"✅ 동작: {res.code}\n" +
                $"프롬프트 길이: {res.promptLen}";

        });
    }

    // ──────────────────
    // 4) 종료 시 연결 정리
    // ──────────────────
    void OnApplicationQuit()
    {
        ws?.CloseAsync();
        ws = null;
    }
}