import { useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import './App.css'

import ChartLive from "./ChartLive";   // ① 상대 경로 import

function App() {
  return (
    <div style={{ padding: 24 }}>
      <h2>실시간 토큰 차트</h2>
      <ChartLive />                    {/* ② 컴포넌트 사용 */}
    </div>
  );
}

export default App
