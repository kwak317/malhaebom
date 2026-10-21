import { afterEach, beforeEach, expect, it, vi } from "vitest";
const mocks = vi.hoisted(() => ({ signInWithOAuth: vi.fn() }));
vi.mock("@supabase/supabase-js", () => ({ createClient: () => ({ auth: { signInWithOAuth: mocks.signInWithOAuth } }) }));
beforeEach(() => {
  vi.resetModules();
  vi.stubEnv("VITE_SUPABASE_URL", "https://auth.example.invalid");
  vi.stubEnv("VITE_SUPABASE_PUBLISHABLE_KEY", "synthetic-public-key");
  sessionStorage.clear();
  mocks.signInWithOAuth.mockResolvedValue({ error: null });
});
afterEach(() => { vi.unstubAllEnvs(); sessionStorage.clear(); });
it("연습 로그인은 복귀 의도를 저장하고 기존 허용 origin으로 OAuth를 시작한다", async () => {
  const { signInWithGoogle } = await import("./supabaseAuth");
  await signInWithGoogle("practice");
  expect(sessionStorage.getItem("malhaebom-login-destination")).toBe("practice");
  expect(mocks.signInWithOAuth).toHaveBeenCalledWith({ provider: "google", options: { redirectTo: window.location.origin } });
});
it("일반 로그인은 홈 복귀를 저장하고 provider 실패를 전달한다", async () => {
  mocks.signInWithOAuth.mockResolvedValue({ error: new Error("OAuth unavailable") });
  const { signInWithGoogle } = await import("./supabaseAuth");
  await expect(signInWithGoogle()).rejects.toThrow("OAuth unavailable");
  expect(sessionStorage.getItem("malhaebom-login-destination")).toBe("home");
});
