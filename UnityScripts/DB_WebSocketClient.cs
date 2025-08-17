using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Networking;
using UnityEngine.UI;
using WebSocketSharp;

[Serializable] public class ServerResponse { public bool ack; public string error; public string received_text; }

[Serializable]
public class RunLog  // 서버 스키마와 1:1 매칭
{
    public string user_id;        // ex) "player_001"
    public string stage_code;     // ex) "A1"
    public int    prompt_length;  // 사용한 단어 수
    public int    clear_time_ms;  // ms
}

[Serializable] public class CreateUserReq { public string user_id; }

[Serializable]
public class StageProgress {
    public string code; public bool unlocked; public bool cleared;
    public int prompt_length; public int clear_time_ms; public string cleared_at;
}

[Serializable]
public class ProgressResponse {
    public string user_id; public List<StageProgress> stages;
}

[Serializable]
public class GameResultResponse
{
    public bool ack;
    public string user_id;
    public string stage;
    public float rank_clear_time_percent; // 상위 %
    public float rank_tokens_percent;     // 상위 %
    public int rank_clear_time;         // 등수
    public int rank_tokens;             // 등수
    public int total_records;           // 총 기록 수
    public string received_text;
}

    public class DB_WebSocketClient : MonoBehaviour
    {
        [Header("API Base")]
        public string restBaseUrl = "https://192.168.55.82:8001";
        public string wsUrl = "wss://192.168.55.82:8001/ws";

        [Header("UI References")]
        public InputField idField;
        public InputField tokensField;
        public InputField clearTimeField;   // ms
        public InputField stageField;
        public Button registerButton;
        public Button refreshProgressButton;   // 수동 새로고침 버튼
        public Button sendButton;
        public Text logText;

        private WebSocket ws;

        // ---- 개발용: 자체서명 인증서 우회(HTTPS/WSS 테스트 편의용) ----
        class DevCertBypass : CertificateHandler { protected override bool ValidateCertificate(byte[] certData) => true; }
        bool IsHttps(string url) => url.StartsWith("https://", StringComparison.OrdinalIgnoreCase);
        bool IsWss(string url) => url.StartsWith("wss://", StringComparison.OrdinalIgnoreCase);

        // --- 간단한 메인스레드 디스패처 ---
        private readonly Queue<Action> _mainQ = new Queue<Action>();
        private readonly object _mainLock = new object();
        void RunOnMain(Action a) { if (a == null) return; lock (_mainLock) _mainQ.Enqueue(a); }
        void Update()
        {
            while (true)
            {
                Action a = null;
                lock (_mainLock) { if (_mainQ.Count > 0) a = _mainQ.Dequeue(); }
                if (a == null) break;
                try { a(); } catch (Exception ex) { Debug.LogError("[MainQ] " + ex); }
            }
        }

        // PlayerPrefs
        const string PREF_USER_ID = "user_id";
        void SaveUserId(string uid) => PlayerPrefs.SetString(PREF_USER_ID, uid);
        string LoadUserId() => PlayerPrefs.GetString(PREF_USER_ID, string.Empty);

        // --- UnityWebRequest helpers ---
        IEnumerator PostJson(string url, string json, Action<string> onOk, Action<string> onErr)
        {
            using (var req = new UnityWebRequest(url, "POST"))
            {
                var bodyRaw = System.Text.Encoding.UTF8.GetBytes(json);
                req.uploadHandler = new UploadHandlerRaw(bodyRaw);
                req.downloadHandler = new DownloadHandlerBuffer();
                req.SetRequestHeader("Content-Type", "application/json");
                req.timeout = 10; // 타임아웃

                if (IsHttps(url)) req.certificateHandler = new DevCertBypass(); // 개발용

                yield return req.SendWebRequest();
                if (req.result == UnityWebRequest.Result.Success) onOk?.Invoke(req.downloadHandler.text);
                else onErr?.Invoke($"HTTP {(long)req.responseCode} {req.error} :: {req.downloadHandler.text}");
            }
        }

        IEnumerator GetJson(string url, Action<string> onOk, Action<string> onErr)
        {
            using (var req = UnityWebRequest.Get(url))
            {
                req.timeout = 10;
                if (IsHttps(url)) req.certificateHandler = new DevCertBypass(); // 개발용
                yield return req.SendWebRequest();

                if (req.result == UnityWebRequest.Result.Success) onOk?.Invoke(req.downloadHandler.text);
                else onErr?.Invoke($"HTTP {(long)req.responseCode} {req.error} :: {req.downloadHandler.text}");
            }
        }

        void Awake() { DontDestroyOnLoad(gameObject); }

        void Start()
        {
            // --- WebSocket ---
            ws = new WebSocket(wsUrl);

            ws.OnOpen += (_, __) =>
            {
                RunOnMain(() =>
                {
                    Debug.Log("✅ WS connected");
                    SetStatus("WS connected");
                    StartCoroutine(Heartbeat());
                    // ⚠️ 자동 진행 조회/출력 금지
                });
            };

            ws.OnMessage += (__, e) =>
            {
                RunOnMain(() =>
                {
                    try
                    {
                        // 게임 결과(퍼센트) 수신은 계속 보여줌 (요청 기능)
                        if (e.Data.Contains("rank_clear_time_percent") || e.Data.Contains("rank_tokens_percent"))
                        {
                            var gr = JsonUtility.FromJson<GameResultResponse>(e.Data);
                            if (gr != null && gr.ack)
                            {
                                string msg =
                                    $"유저ID: {gr.user_id}\n" +
                                    $"스테이지: {gr.stage}\n" +
                                    $"클리어타임: 상위 {gr.rank_clear_time_percent:F1}% · {gr.rank_clear_time}위\n" +
                                    $"단어수:     상위 {gr.rank_tokens_percent:F1}% · {gr.rank_tokens}위\n";
                                SetStatus(msg);
                            }
                            return;
                        }
                        // 일반 ACK/에러 → 메시지만 표시, 진행 출력/조회는 안 함
                        else if (e.Data.Contains("\"ack\""))
                        {
                            var res = JsonUtility.FromJson<ServerResponse>(e.Data);
                            if (res != null && res.ack) logText.text = $"서버 ACK ✅\n메시지: {res.received_text}";
                            else logText.text = $"서버 거부 ❌\n원인: {res?.error ?? "unknown"}";
                            return;
                        }
                        else
                        {
                            // 기타 알림
                            logText.text = $"WS msg: {e.Data}";
                            return;
                        }
                    }
                    catch (Exception ex2) { Debug.LogError("OnMessage parse fail: " + ex2); }
                });
            };

            ws.OnError += (_, e) => RunOnMain(() => { Debug.LogError($"WS Error: {e.Message}"); SetStatus("WS Error: " + e.Message); });
            ws.OnClose += (_, e) => RunOnMain(() => { var msg = $"WS Closed: code={e.Code}, wasClean={e.WasClean}, reason={e.Reason}"; Debug.LogWarning(msg); SetStatus(msg); });

            ws.ConnectAsync();

            // --- Buttons ---
            if (registerButton) registerButton.onClick.AddListener(OnClickRegister);
            if (refreshProgressButton) refreshProgressButton.onClick.AddListener(OnClickRefreshProgress);
            if (sendButton) sendButton.onClick.AddListener(SendRunLog);

            // --- 저장된 ID 복구 (출력은 하지 않음) ---
            var savedId = LoadUserId();
            if (!string.IsNullOrEmpty(savedId))
            {
                if (idField) idField.text = savedId;
                SetStatus($"🔑 Saved ID: {savedId}");
                // ⚠️ 자동 진행 조회/출력 금지
            }
            else
            {
                SetStatus("🆔 Enter ID and press 'ID 등록'.");
            }
        }

        IEnumerator Heartbeat()
        {
            var wait = new WaitForSeconds(20f);
            while (true)
            {
                if (ws != null && ws.ReadyState == WebSocketState.Open)
                {
                    try { ws.Ping(); } catch (Exception ex) { Debug.LogWarning("Ping fail: " + ex.Message); }
                }
                yield return wait;
            }
        }

        // ---- Register user (REST) ----
        void OnClickRegister()
        {
            string uid = idField ? idField.text.Trim() : "";
            if (string.IsNullOrEmpty(uid)) { SetStatus("⚠ ID를 입력하세요."); return; }

            SetStatus("⏳ Registering...");
            string json = JsonUtility.ToJson(new CreateUserReq { user_id = uid });

            StartCoroutine(PostJson($"{restBaseUrl}/users", json,
                onOk: _ =>
                {
                    SaveUserId(uid);
                    SetStatus($"✅ ID 등록 완료: {uid}");
                    // ✅ 등록에 성공한 “이때만” 해금 스테이지 출력
                    StartCoroutine(FetchProgressAndMaybePrint(uid, showOutput: true));
                },
                onErr: err => SetStatus($"❌ ID 등록 실패: {err}")
            ));
        }

        // ---- 수동 새로고침 ----
        void OnClickRefreshProgress()
        {
            string uid = idField ? idField.text.Trim() : "";
            if (string.IsNullOrEmpty(uid)) { SetStatus("⚠ ID를 입력하세요."); return; }
            // ✅ 버튼을 눌렀을 때만 출력
            StartCoroutine(FetchProgressAndMaybePrint(uid, showOutput: true));
        }

        // ---- 진행 조회 (출력 여부 제어) ----
        IEnumerator FetchProgressAndMaybePrint(string uid, bool showOutput)
        {
            yield return GetJson($"{restBaseUrl}/progress/{UnityWebRequest.EscapeURL(uid)}",
                onOk: text =>
                {
                    // JsonUtility null 가드(필요 시 Newtonsoft.Json 권장)
                    text = text.Replace(":null", ":0");
                    var resp = JsonUtility.FromJson<ProgressResponse>(text);
                    if (resp == null || resp.stages == null)
                    {
                        if (showOutput) SetStatus("⚠ 진행 정보 파싱 실패");
                        return;
                    }

                    var unlocked = new List<string>();
                    foreach (var s in resp.stages) if (s.unlocked) unlocked.Add(s.code);
                    if (showOutput)
                    {
                        SetStatus("🔓 해금된 스테이지: " + (unlocked.Count > 0 ? string.Join(", ", unlocked) : "(없음)"));
                    }
                    // showOutput=false 인 경우엔 조용히 끝
                },
                onErr: err =>
                {
                    if (showOutput) SetStatus($"❌ 진행 조회 실패: {err}");
                }
            );
        }

        // ---- Send clear log (WS) ----
        void SendRunLog()
        {
            if (ws == null || ws.ReadyState != WebSocketState.Open) { SetStatus("⚠ WS 미연결"); return; }

            string uid = idField ? idField.text.Trim() : "";
            if (string.IsNullOrEmpty(uid)) { SetStatus("⚠ ID를 입력하세요."); return; }

            if (!int.TryParse(tokensField ? tokensField.text : "0", out int tokens) || tokens < 0)
            { SetStatus("⚠ 토큰 수가 올바르지 않습니다."); return; }

            if (!int.TryParse(clearTimeField ? clearTimeField.text : "0", out int clearTime) || clearTime < 0)
            { SetStatus("⚠ 클리어 시간이 올바르지 않습니다.(ms)"); return; }

            string stage = stageField ? stageField.text.Trim() : "";
            if (string.IsNullOrEmpty(stage)) { SetStatus("⚠ 스테이지 코드가 올바르지 않습니다.(예:A1)"); return; }

            var payload = new RunLog
            {
                user_id = uid,
                stage_code = stage,
                prompt_length = tokens,
                clear_time_ms = clearTime
            };
            string json = JsonUtility.ToJson(payload);
            try { ws.Send(json); Debug.Log("⇒ Sent(ws): " + json); }
            catch (Exception ex) { SetStatus("WS send error: " + ex.Message); }
        }

        void SetStatus(string msg) { if (logText) logText.text = msg; Debug.Log(msg); }

        void OnApplicationQuit()
        {
            if (registerButton) registerButton.onClick.RemoveListener(OnClickRegister);
            if (refreshProgressButton) refreshProgressButton.onClick.RemoveListener(OnClickRefreshProgress);
            if (sendButton) sendButton.onClick.RemoveListener(SendRunLog);

            try { ws?.Close(); } catch { }
            ws = null;
        }
    }
