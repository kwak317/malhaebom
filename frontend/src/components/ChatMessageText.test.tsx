import { act } from "react";
import { createRoot } from "react-dom/client";
import { expect, it } from "vitest";
import { ChatMessageText } from "./ChatMessageText";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
it("핵심 구절을 강조해도 원문 링크와 문장부호를 유지하고 HTML은 실행하지 않는다", async () => {
  const container = document.createElement("div"); const root = createRoot(container);
  await act(async () => root.render(<ChatMessageText text={'**원문 확인**: https://example.com/jobs/1. <img src=x onerror=alert(1)>'} />));
  expect(container.querySelector("strong")?.textContent).toBe("원문 확인");
  expect(container.querySelector("a")?.getAttribute("href")).toBe("https://example.com/jobs/1");
  expect(container.textContent).toContain('https://example.com/jobs/1.');
  expect(container.querySelector("img")).toBeNull();
  expect(container.textContent).toContain('<img src=x onerror=alert(1)>');
  await act(async () => root.render(<ChatMessageText text="**" />));
  expect(container.textContent).toBe("**");
  expect(container.querySelector("strong")).toBeNull();
  await act(async () => root.unmount());
});
