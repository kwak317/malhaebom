import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ResumeSubmissionChat } from "./ResumeSubmissionChat";
(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
const analyze = vi.fn();
vi.mock("../api/supabaseAuth", () => ({ supabase: () => ({ auth: { getSession: async () => ({ data: { session: { access_token: "test-token" } } }) } }) }));
vi.mock("../api/resume", async (original) => ({ ...await original<typeof import("../api/resume")>(), analyzeResumePdf: (...args: unknown[]) => analyze(...args) }));
let root: Root; let container: HTMLDivElement;
beforeEach(() => { container = document.createElement("div"); document.body.append(container); root = createRoot(container); container.className = "coach-thread"; });
afterEach(async () => { await act(async () => root.unmount()); container.remove(); vi.useRealTimers(); vi.clearAllMocks(); });
async function submit() {
  await act(async () => root.render(<ResumeSubmissionChat profile={null} onConfirm={vi.fn()} onSkip={vi.fn()} />));
  const input = container.querySelector('input[type="file"]') as HTMLInputElement;
  Object.defineProperty(input, "files", { value: [new File(["sample"], "sample.pdf", { type: "application/pdf" })], configurable: true });
  await act(async () => input.dispatchEvent(new Event("change", { bubbles: true })));
  await act(async () => (container.querySelector('.resume-submit-button') as HTMLButtonElement).click());
}
it("진행 이벤트와 예상 시간을 표시하고 완료 시 제거한다", async () => {
  vi.useFakeTimers(); let finish!: (v: object) => void;
  analyze.mockImplementation(() => new Promise(resolve => { finish = resolve; })); const nextStage = vi.fn(); container.addEventListener("workspace-next-stage", nextStage); await submit();
  expect(nextStage).toHaveBeenCalledOnce();
  expect(container.textContent).toContain("예상 남은 시간 약 35초");
  expect((container.querySelector('input[type="file"]') as HTMLInputElement).disabled).toBe(true);
  await act(async () => { window.dispatchEvent(new CustomEvent("coach-request-progress", { detail: { path: "/api/resume/analyze", stage: "추출 결과를 다시 확인하고 있어요…" } })); vi.advanceTimersByTime(10000); });
  expect(container.querySelector('.is-current')?.textContent).toContain("추출 결과를 다시 확인");
  expect(container.textContent).toContain("예상 남은 시간 약 25초");
  await act(async () => vi.advanceTimersByTime(30000));
  expect(container.textContent).toContain("예상보다 오래 걸리고 있어요");
  await act(async () => finish({ facts: [], model: "test" }));
  expect(container.querySelector('.resume-loading-progress')).toBeNull();
  expect(container.textContent).toContain("이력서 검토 결과");
});
it("실패 시 진행 표시를 제거하고 재검토 시간을 초기화한다", async () => {
  vi.useFakeTimers(); let reject!: (e: Error) => void;
  analyze.mockImplementationOnce(() => new Promise((_, fail) => { reject = fail; })); await submit();
  await act(async () => { vi.advanceTimersByTime(20000); reject(new Error("검토 실패")); });
  expect(container.querySelector('.resume-loading-progress')).toBeNull();
  expect(container.querySelector('[role="alert"]')?.textContent).toBe("검토 실패");
  analyze.mockImplementationOnce(() => new Promise(() => undefined));
  await act(async () => (container.querySelector('.resume-submit-button') as HTMLButtonElement).click());
  expect(container.textContent).toContain("예상 남은 시간 약 35초");
  expect(container.textContent).toContain("경과 0초");
});
