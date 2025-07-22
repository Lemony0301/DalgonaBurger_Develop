'use client';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Label,
} from 'recharts';
import React from 'react';

// 정규분포 곡선 좌표를 생성합니다.
function getNormalPoints(values, mean, stdDev) {
  const min = Math.min(...values);
  const max = Math.max(...values);

  // 모든 값이 동일하면 단일 점만 반환
  if (max === min) return [{ x: min, y: 1 }];

  const step = (max - min) / 100;
  return Array.from({ length: 101 }, (_, i) => {
    const x = min + step * i;
    const y =
      (1 / (stdDev * Math.sqrt(2 * Math.PI))) *
      Math.exp(-((x - mean) ** 2) / (2 * stdDev ** 2));
    return { x, y: Number(y.toFixed(6)) };
  });
}

// 점수가 어느 등급 구간에 속하는지 반환합니다.
function getGrade(x, boundaries) {
  if (x <= boundaries[0]) return 'S';
  if (x <= boundaries[1]) return 'A';
  if (x <= boundaries[2]) return 'B';
  if (x <= boundaries[3]) return 'C';
  return 'D';
}

export default function NormalDistChart({ values = [], label, rawData = [], field }) {
  // 로딩 상태 처리
  if (!values.length) return <p>데이터 로딩 중…</p>;

  // 평균 & 표준편차 계산
  const mean = values.reduce((a, b) => a + b, 0) / values.length;
  const variance = values.reduce((a, b) => a + (b - mean) ** 2, 0) / values.length;
  const stdDev = Math.sqrt(variance);

  // 값이 모두 같으면 분포를 그릴 수 없음
  if (stdDev === 0) {
    return <p>분포를 그릴 수 없습니다 (모든 값 동일).</p>;
  }

  // 등급 경계선 정의 (S/A, A/B, B/C, C/D)
  const boundaries = [
    mean - 1.5 * stdDev,
    mean - 0.5 * stdDev,
    mean + 0.5 * stdDev,
    mean + 1.5 * stdDev,
  ];

  // 분포 곡선 포인트 계산
  const points = getNormalPoints(values, mean, stdDev);

  // 등급별로 유저를 그룹핑
  const bucketMap = { S: [], A: [], B: [], C: [], D: [] };
  rawData.forEach((d) => {
    const val = Number(d[field]);
    if (!isNaN(val)) {
      const grade = getGrade(val, boundaries);
      bucketMap[grade].push({ id: d.id, value: val });
    }
  });

  // 커스텀 툴팁
  const CustomTooltip = ({ active, label: hoveredX }) => {
    if (!active || hoveredX == null) return null;
    const x = parseFloat(hoveredX);
    const grade = getGrade(x, boundaries);
    const users = bucketMap[grade];

    return (
      <div style={{ background: "var(--bg-color)", padding: 10, border: '1px solid #ccc' }}>
        <strong>
          {grade} 등급 ({users.length}명)
        </strong>
        <ul style={{ margin: 0, paddingLeft: 12, maxHeight: 100, overflowY: 'auto' }}>
          {users.slice(0, 5).map((u) => (
            <li key={u.id}>
              {u.id} ({u.value})
            </li>
          ))}
          {users.length > 5 && <li>외 {users.length - 5}명…</li>}
        </ul>
      </div>
    );
  };

  // 경계선 레이블 (등급 & 값) 렌더러
  const renderBoundary = (xVal, idx) => {
    const gradeLabel = ['S/A', 'A/B', 'B/C', 'C/D'][idx];
    const valueLabel = xVal % 1 === 0 ? xVal.toString() : xVal.toFixed(1);

    return (
      <React.Fragment key={idx}>
        {/* 상단 등급 라벨 */}
        <ReferenceLine
          x={xVal}
          stroke="gray"
          strokeDasharray="4 2"
          label={{
            value: gradeLabel,
            position: 'top',
            fontSize: 10,
            fill: "var(--boundary-line)",
          }}
        />
        
        {/* 하단 값 라벨 (투명선) */}
        <ReferenceLine
          x={xVal}
          stroke="transparent"
          label={{
            value: valueLabel,
            position: 'bottom',
            fontSize: 10,
            fill: "var(--boundary-line)",
          }}
        />
      </React.Fragment>
    );
  };

  return (
    <ResponsiveContainer width="100%" height={320}>
      <LineChart data={points} margin={{ top: 20, right: 40, left: 50, bottom: 50 }}>
        <CartesianGrid stroke="var(--grid-line)" strokeDasharray="3 3" />
        <XAxis
          type="number"
          dataKey="x"
          domain={['dataMin', 'dataMax']}
          tick={{ fontSize: 12 }}
          label={{
            value: label,
            position: 'insideBottom',
            offset: -10,
            style: { fontSize: 12 },
          }}
        />
        <YAxis
          type="number"
          dataKey="y"
          domain={['dataMin', 'dataMax']}
          tick={{ fontSize: 12 }}
          label={{
            value: 'P(x)',
            angle: -90,
            position: 'insideLeft',
            offset: -10,
            style: { fontSize: 12 },
          }}
        />
        <Tooltip content={<CustomTooltip />} />
        <Line type="natural" dataKey="y" stroke="var(--chart-line)" dot={false} />

        {/* 경계선 + 레이블 */}
        {boundaries.map(renderBoundary)}
      </LineChart>
    </ResponsiveContainer>
  );
}
