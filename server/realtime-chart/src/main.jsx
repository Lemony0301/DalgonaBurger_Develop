import React from "react";
import './index.css';
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import HeaderNav from "@/components/HeaderNav";
import DistributionPage from "@/pages/distribution";
import Dashboard from "@/components/Dashboard";

const PageWrapper = ({ pageId }) => <Dashboard pageId={pageId} />;

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <HeaderNav />
      <Routes>
        <Route path="/distribution" element={<DistributionPage />} />
        {[
            "A1", "A2", "A3", "A4", "A5",
            "B1", "B2", "B3", "B4", "B5",
            "C1", "C2", "C3", "C4", "C5",
            "D1", "D2", "D3", "D4", "D5",
            "E1", "E2", "E3", "E4", "E5",
        ].map(stage => (
          <Route
            key={stage}
            path={`/dashboard/${stage}`}
            element={<PageWrapper pageId={stage} />}
          />
        ))}
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);