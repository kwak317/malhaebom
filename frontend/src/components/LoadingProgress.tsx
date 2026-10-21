import { useEffect, useState } from "react";

export function LoadingProgress({ stage }: { stage: string }) {
  const [steps, setSteps] = useState([stage]);
  useEffect(() => {
    setSteps((previous) => previous[previous.length - 1] === stage ? previous : [...previous.slice(-2), stage]);
  }, [stage]);
  return <div className="coach-loading-progress" aria-label="현재 작업 진행 상황">
    <span className="coach-loading-progress-label">진행 상황</span>
    {steps.slice(-3).map((step, index, visible) => {
      const current = index === visible.length - 1;
      return <div key={`${index}-${step}`} className={current ? "is-current" : "is-complete"}>
        <span className="coach-loading-progress-icon" aria-hidden="true">{current ? "" : "✓"}</span>
        <span>{step}</span>
      </div>;
    })}
  </div>;
}
