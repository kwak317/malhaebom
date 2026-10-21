import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it } from "vitest";
import { ThemeProvider } from "../theme/ThemeProvider";
import { ThemeToggle } from "./ThemeToggle";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let container: HTMLDivElement;
let root: Root;
const storage = new Map<string, string>();

beforeEach(() => { storage.clear(); Object.defineProperty(window, "localStorage", { configurable: true, value: { getItem: (key: string) => storage.get(key) ?? null, setItem: (key: string, value: string) => storage.set(key, value) } }); container = document.createElement("div"); document.body.appendChild(container); root = createRoot(container); });
afterEach(async () => { if (root) await act(async () => root.unmount()); container.remove(); });

it("현재 테마의 반대 전환 동작을 툴팁과 접근 가능한 이름으로 제공한다", async () => {
  await act(async () => root.render(<ThemeProvider><ThemeToggle /></ThemeProvider>));
  const button = container.querySelector("button")!;
  expect(button.getAttribute("aria-label")).toBe("다크 모드로 전환");
  expect(button.textContent).toContain("다크 모드로 전환");
});

it("테마 provider 없이 독립 렌더링된 헤더를 중단시키지 않는다", async () => {
  await act(async () => root.render(<ThemeToggle />));
  expect(container.textContent).toBe("");
});
