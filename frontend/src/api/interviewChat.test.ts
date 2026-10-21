import { describe, expect, it, vi } from "vitest";
import { requestInterviewChat } from "./interviewChat";
const active = { conversation_id:"c1",status:"active",message:"피드백",follow_up_question:"결과는요?",summary:null };
describe("면접 대화 API 계약", () => {
  it("사용자 문맥 없이 세션과 메시지만 인증해서 보낸다", async () => {
    const fetcher=vi.fn().mockResolvedValue(new Response(JSON.stringify(active),{ status:200 }));
    const request={ action:"message" as const,request_id:"r1",practice_session_id:"s1",conversation_id:"c1",message:"사용자 질문" };
    expect(await requestInterviewChat(request,"token","http://localhost:18000/",fetcher)).toEqual(active);
    expect(fetcher).toHaveBeenCalledWith("http://localhost:18000/api/agent/chat",expect.objectContaining({ method:"POST",body:JSON.stringify(request),headers:{ Authorization:"Bearer token","Content-Type":"application/json" } }));
  });
  it("인증 누락과 HTTP 오류를 전달한다", async () => {
    const fetcher=vi.fn();
    await expect(requestInterviewChat({action:"start",request_id:"r1",practice_session_id:"s1"},"","",fetcher)).rejects.toThrow("로그인");
    expect(fetcher).not.toHaveBeenCalled();
    fetcher.mockResolvedValue(new Response(JSON.stringify({detail:"기록 만료"}),{status:404}));
    await expect(requestInterviewChat({action:"start",request_id:"r1",practice_session_id:"s1"},"token","",fetcher)).rejects.toThrow("기록 만료");
  });
  it("종료에 요약이 없거나 꼬리질문이 있으면 거부한다", async () => {
    for (const payload of [{...active,status:"finished"},{...active,status:"finished",summary:{clarified_points:[],next_practice:["다시 연습"]}}]) {
      const fetcher=vi.fn().mockResolvedValue(new Response(JSON.stringify(payload),{status:200}));
      await expect(requestInterviewChat({action:"finish",request_id:"r1",practice_session_id:"s1",conversation_id:"c1"},"token","",fetcher)).rejects.toThrow("응답 형식");
    }
  });
});
