'use client';
import { useEffect, useState } from 'react';
import NormalDistChart from '@/components/NormalDistChart';

const STAGES = [
  'A1', 'A2', 'A3', 'A4', 'A5',
  'B1', 'B2', 'B3', 'B4', 'B5',
  'C1', 'C2', 'C3', 'C4', 'C5',
  'D1', 'D2', 'D3', 'D4', 'D5',
  'E1', 'E2', 'E3', 'E4', 'E5',
];

export default function DistributionPage() {
  const [raw, setRaw] = useState([]);
  const [field, setField] = useState('tokens');
  const [selectedStage, setSelectedStage] = useState('ALL');

  // WebSocket 연결
  useEffect(() => {
    const ws = new WebSocket('ws://192.168.55.82:8001/chart');
    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      if (msg.type === 'snapshot') setRaw(msg.rows);
      else setRaw((prev) => [...prev.slice(-499), msg]);
    };
    return () => ws.close();
  }, []);

  // 스테이지 별 최상 기록 계산
  const getBestRecordsByStage = (stage) => {
    const bestById = new Map();
    raw
      .filter((d) => d.stage === stage && !isNaN(Number(d[field])))
      .forEach((d) => {
        const id = d.id;
        const current = bestById.get(id);
        const better =
          !current ||
          Number(d.tokens) < Number(current.tokens) ||
          (Number(d.tokens) === Number(current.tokens) &&
            Number(d.clear_time) < Number(current.clear_time));
        if (better) bestById.set(id, d);
      });
    return [...bestById.values()];
  };

  const visibleStages = selectedStage === 'ALL' ? STAGES : [selectedStage];

  if (!raw.length) {
    return <p style={{ padding: 24 }}>웹소켓에서 데이터를 기다리는 중…</p>;
  }

  return (
    <div className="page-wrap">
      <h2>📈 정규분포 그래프</h2>

      <label style={{ marginRight: 8 }}>분석 항목:</label>
      <select
        value={field}
        onChange={(e) => setField(e.target.value)}
        style={{ marginRight: 24, padding: '4px 8px' }}
      >
        <option value="tokens">tokens</option>
        <option value="clear_time">clear_time (ms)</option>
      </select>

      <label style={{ marginRight: 8 }}>스테이지 선택:</label>
      <select
        value={selectedStage}
        onChange={(e) => setSelectedStage(e.target.value)}
        style={{ padding: '4px 8px', marginBottom: 24 }}
      >
        <option value="ALL">전체 보기</option>
        {STAGES.map((s) => (
          <option key={s} value={s}>
            {s}
          </option>
        ))}
      </select>

      {visibleStages.map((stage) => {
        const bestRecords = getBestRecordsByStage(stage);
        if (bestRecords.length < 5) return null; // 데이터가 부족한 스테이지는 스킵

        const values = bestRecords.map((d) => Number(d[field]));

        return (
          <div key={stage} style={{ marginBottom: 48 }}>
            <h4>
              📊 정규분포 – {stage} ({values.length}명)
            </h4>
            <NormalDistChart
              values={values}
              label={`${field} (${stage})`}
              rawData={bestRecords}
              field={field}
            />
          </div>
        );
      })}
    </div>
  );
}