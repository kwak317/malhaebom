import { useLoadingProgress } from "../api/loadingProgress";
import { LoadingProgress } from "./LoadingProgress";
import type { ReactNode } from "react";
import coachThinking from "../assets/coach-comparing.png";

export function CoachLoadingCard({ badge, title, children, className = "", label, mascot = coachThinking, progressPath, progressFallback = "요청을 준비하고 있어요…" }: {
  badge: string;
  title: string;
  children: ReactNode;
  className?: string;
  label: string;
  mascot?: string;
  progressPath?: string;
  progressFallback?: string;
}) {
  const stage = useLoadingProgress(progressPath || (label === "README 분석 중" ? "/api/github/readme/analyze" : "/api/job-search/recommendations"), progressFallback);
  return <article className={`coach-message coach-message-assistant coach-typing-message coach-analysis-loading ${className}`} role="status" aria-live="polite" aria-label={label}>
    <span className="coach-message-avatar" aria-hidden="true">✦</span>
    <div className="coach-analysis-status">
      <img className="coach-state-mascot" src={mascot} alt="작업 중인 말해봄 코치" />
      <div className="coach-analysis-copy">
        <span className="coach-analysis-badge"><span className="coach-typing-dots" aria-hidden="true"><i /><i /><i /></span>{badge}</span>
        <strong className="coach-analysis-title">{title}</strong>
        <p>{children}</p>
      </div>
      <LoadingProgress stage={stage} />
    </div>
  </article>;
}
