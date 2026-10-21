import { useOptionalTheme } from "../theme/ThemeProvider";

export function ThemeToggle() {
  const value = useOptionalTheme();
  if (!value) return null;
  const { theme, toggleTheme } = value;
  const nextLabel = theme === "light" ? "다크 모드로 전환" : "라이트 모드로 전환";
  return <button className="theme-toggle" type="button" onClick={toggleTheme} aria-label={nextLabel} title={nextLabel}>
    <span aria-hidden="true">{theme === "light" ? "☾" : "☀"}</span><span className="sr-only">{nextLabel}</span>
  </button>;
}
