import { useEffect, useRef, useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";

const stageList = [
  "A1", "A2", "A3", "A4", "A5",
  "B1", "B2", "B3", "B4", "B5",
  "C1", "C2", "C3", "C4", "C5",
  "D1", "D2", "D3", "D4", "D5",
  "E1", "E2", "E3", "E4", "E5",
];

function formatDate(dateString) {
  const d = new Date(dateString);
  if (isNaN(d)) return "-";
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ` +
         `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

export default function Dashboard({ pageId }) {
  const [raw, setRaw] = useState([]);
  const navigate = useNavigate();

  const stage = pageId;

  useEffect(() => {
    const ws = new WebSocket("ws://192.168.55.82:8001/chart");
    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      if (msg.type === "snapshot") setRaw(msg.rows);
      else setRaw((prev) => [...prev.slice(-499), msg]);
      console.log("WS message:", msg);
    };
    return () => ws.close();
  }, []);

  const filteredData = useMemo(() => {
    const bestById = new Map();
    for (const d of raw) {
      if (d.stage !== stage) continue;

      const current = bestById.get(d.id);
      const better =
        !current ||
        Number(d.tokens) < Number(current.tokens) ||
        (Number(d.tokens) === Number(current.tokens) &&
          Number(d.clear_time) < Number(current.clear_time));

      if (better) bestById.set(d.id, d);
    }

    return [...bestById.values()]
      .sort((a, b) =>
        Number(a.tokens) - Number(b.tokens) ||
        Number(a.clear_time) - Number(b.clear_time)
      )
      .map((d, i) => ({
        no: i + 1,
        id: d.id,
        tokens: Number(d.tokens),
        clearSecs: (Number(d.clear_time) / 1000).toFixed(2),
        createdAt: formatDate(d.created_at),
      }));
  }, [raw, stage]);

  const handleStageChange = (e) => {
    const selected = e.target.value;
    navigate(`/dashboard/${selected}`);
  };

  return (
    <div className="page-wrap">
      <h3>📊 대쉬보드 - Stage {stage} 결과</h3>

      <select
        value={stage}
        onChange={handleStageChange}
        style={{ margin: "12px 0", padding: "4px 8px" }}
      >
        {stageList.map((s) => (
          <option key={s} value={s}>Stage {s}</option>
        ))}
      </select>

      <table style={{
        width: "100%",
        borderCollapse: "collapse",
        marginTop: 12,
        textAlign: "center",
      }}>
        <thead>
          <tr style={{ background: "#555", color: "#fff" }}>
            <th>순위</th>
            <th>ID</th>
            <th>Tokens</th>
            <th>Clear Time (s)</th>
            <th>created At</th>
          </tr>
        </thead>
        <tbody>
          {filteredData.length === 0 ? (
            <tr>
              <td colSpan={5}>데이터가 없습니다.</td>
            </tr>
          ) : (
            filteredData.map(d => (
              <tr key={d.id}>
                <td>{d.no}</td>
                <td>{d.id}</td>
                <td>{d.tokens}</td>
                <td>{d.clearSecs}</td>
                <td>{d.createdAt}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}