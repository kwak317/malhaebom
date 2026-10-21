import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import HomePage from "./HomePage";
import { NavigationProvider } from "../navigation";
import { ThemeProvider } from "../theme/ThemeProvider";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let container: HTMLDivElement;
let root: Root;
beforeEach(() => { container = document.createElement("div"); document.body.appendChild(container); root = createRoot(container); });
afterEach(async () => { await act(async () => root.unmount()); container.remove(); });

it("시작 메인의 연습과 기록 버튼이 기존 이동 callback을 호출한다", async () => {
  const onStartPractice = vi.fn(); const onViewHistory = vi.fn();
  await act(async () => root.render(
    <ThemeProvider><NavigationProvider active="practice" isLoggedIn={false} navigate={() => undefined} logout={() => undefined}>
      <HomePage onStartPractice={onStartPractice} onViewHistory={onViewHistory} />
    </NavigationProvider></ThemeProvider>,
  ));
  const buttons = Array.from(container.querySelectorAll<HTMLButtonElement>(".home-actions button"));
  await act(async () => buttons.find((button) => button.textContent?.includes("연습하기"))?.click());
  await act(async () => buttons.find((button) => button.textContent?.includes("기록 확인하기"))?.click());
  expect(onStartPractice).toHaveBeenCalledOnce();
  expect(onViewHistory).toHaveBeenCalledOnce();
});

it("질문 카드의 설명은 배경 장식과 겹치지 않는 전용 본문 영역에 표시한다", async () => {
  await act(async () => root.render(
    <ThemeProvider><NavigationProvider active="practice" isLoggedIn={false} navigate={() => undefined} logout={() => undefined}>
      <HomePage onStartPractice={vi.fn()} onViewHistory={vi.fn()} />
    </NavigationProvider></ThemeProvider>,
  ));

  const copy = container.querySelector(".home-question-copy");
  expect(copy).not.toBeNull();
  expect(copy?.textContent).toContain("기술적으로 가장 도전적이었던");
});
