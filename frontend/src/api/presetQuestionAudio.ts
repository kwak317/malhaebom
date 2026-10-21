import { API_BASE_URL } from "../config/apiBase";

const PRESET_IDS = new Set(
  Array.from({ length: 10 }, (_, index) => `preset-${String(index + 1).padStart(2, "0")}`)
    .filter((questionId) => questionId !== "preset-04"),
);

export function getPresetQuestionAudioUrl(
  questionId: string,
  apiBase?: string,
): string | null {
  const normalizedApiBase = (apiBase === undefined ? API_BASE_URL : apiBase).replace(/\/$/, "");
  if (!PRESET_IDS.has(questionId) || (apiBase !== undefined && !normalizedApiBase)) return null;
  return `${normalizedApiBase}/api/preset-questions/${encodeURIComponent(questionId)}/audio`;
}
