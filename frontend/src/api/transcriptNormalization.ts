import { progressFetch } from "./loadingProgress";
import { API_BASE_URL } from "../config/apiBase";
export type NormalizationResult = {
  transcript: string;
  edit_log: Array<{ original: string; replacement: string; edit_type: string; reason: string }>;
  confirmations: Array<{ original: string; replacement: string; reason: string; applied: boolean }>;
  meaning_preservation_check: string;
  prompt_name: string; prompt_version: number; trace_id: string;
};
export async function normalizeTranscript({ analysisJobId, transcript, accessToken }: {
  analysisJobId: string; transcript: string; accessToken: string;
}): Promise<NormalizationResult> {
  const response = await progressFetch(`${API_BASE_URL}/analysis-jobs/${encodeURIComponent(analysisJobId)}/normalize-transcript`, {
    method: "POST", headers: { Authorization: `Bearer ${accessToken}`, "Content-Type": "application/json" },
    body: JSON.stringify({ transcript }),
  });
  const payload = await response.json().catch(() => null);
  if (!response.ok) throw new Error(typeof payload?.detail === "string" ? payload.detail : "표준어로 바꾸지 못했어요. 원문은 유지됩니다.");
  if (!payload || typeof payload.transcript !== "string" || !payload.transcript.trim() || payload.transcript.length > 5000
      || !Array.isArray(payload.edit_log) || !Array.isArray(payload.confirmations)
      || typeof payload.meaning_preservation_check !== "string") {
    throw new Error("변환 결과를 확인하지 못했어요. 원문은 유지됩니다.");
  }
  return payload;
}
