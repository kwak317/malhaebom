export type CoachAudioState = "available" | "unavailable" | "unreviewed" | "error";
export type AnalysisFeedback = {
  title: string;
  measurement: string;
  nextPractice: string;
};
export type ReferenceMetric = {
  value?: number;
  min?: number;
  max?: number;
};
export type ReferenceMetrics = {
  pace: ReferenceMetric;
  longSilenceCount: ReferenceMetric;
  repetitionCount: ReferenceMetric;
};
export type ContentFeedback = {
  text: string;
};
export type AnalysisResult = {
  attemptNo: 1 | 2;
  analysisJobId?: string;
  practiceSessionId?: string;
  transcript: string;
  answerDurationSec?: number;
  speakingRate: number;
  longSilence: number;
  repeatedExpressions: number;
  feedback: AnalysisFeedback[];
  prosodyReferenceAvailable: boolean;
  referenceMetrics: ReferenceMetrics;
  contentFeedback: ContentFeedback;
  improvedAnswer?: string;
};

// 실제 backend 응답이 아닌 화면 흐름 확인용 mock 값입니다.
export const MOCK_LOGGED_IN = true;
export const MOCK_COACH_AUDIO_STATE: CoachAudioState = "available";
// 정적 검수 WAV가 추가되면 이 값에 로컬 asset 경로를 넣습니다. 현재는 자산이 없습니다.
export const MOCK_COACH_AUDIO_SRC: string | null = null;

// 실제 평균 데이터가 아닌 화면 확인용 참고 기준 Mock입니다.
export const MOCK_ANALYSIS_REFERENCE_METRICS: ReferenceMetrics = {
  pace: { value: 320, min: 280, max: 320 },
  longSilenceCount: { value: 2.48, min: 0, max: 2.48 },
  repetitionCount: { value: 0.41, min: 0, max: 0.41 },
};

const firstMockResult: AnalysisResult = {
  attemptNo: 1,
  transcript: "안녕하세요. 저는 새로운 기술을 배우고 문제를 해결하는 과정에 흥미를 느끼는 지원자입니다. 협업을 통해 더 나은 결과를 만들어 왔습니다.",
  speakingRate: 345,
  longSilence: 3,
  repeatedExpressions: 4,
  feedback: [
    {
      title: "긴 침묵",
      measurement: "이번 답변에서는 긴 침묵이 3회 나타났어요. 참고 기준은 약 2.5회/분이에요.",
      nextPractice: "다음 답변에서는 긴 침묵을 줄여보세요.",
    },
    {
      title: "반복 표현",
      measurement: "이번 답변에서는 반복 표현이 4회 나타났어요. 참고 기준은 약 0.4회/100어절이에요.",
      nextPractice: "다음 답변에서는 반복 표현을 줄이는 것을 목표로 연습해보세요.",
    },
  ],
  prosodyReferenceAvailable: true,
  referenceMetrics: MOCK_ANALYSIS_REFERENCE_METRICS,
  contentFeedback: { text: "갈등 상황과 해결 과정은 답변에 포함되어 있어요. 여기에 본인이 맡았던 역할과 실제로 어떤 행동을 했는지 조금 더 구체적으로 넣어보세요. 마지막에 그 결과가 어떻게 달라졌는지까지 이야기하면 경험의 흐름을 더 이해하기 쉬워요." },
};

const secondMockResult: AnalysisResult = {
  attemptNo: 2,
  transcript: "안녕하세요. 저는 새로운 기술을 배우고 문제를 해결하는 과정에 흥미를 느끼는 지원자입니다. 협업 경험을 통해 성장해 왔습니다.",
  speakingRate: 330,
  longSilence: 1,
  repeatedExpressions: 2,
  feedback: [],
  prosodyReferenceAvailable: false,
  referenceMetrics: MOCK_ANALYSIS_REFERENCE_METRICS,
  contentFeedback: { text: "답변에 담긴 경험을 바탕으로 다음 내용을 더 구체화해볼 수 있어요. 질문과 연결되는 본인의 역할이나 행동을 한 가지 더 설명해보세요." },
};

export const MOCK_CONTENT_FEEDBACK_BY_QUESTION: Record<string, ContentFeedback> = {
  "지원한 이유를 말씀해주세요.": {
    text: "지원 직무에 관심을 갖게 된 이유는 답변에 잘 드러나 있어요. 여기에 본인의 경험과 지원 직무가 어떻게 연결되는지 구체적인 사례를 한 가지 더 넣어보세요. 프로젝트에서 맡았던 역할이나 그 경험을 통해 배운 점을 함께 설명하면 지원 이유를 더 구체적으로 전달할 수 있어요.",
  },
  "본인의 장점을 말씀해주세요.": {
    text: "장점 자체는 답변에 포함되어 있어요. 그 장점이 실제로 드러났던 경험이나 결과를 한 가지 함께 설명해보세요. 당시 본인이 어떤 행동을 했는지까지 덧붙이면 강점을 더 구체적으로 전달할 수 있어요.",
  },
  "협업 중 갈등을 해결했던 경험을 말씀해주세요.": {
    text: "갈등 상황과 해결 과정은 답변에 포함되어 있어요. 여기에 본인이 맡았던 역할과 실제로 어떤 행동을 했는지 조금 더 구체적으로 넣어보세요. 마지막에 그 결과가 어떻게 달라졌는지까지 이야기하면 경험의 흐름을 더 이해하기 쉬워요.",
  },
};

export function getMockAnalysisResult(attemptNo: 1 | 2): AnalysisResult {
  return attemptNo === 1 ? firstMockResult : secondMockResult;
}
