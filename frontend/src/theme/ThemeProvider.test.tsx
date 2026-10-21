import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { ThemeProvider, useTheme } from "./ThemeProvider";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let container: HTMLDivElement;
let root: Root;
const storage = new Map<string, string>();

function Probe() {
  const { theme, toggleTheme } = useTheme();
  return <button type="button" onClick={toggleTheme}>{theme}</button>;
}

beforeEach(() => {
  storage.clear();
  Object.defineProperty(window, "localStorage", { configurable: true, value: { getItem: (key: string) => storage.get(key) ?? null, setItem: (key: string, value: string) => storage.set(key, value), clear: () => storage.clear() } });
  document.documentElement.removeAttribute("data-theme");
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(async () => {
  if (root) await act(async () => root.unmount());
  container.remove();
});

describe("ThemeProvider", () => {
  it("저장된 다크 선택을 적용하고 토글 뒤에도 유지한다", async () => {
    window.localStorage.setItem("malhaebom-theme", "dark");
    await act(async () => root.render(<ThemeProvider><Probe /></ThemeProvider>));

    expect(document.documentElement.dataset.theme).toBe("dark");
    const button = container.querySelector("button")!;
    expect(button.textContent).toBe("dark");

    await act(async () => button.click());
    expect(document.documentElement.dataset.theme).toBe("light");
    expect(window.localStorage.getItem("malhaebom-theme")).toBe("light");
  });
});
