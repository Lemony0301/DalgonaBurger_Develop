import { useEffect, useRef, useState, useMemo } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from "recharts";

export default function ChartLive() {
  /* ───── 상태 ───── */
  const [raw, setRaw] = useState([]);
  const [stage, setStage] = useState(11);   // int 값
  const wsRef = useRef(null);

  /* ───── WebSocket 연결 ───── */
  useEffect(() => {
    const ws = new WebSocket("ws://192.168.55.82:8001/chart");
    wsRef.current = ws;

    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data);

      // 서버가 보내는 메시지 타입은 2가지:
      //  ① {type:'snapshot', rows:[...]}
      //  ② {id, stage, tokens, clear_time, ...}  (실시간 단건)
      if (msg.type === "snapshot" && Array.isArray(msg.rows)) {
        setRaw(msg.rows);                      // 스냅샷으로 초기화
      } else {
        setRaw((prev) => [...prev.slice(-499), msg]); // 새 데이터 추가
      }
    };

    return () => ws.close();
  }, []);

  /* ───── Recharts용 데이터 변환 ───── */
  const chartData = useMemo(() => {
    const s = Number(stage);

    /* ① 같은 id 중 토큰·클리어시간이 가장 낮은 것만 남긴다 */
    const bestById = new Map();
    for (const d of raw) {
      if (Number(d.stage) !== s) continue;     // 선택된 stage만
      const key = d.id;
      const current = bestById.get(key);

      const better =
        !current ||
        Number(d.tokens) < Number(current.tokens) ||
        (Number(d.tokens) === Number(current.tokens) &&
          Number(d.clear_time) < Number(current.clear_time));

      if (better) bestById.set(key, d);
    }

    /* ② Map → 배열 변환 후 정렬(토큰↑, 시간↑) */
    return [...bestById.values()]
      .sort((a, b) =>
        Number(a.tokens) !== Number(b.tokens)
          ? Number(a.tokens) - Number(b.tokens)
          : Number(a.clear_time) - Number(b.clear_time)
      )
      .map((d) => ({
        id: d.id,
        tokens: Number(d.tokens),
        clearSecs: Number(d.clear_time) / 1000,
      }));
  }, [raw, stage]);

  /* ───── UI ───── */
  return (
    <div style={{ padding: 24 }}>
      <h3>Stage {stage} – 토큰 &amp; 클리어시간</h3>

      {/* Stage 선택 (int) */}
      <select
        value={stage}
        onChange={(e) => setStage(Number(e.target.value))}
        style={{ marginBottom: 12, padding: "4px 8px" }}
      >
        {[11, 12, 13, 14, 15].map((s) => (
          <option key={s} value={s}>
            Stage {s}
          </option>
        ))}
      </select>

      <div style={{ width: "110%", maxWidth: 900, margin: "0 auto" }}>
        <ResponsiveContainer width="100%" height={360}>
          <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="id" />
          {/* 왼쪽 Y축: 토큰 */}
          <YAxis
            yAxisId="left"
            orientation="left"
            label={{ value: "Token", angle: -90, position: "insideLeft" }}
          />
          {/* 오른쪽 Y축: 클리어 초 */}
          <YAxis
            yAxisId="right"
            orientation="right"
            label={{ value: "Sec", angle: -90, position: "insideRight" }}
          />
          <Tooltip />
          <Legend />
          <Bar yAxisId="left"  dataKey="tokens"    name="Tokens"          fill="#8884d8" />
          <Bar yAxisId="right" dataKey="clearSecs" name="Clear Time (s)"  fill="#82ca9d" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}