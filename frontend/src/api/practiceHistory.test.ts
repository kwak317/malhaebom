import { describe, expect, it, vi } from "vitest";

import { PracticeHistoryApiError, deleteAllPracticeRecords, fetchPracticeRecords, fetchPreparationChatHistory } from "./practiceHistory";

describe("fetchPracticeRecords", () => {
  it("사용자 access token으로 백엔드 기록 API만 호출한다", async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ records: [] }), { status: 200 }));

    await expect(fetchPracticeRecords("access-token", "https://api.example.com/", fetcher)).resolves.toEqual([]);

    expect(fetcher).toHaveBeenCalledWith(
      "https://api.example.com/practice-records",
      { headers: { Authorization: "Bearer access-token" } },
    );
  });

  it("저장소 오류는 내부 응답을 노출하지 않는 안전한 오류로 바꾼다", async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response("analysis-audio/user-1/private.wav", { status: 503 }));

    const result = fetchPracticeRecords("access-token", "https://api.example.com", fetcher);

    await expect(result).rejects.toThrow("연습 기록을 불러오지 못했습니다. 다시 시도해 주세요.");
    await expect(result).rejects.not.toThrow("analysis-audio");
    await expect(result).rejects.toBeInstanceOf(PracticeHistoryApiError);
  });

  it("API 주소가 없으면 기존 분석 API와 같은 로컬 백엔드를 사용한다", async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ records: [] }), { status: 200 }));

    await expect(fetchPracticeRecords("access-token", undefined, fetcher)).resolves.toEqual([]);

    expect(fetcher).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/practice-records",
      { headers: { Authorization: "Bearer access-token" } },
    );
  });
});

describe("deleteAllPracticeRecords", () => {
  it("현재 로그인 사용자의 백엔드 전체 삭제 API만 호출한다", async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));

    await expect(deleteAllPracticeRecords("access-token", "https://api.example.com/", fetcher)).resolves.toBeUndefined();

    expect(fetcher).toHaveBeenCalledWith(
      "https://api.example.com/practice-records",
      { method: "DELETE", headers: { Authorization: "Bearer access-token" } },
    );
  });
});


describe("fetchPreparationChatHistory", () => {
  it("인증된 연습 ID로 저장 대화를 조회한다", async () => {
    const messages = [{ role: "user", message: "경험 추가", follow_up_question: null }];
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ messages }), { status: 200 }));
    await expect(fetchPreparationChatHistory("session-1", "token", "https://api.example.com", fetcher)).resolves.toEqual(messages);
    expect(fetcher).toHaveBeenCalledWith("https://api.example.com/practice-records/session-1/preparation-chat", { headers: { Authorization: "Bearer token" } });
  });
  it("잘못된 대화 형식과 조회 오류를 빈 대화로 처리하지 않는다", async () => {
    for (const response of [new Response(JSON.stringify({ messages: [{ role: "system", message: "hidden", follow_up_question: null }] })), new Response("private", { status: 503 })]) {
      await expect(fetchPreparationChatHistory("session-1", "token", "https://api.example.com", vi.fn().mockResolvedValue(response))).rejects.toThrow("채팅 내역을 불러오지 못했어요.");
    }
  });
});
