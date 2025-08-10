import { useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import "@/styles/globals.css";
import HeaderNav from "@/components/HeaderNav";

export default function App({ Component, pageProps }) {
  return (
    <>
      <HeaderNav /> {/* 상단 공통 네비게이션 */}
      <Component {...pageProps} />
    </>
  );
}