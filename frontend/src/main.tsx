import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import DemoRouter from "./demoRouter";
import "./styles/detail-design.css";
import "./styles/intro-page-demo.css";
import "./styles/intro-feature-demo.css";
import "./styles/intro-flow-demo.css";
import "./styles/intro-problem-solution-demo.css";
import "./styles/intro-preview-demo.css";
import "./styles/intro-editorial-demo.css";
import "./styles/intro-interactive-demo.css";
import "./styles/intro-coachroom-demo.css";
import "./styles/intro-coachroom-hero-layout.css";
import "./styles/intro-coachroom-metrics.css";
import "./styles/intro-coachroom-value-copy.css";
import "./styles/intro-coachroom-challenges-grid.css";
import "./styles/intro-coachroom-why-section.css";
import "./styles/theme.css";
import "./styles/home-page.css";
import DesignGallery from "./pages/DesignGallery";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    {window.location.pathname === "/design" ? <DesignGallery /> : window.location.pathname.startsWith("/demo/") ? <DemoRouter /> : <App />}
  </StrictMode>,
);
