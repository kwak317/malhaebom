import { PRESET_QUESTIONS } from "./presetQuestions";

export const INTERVIEW_QUESTION_CATEGORIES = [
  {
    id: "preset",
    label: "기본 면접",
    questions: PRESET_QUESTIONS.map((question) => question.text),
  },
] as const;
