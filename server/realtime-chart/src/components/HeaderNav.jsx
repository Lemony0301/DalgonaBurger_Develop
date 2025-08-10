import { useState, useEffect } from "react";

export default function HeaderNav() {
  const [dark, setDark] = useState(() => localStorage.getItem("theme") === "dark");

  /* 다크모드 토글 */
  useEffect(() => {
    document.body.classList.toggle("dark", dark);
    localStorage.setItem("theme", dark ? "dark" : "light");
  }, [dark]);

  return (
    <nav className="top-bar">
      {/* ───── 왼쪽: 사이트 명 ───── */}
      <span className="site-title">
        달고나 부거 WEBUI
      </span>

      {/* ───── 가운데: 메뉴 링크 ───── */}
      <div className="menu">
        <a href="/dashboard/A1">📊 대시보드</a>
        <a href="/distribution">📈 정규분포</a>
      </div>

      {/* ───── 오른쪽: 다크모드 토글 ───── */}
      <button onClick={() => setDark((p) => !p)}>
        {dark ? "☀️ Light" : "🌙 Dark"}
      </button>
    </nav>
  );
}