// @vitest-environment node
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { runInNewContext } from "node:vm";
import { expect, it, vi } from "vitest";

const script = readFileSync(resolve("public/intro/assets/auth-callback.js"), "utf8");
function callback(search: string, hash: string, stored: string | null = "practice", storageFails = false) {
  const replace = vi.fn();
  const removeItem = vi.fn();
  runInNewContext(script, {
    URLSearchParams,
    window: { location: { search, hash, replace } },
    sessionStorage: { getItem: () => { if (storageFails) throw new Error("blocked storage"); return stored; }, removeItem },
  });
  return { replace, removeItem };
}
it("인증 fragment는 같은 origin의 연습으로 전달한다", () => {
  const result = callback("", "#access_token=synthetic&refresh_token=synthetic");
  expect(result.replace).toHaveBeenCalledWith("/app/practice#access_token=synthetic&refresh_token=synthetic");
  expect(result.removeItem).toHaveBeenCalledWith("malhaebom-login-destination");
});
it("기존 서비스 홈 로그인은 홈으로 복귀한다", () => {
  expect(callback("?code=synthetic", "", "home").replace).toHaveBeenCalledWith("/app/?code=synthetic");
});
it("취소 오류는 로그인 화면으로 전달한다", () => {
  expect(callback("", "#error=access_denied", "home").replace).toHaveBeenCalledWith("/app/auth#error=access_denied");
});
it("변조한 복귀 URL과 storage 거부도 외부 주소로 이동하지 않는다", () => {
  expect(callback("?code=synthetic&next=https://example.invalid", "", "https://example.invalid").replace.mock.calls[0][0]).toMatch(/^\/app\/practice\?/);
  expect(callback("?code=synthetic", "", null, true).replace).toHaveBeenCalledWith("/app/practice?code=synthetic");
});
it("소개 페이지 앵커 이동은 인증 복귀로 오인하지 않는다", () => {
  expect(callback("", "#features").replace).not.toHaveBeenCalled();
});
