import { Fragment, type ChangeEvent, type FormEvent, useEffect, useMemo, useRef, useState } from "react";
import "../styles/practice-page.css";
import { AppHeader } from "../navigation";
import { MOCK_ERROR_STATE } from "../mocks/errorStateMock";
import { INTERVIEW_QUESTION_CATEGORIES } from "../catalog/interviewQuestions";
import { supabase } from "../api/supabaseAuth";
import { useCoachThreadAutoScroll } from "../hooks/useCoachThreadAutoScroll";
import { AnswerAnalysisChat } from "./AnalysisPage";
import type { AnalysisResult } from "../mocks/analysisMock";
import { CoachingChatMessages } from "./ResultPage";
import { WorkspaceHistory, WorkspaceLibrary, usePracticeWorkspace, workspaceId } from "../components/PracticeWorkspace";
import "../styles/practice-workspace.css";
import { InlineAttemptComparisonChat } from "../components/InlineAttemptComparisonChat";
import { PreparationConversationChat, usePreparationConversation, type PreparationChatPlacement } from "../components/PreparationConversationChat";
import type { PreparationStage, PracticeRestart, RestartTarget } from "../api/preparationConversation";
import { ResumeSubmissionChat } from "../components/ResumeSubmissionChat";
import { PracticeChatHistory, capturePracticeChat, type PracticeChatHistoryMessage } from "../components/PracticeChatHistory";
import coachRecording from "../assets/coach-recording.png";
import { CoachLoadingCard } from "../components/CoachLoadingCard";
import type { ResumeProfile } from "../api/resume";
import {
  createPracticeSession,
  analyzeGithubReadme,
  analyzeRecommendedJob,
  recommendSaraminJobs,
  getNcsBackendCompetencies,
  listJobPostings,
  analyzeAlioRecruitment,
  analyzeMofeRecruitment,
  analyzePublicEmploymentRecruitment,
  interpretJobSearchMessage,
  searchAlioRecruitments,
  searchMofeRecruitments,
  searchPublicEmploymentRecruitments,
  type AlioRecruitment,
  type JobPosting,
  type GithubReadmeAnalysis,
  type MofeRecruitment,
  type NcsBackendCompetencies,
  type PublicEmploymentRecruitment,
  type SaraminRecommendation,
} from "../api/practiceSetup";

export { PRESET_QUESTIONS } from "../catalog/presetQuestions";

type QuestionType = "preset" | "custom";
type MicrophoneState = "idle" | "checking" | "granted" | "denied" | "error";
type PracticeView = "job-select" | "question-select";
type ChatAssistantMessagePlacement = "before-results" | "after-results";
type InlineRecordingState = "ready" | "preparing" | "recording" | "completed" | "error";
type PendingWav = { file: File; question: PracticeQuestion; url: string | null };
type ActiveAnswerAnalysis = {
  question: PracticeQuestion;
  audio: Blob;
  attemptNo: 1 | 2;
  practiceSessionId?: string;
  contextEvidenceIds: string[];
};
type CompletedAnswerAnalysis = ActiveAnswerAnalysis & { result: AnalysisResult };

export type PracticeQuestion = {
  questionType: QuestionType;
  question: string;
  questionId: string | null;
  practiceSessionId?: string;
  jobPostingId?: string;
  requirementIds?: string[];
};

type PracticePageProps = {
  onAnalysisReady?: (question: PracticeQuestion, audio: Blob, attemptNo?: 1 | 2) => void;
  onAnalysisComplete?: (question: PracticeQuestion, result: AnalysisResult) => void;
  isLoggedIn: boolean;
  onLogin: () => void;
  resumeQuestion?: PracticeQuestion;
  resumeAttemptNo?: 1 | 2;
};

const WAV_MIME_TYPES = new Set(["audio/wav", "audio/x-wav", "audio/wave", "audio/vnd.wave"]);
const RECORDING_MIME_TYPES = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg;codecs=opus"];
const MIN_RECORDING_MS = 5_000;
const MAX_RECORDING_MS = 60_000;
const NCS_CATEGORY_LABELS = [
  { id: "knowledge", label: "지식" },
  { id: "skill", label: "기술" },
  { id: "attitude", label: "태도" },
] as const;

function githubReadmeUrl(value: string): string | null {
  try {
    const url = new URL(value.trim());
    const parts = url.pathname.split("/").filter(Boolean);
    const isRepository = parts.length === 2;
    const isReadmeFile = parts.length >= 5
      && parts[2] === "blob"
      && /^README\.md$/i.test(parts[parts.length - 1]);
    if (url.protocol !== "https:"
      || (url.hostname !== "github.com" && url.hostname !== "www.github.com")
      || url.username || url.password || url.port
      || !parts[0] || !parts[1]
      || (!isRepository && !isReadmeFile)) return null;
    return url.toString();
  } catch {
    return null;
  }
}

function isWavFile(file: File): boolean {
  return file.name.toLowerCase().endsWith(".wav") || WAV_MIME_TYPES.has(file.type.toLowerCase());
}

function formatRecordingTime(milliseconds: number) {
  const seconds = Math.floor(milliseconds / 1000);
  return `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
}

function createAudioUrl(audio: Blob): string | null {
  return typeof URL.createObjectURL === "function" ? URL.createObjectURL(audio) : null;
}

function jobOriginLabel(job: JobPosting): string {
  if (job.data_origin === "alio") return "ALIO 공공기관 채용";
  if (job.data_origin === "public_job") return "인사혁신처 공공취업정보";
  if (job.data_origin === "mofe_job") return "재정경제부 공공기관 채용정보";
  if (job.data_origin === "private_job") return "민간 채용 공고";
  if (job.data_origin === "demo") return "연습용 가상 공고";
  return "검토 완료 공고";
}

function technicalPriority(text: string): number {
  return /spring|react|vite|next\.?js|django|fastapi|express|mysql|postgres|redis|mongodb|sql|database|security|oauth|jwt|docker|kubernetes|rest|아키텍처|인증|데이터베이스|프레임워크/i.test(text) ? 2 : /api|연동/i.test(text) ? 1 : 0;
}

const JOB_SOURCES = [
  { name: "사람인", domain: "saramin.co.kr" },
  { name: "잡코리아", domain: "jobkorea.co.kr" },
  { name: "랠릿", domain: "rallit.com" },
  { name: "원티드", domain: "wanted.co.kr" },
  { name: "점핏", domain: "jumpit.saramin.co.kr" },
];

function jobsForSource(jobs: SaraminRecommendation[], domain: string): SaraminRecommendation[] {
  return jobs.filter((job) => {
    const hostname = new URL(job.source_url).hostname;
    return (hostname === domain || hostname.endsWith(`.${domain}`))
      && !(domain === "saramin.co.kr" && hostname.endsWith("jumpit.saramin.co.kr"));
  }).slice(0, 5);
}

function recommendationReason(job: SaraminRecommendation, hasReadmeAnalysis: boolean): string {
  const readmeMatch = job.matched_technologies[0] ?? job.matched_project_flows[0];
  const reasons = [];
  const resumeMatch = job.matched_resume_technologies?.[0] ?? job.matched_resume_project_flows?.[0];
  if (job.matched_chat_experience?.length) reasons.push(`채팅에서 확인한 경험: ${job.matched_chat_experience.join(", ")}`);
  if (resumeMatch) reasons.push(`이력서 확인 정보: ${resumeMatch}`);
  if (readmeMatch) reasons.push(`README: ${readmeMatch}`);
  else if (hasReadmeAnalysis) reasons.push("README 일치 근거 없음");
  if (job.matched_ncs_labels.length > 0) reasons.push(`NCS: ${job.matched_ncs_labels[0]}`);
  return reasons.join(" · ");
}

export function isReanswerCommand(message: string): boolean {
  return /^(?:재답변\s*(?:하기|할게요|할래요|하겠습니다|해\s*(?:줘|주세요))?|다시\s*(?:답(?:변)?|녹음|연습)(?:하기|할게요|할래요|하겠습니다|해\s*(?:줘|주세요))?|다음(?:\s*단계)?(?:으로|로)?)(?:[.!。]*)$/.test(message.trim());
}

function PracticePage({ onAnalysisReady, onAnalysisComplete, isLoggedIn, onLogin, resumeQuestion, resumeAttemptNo = 1 }: PracticePageProps) {
  const isRerecord = Boolean(resumeQuestion && resumeAttemptNo === 2);
  const [retryQuestion, setRetryQuestion] = useState<PracticeQuestion | null>(resumeQuestion ?? null);
  const isResumeRerecord = Boolean(isRerecord && retryQuestion);
  const [activeAnswerAnalysis, setActiveAnswerAnalysis] = useState<ActiveAnswerAnalysis | null>(null);
  const [completedAnswerAnalyses, setCompletedAnswerAnalyses] = useState<CompletedAnswerAnalysis[]>([]);
  const [inlineComparisonRequested, setInlineComparisonRequested] = useState(false);
  const [coachingReadyAttempts, setCoachingReadyAttempts] = useState<Set<1 | 2>>(() => new Set());
  const [retryRecordingOpen, setRetryRecordingOpen] = useState(isRerecord);
  const isInlineRerecord = Boolean(retryQuestion && (isRerecord || retryRecordingOpen));
  const [view, setView] = useState<PracticeView>(() => isRerecord ? "question-select" : "job-select");
  const [jobPostings, setJobPostings] = useState<JobPosting[]>([]);
  const [jobLoading, setJobLoading] = useState(false);
  const [jobError, setJobError] = useState("");
  const [alioQuery, setAlioQuery] = useState("");
  const [alioResults, setAlioResults] = useState<AlioRecruitment[]>([]);
  const [alioTotalCount, setAlioTotalCount] = useState(0);
  const [alioLoading, setAlioLoading] = useState(false);
  const [alioError, setAlioError] = useState("");
  const [hasSearchedAlio, setHasSearchedAlio] = useState(false);
  const [analyzingAnnouncementId, setAnalyzingAnnouncementId] = useState<number | null>(null);
  const [publicEmploymentResults, setPublicEmploymentResults] = useState<PublicEmploymentRecruitment[]>([]);
  const [publicEmploymentTotalCount, setPublicEmploymentTotalCount] = useState(0);
  const [publicEmploymentLoading, setPublicEmploymentLoading] = useState(false);
  const [publicEmploymentError, setPublicEmploymentError] = useState("");
  const [hasSearchedPublicEmployment, setHasSearchedPublicEmployment] = useState(false);
  const [analyzingPublicEmploymentAnnouncementId, setAnalyzingPublicEmploymentAnnouncementId] = useState<number | null>(null);
  const [mofeResults, setMofeResults] = useState<MofeRecruitment[]>([]);
  const [mofeTotalCount, setMofeTotalCount] = useState(0);
  const [mofeLoading, setMofeLoading] = useState(false);
  const [mofeError, setMofeError] = useState("");
  const [hasSearchedMofe, setHasSearchedMofe] = useState(false);
  const [analyzingMofeAnnouncementId, setAnalyzingMofeAnnouncementId] = useState<number | null>(null);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [selectedRequirementIds, setSelectedRequirementIds] = useState<string[]>([]);
  const [setupError, setSetupError] = useState("");
  const [questionType, setQuestionType] = useState<QuestionType>("preset");
  const [questionTypeChosen, setQuestionTypeChosen] = useState(false);
  const [selectedCategoryId, setSelectedCategoryId] = useState<string>(
    INTERVIEW_QUESTION_CATEGORIES[0].id,
  );
  const [selectedQuestion, setSelectedQuestion] = useState<number | null>(null);
  const [customQuestion, setCustomQuestion] = useState("");
  const [microphoneState, setMicrophoneState] =
    useState<MicrophoneState>("idle");
  const [chatInput, setChatInput] = useState("");
  const [chatMessages, setChatMessages] = useState<string[]>([]);
  const [ncsCompetencies, setNcsCompetencies] = useState<NcsBackendCompetencies | null>(null);
  const [ncsLoading, setNcsLoading] = useState(false);
  const [ncsError, setNcsError] = useState("");
  const [ncsRetryCount, setNcsRetryCount] = useState(0);
  const preparationSelectionFingerprint = useRef("");
  const [selectedNcsIds, setSelectedNcsIds] = useState<string[]>([]);
  const [submittedNcsIds, setSubmittedNcsIds] = useState<string[] | null>(null);
  const [resumeSourceFile, setResumeSourceFile] = useState<File | null>(null);
  const [resumeProfile, setResumeProfile] = useState<ResumeProfile | null>(null);
  useEffect(() => { if (!resumeProfile) setResumeSourceFile(null); }, [resumeProfile]);
  const [resumeSkipped, setResumeSkipped] = useState(false);
  const [resumeStepOpened, setResumeStepOpened] = useState(false);
  const [readmeStepOpened, setReadmeStepOpened] = useState(false);
  const [jobSearchStarted, setJobSearchStarted] = useState(false);
  const [readmeUrlInput, setReadmeUrlInput] = useState("");
  const [readmeUrlError, setReadmeUrlError] = useState("");
  const [submittedReadmeUrl, setSubmittedReadmeUrl] = useState<string | null>(null);
  const [readmeSkipped, setReadmeSkipped] = useState(false);
  const [readmeAnalysis, setReadmeAnalysis] = useState<GithubReadmeAnalysis | null>(null);
  const [readmeAnalysisLoading, setReadmeAnalysisLoading] = useState(false);
  const [readmeAnalysisError, setReadmeAnalysisError] = useState("");
  const readmeRequestIdRef = useRef(0);
  const [restartStage, setRestartStage] = useState<RestartTarget | null>(null);
  const [newGraduateOnly, setNewGraduateOnly] = useState(false);
  const showPreparationStage = (stage: RestartTarget) => !restartStage || ["ncs", "resume", "readme", "jobs", "questions"].indexOf(stage) >= ["ncs", "resume", "readme", "jobs", "questions"].indexOf(restartStage);
  const [saraminRecommendations, setSaraminRecommendations] = useState<SaraminRecommendation[]>([]);
  const [activeJobSource, setActiveJobSource] = useState(JOB_SOURCES[0].domain);
  const sourceJobGroups = JOB_SOURCES.map((source) => ({
    ...source, jobs: jobsForSource(newGraduateOnly ? saraminRecommendations.filter((job) => /신입|경력\s*무관/.test(job.experience) && !/신입\s*제외/.test(job.experience)) : saraminRecommendations, source.domain),
  }));
  const [saraminLoading, setSaraminLoading] = useState(false);
  const [saraminError, setSaraminError] = useState("");
  const [saraminSearched, setSaraminSearched] = useState(false);
  const [saraminRetryCount, setSaraminRetryCount] = useState(0);
  const [analyzingRecommendedUrl, setAnalyzingRecommendedUrl] = useState<string | null>(null);
  const [recommendedReviewError, setRecommendedReviewError] = useState("");
  const [chatSearchRequested, setChatSearchRequested] = useState(false);
  const [chatAssistantMessage, setChatAssistantMessage] = useState("");
  const [chatAssistantMessagePlacement, setChatAssistantMessagePlacement] =
    useState<ChatAssistantMessagePlacement>("before-results");
  const [chatIntentLoading, setChatIntentLoading] = useState(false);
  const [recordingPromptError, setRecordingPromptError] = useState("");
  const [wavUploadPending, setWavUploadPending] = useState(false);
  const [pendingWav, setPendingWav] = useState<PendingWav | null>(null);
  const [inlineRecordingActive, setInlineRecordingActive] = useState(false);
  const preparation = usePreparationConversation(isLoggedIn, resumeQuestion?.practiceSessionId || "");
  const wavUploadInputRef = useRef<HTMLInputElement | null>(null);
  const practiceGenerationRef = useRef(0);
  const practiceGeneration = practiceGenerationRef.current;
  const [jobSelectionRestart, setJobSelectionRestart] = useState(0);
  const coachThreadRef = useCoachThreadAutoScroll();
  const [chatHistory, setChatHistory] = useState<PracticeChatHistoryMessage[]>([]);
  const workspace = usePracticeWorkspace(coachThreadRef);

  useEffect(() => setChatHistory([]), [isLoggedIn, resumeQuestion?.practiceSessionId]);

  useEffect(() => { if (!isLoggedIn) workspace.reset(); }, [isLoggedIn, workspace.reset]);

  useEffect(() => {
    if (retryRecordingOpen) workspace.latest();
  }, [retryRecordingOpen, workspace.latest]);

  useEffect(() => {
    if (view === "question-select" && questionTypeChosen) workspace.latest();
  }, [view, questionType, questionTypeChosen, workspace.latest]);

  useEffect(() => () => {
    if (pendingWav?.url) URL.revokeObjectURL(pendingWav.url);
  }, [pendingWav?.url]);

  useEffect(() => {
    if (!isLoggedIn) {
      setJobPostings([]);
      setSelectedJobId(null);
      setSelectedRequirementIds([]);
      setAlioResults([]);
      setAlioTotalCount(0);
      setAlioError("");
      setHasSearchedAlio(false);
      setAnalyzingAnnouncementId(null);
      setPublicEmploymentResults([]);
      setPublicEmploymentTotalCount(0);
      setPublicEmploymentError("");
      setHasSearchedPublicEmployment(false);
      setAnalyzingPublicEmploymentAnnouncementId(null);
      setMofeResults([]);
      setMofeTotalCount(0);
      setMofeError("");
      setHasSearchedMofe(false);
      setAnalyzingMofeAnnouncementId(null);
      setChatMessages([]);
      setChatSearchRequested(false);
      setChatAssistantMessage("");
      setChatAssistantMessagePlacement("before-results");
      setChatIntentLoading(false);
      setQuestionTypeChosen(false);
      setRecordingPromptError("");
      setWavUploadPending(false);
      setPendingWav(null);
      return undefined;
    }
    if (isResumeRerecord) return undefined;
    let active = true;
    setJobLoading(true);
    setJobError("");
    void supabase().auth.getSession().then(async ({ data }) => {
      if (!data.session) throw new Error("로그인이 필요하거나 세션이 만료되었습니다.");
      return listJobPostings({ accessToken: data.session.access_token });
    }).then((postings) => {
      if (!active) return;
      setJobPostings(postings);
      if (postings.length === 0) setJobError("현재 선택할 수 있는 검토 공고가 없습니다.");
    }).catch((error) => {
      if (active) setJobError(error instanceof Error ? error.message : "공고를 불러오지 못했습니다.");
    }).finally(() => {
      if (active) setJobLoading(false);
    });
    return () => { active = false; };
  }, [isLoggedIn, isResumeRerecord]);

  useEffect(() => {
    if (!isLoggedIn || isResumeRerecord) {
      setNcsCompetencies(null);
      setNcsError("");
      setNcsRetryCount(0);
      setSelectedNcsIds([]);
      setSubmittedNcsIds(null);
      setResumeProfile(null);
      setResumeSkipped(false);
      setResumeStepOpened(false);
      setReadmeStepOpened(false);
      setJobSearchStarted(false);
      setReadmeUrlInput("");
      setReadmeUrlError("");
      setSubmittedReadmeUrl(null);
      setReadmeSkipped(false);
      setReadmeAnalysis(null);
      setReadmeAnalysisLoading(false);
      setReadmeAnalysisError("");
      setSaraminRecommendations([]);
      setSaraminLoading(false);
      setSaraminError("");
      setSaraminSearched(false);
      setAnalyzingRecommendedUrl(null);
      setRecommendedReviewError("");
      readmeRequestIdRef.current += 1;
      return undefined;
    }
    let active = true;
    setNcsLoading(true);
    setNcsError("");
    void supabase().auth.getSession().then(({ data }) => {
      if (!data.session) throw new Error("로그인이 필요하거나 세션이 만료되었습니다.");
      return getNcsBackendCompetencies({ accessToken: data.session.access_token, source: ncsRetryCount > 0 ? "database" : "api" });
    }).then((result) => {
      if (active) setNcsCompetencies(result);
    }).catch(() => {
      if (active) setNcsError(ncsRetryCount > 0 ? "저장된 NCS 목록을 불러오지 못했어요. 다시 시도해 주세요." : "NCS 실시간 조회에 실패했어요. 다시 시도를 누르면 저장된 목록을 불러옵니다.");
    }).finally(() => {
      if (active) setNcsLoading(false);
    });
    return () => { active = false; };
  }, [isLoggedIn, isResumeRerecord, ncsRetryCount]);

  useEffect(() => {
    if (!isLoggedIn || isResumeRerecord || !submittedNcsIds || (!resumeProfile && !resumeSkipped)
        || !jobSearchStarted || (!readmeAnalysis && !readmeSkipped)) return undefined;
    let active = true;
    setSaraminLoading(true);
    setSaraminError("");
    setSaraminSearched(false);
    setRecommendedReviewError("");
    void supabase().auth.getSession().then(({ data }) => {
      if (!data.session) throw new Error("로그인이 필요하거나 세션이 만료되었습니다.");
      return recommendSaraminJobs({
        accessToken: data.session.access_token,
        selectedNcsIds: submittedNcsIds,
        readmeAnalysis,
        resumeProfile,
        ...(preparation.getConversationId() ? { preparationConversationId: preparation.getConversationId() } : {}),
      });
    }).then((recommendations) => {
      if (!active) return;
      setSaraminRecommendations(recommendations);
      setActiveJobSource(JOB_SOURCES.find((source) => jobsForSource(recommendations, source.domain).length > 0)?.domain ?? JOB_SOURCES[0].domain);
      setSaraminSearched(true);
    }).catch((error) => {
      if (!active) return;
      setSaraminRecommendations([]);
      setSaraminError(error instanceof Error ? error.message : "공고 검색에 실패했어요.");
    }).finally(() => { if (active) setSaraminLoading(false); });
    return () => { active = false; };
  }, [isLoggedIn, isResumeRerecord, submittedNcsIds, resumeProfile, resumeSkipped, readmeAnalysis, readmeSkipped, jobSearchStarted, saraminRetryCount, newGraduateOnly]);

  useEffect(() => {
    if (!submittedReadmeUrl && !readmeSkipped) return;
    const thread = coachThreadRef.current;
    if (!thread || thread.dataset.historyBrowsing) return;
    if (typeof thread.scrollTo === "function") {
      thread.scrollTo({ top: thread.scrollHeight, behavior: "smooth" });
    } else {
      thread.scrollTop = thread.scrollHeight;
    }
  }, [submittedReadmeUrl, readmeSkipped, coachThreadRef]);

  useEffect(() => {
    if (!saraminSearched && !saraminError) return;
    const thread = coachThreadRef.current;
    const message = thread?.querySelector<HTMLElement>(".coach-job-search-message");
    if (!thread || !message || thread.dataset.historyBrowsing) return;
    const top = thread.scrollTop + message.getBoundingClientRect().top
      - thread.getBoundingClientRect().top - 24;
    if (typeof thread.scrollTo === "function") {
      thread.scrollTo({ top, behavior: "smooth" });
    } else {
      thread.scrollTop = top;
    }
  }, [saraminSearched, saraminError, coachThreadRef]);

  const customError = useMemo(() => {
    if (questionType !== "custom" || customQuestion.length === 0) return "";
    if (customQuestion.trim().length === 0) return "질문을 입력해 주세요.";
    if (customQuestion.length > 200) return "질문은 200자 이내로 입력해 주세요.";
    return "";
  }, [customQuestion, questionType]);

  const selectedCategory =
    INTERVIEW_QUESTION_CATEGORIES.find(
      (category) => category.id === selectedCategoryId,
    ) ?? INTERVIEW_QUESTION_CATEGORIES[0];

  const selectedJob = jobPostings.find((posting) => posting.id === selectedJobId) ?? null;
  const isRecruitmentSearchLoading = alioLoading || publicEmploymentLoading || mofeLoading;
  const isChatRequestLoading = isRecruitmentSearchLoading || chatIntentLoading;
  const isAnalyzingRecruitment = analyzingAnnouncementId !== null
    || analyzingPublicEmploymentAnnouncementId !== null
    || analyzingMofeAnnouncementId !== null;
  const canContinueToQuestion = Boolean(
    selectedJob && selectedRequirementIds.length >= 1 && selectedRequirementIds.length <= 2,
  );

  const selectedText =
    questionType === "preset" && selectedQuestion !== null
      ? selectedCategory.questions[selectedQuestion]
      : customQuestion.trim();

  const isCustomValid =
    questionType === "custom" &&
    customQuestion.trim().length >= 1 &&
    customQuestion.length <= 200;

  const canStart =
    (questionType === "preset" && selectedQuestion !== null) || isCustomValid;

  const selectedRequirements = selectedJob?.requirements.filter((requirement) =>
    selectedRequirementIds.includes(requirement.id),
  ) ?? [];

  const hasCompletedAttempt = (attemptNo: 1 | 2) =>
    completedAnswerAnalyses.some((completed) => completed.attemptNo === attemptNo);
  const hasCompletedSecondAnswer = hasCompletedAttempt(2);
  const isSecondAnswerInProgress = !hasCompletedSecondAnswer
    && (retryRecordingOpen || activeAnswerAnalysis?.attemptNo === 2);
  const canStartSecondRecording =
    coachingReadyAttempts.has(1) &&
    hasCompletedAttempt(1) &&
    !hasCompletedSecondAnswer &&
    !activeAnswerAnalysis &&
    !preparation.loading &&
    !retryRecordingOpen;
  const canStartComparison =
    coachingReadyAttempts.has(2) &&
    hasCompletedAttempt(1) &&
    hasCompletedAttempt(2) &&
    !activeAnswerAnalysis;

  const selectedPracticeQuestion = isInlineRerecord && retryQuestion
    ? retryQuestion.question
    : view === "question-select" && questionTypeChosen && canStart
      ? selectedText
      : null;

  const currentPracticeStep = retryRecordingOpen
    ? 3
    : activeAnswerAnalysis || completedAnswerAnalyses.length > 0
      ? 4
      : selectedPracticeQuestion
        ? 3
        : canContinueToQuestion
          ? 2
          : 1;

  const secondRecordingClassName = hasCompletedSecondAnswer
    ? "is-complete"
    : isSecondAnswerInProgress
      ? "is-current"
      : canStartSecondRecording
        ? "is-available"
        : "";
  const secondRecordingHint = hasCompletedSecondAnswer
    ? "2차 답변 녹음 완료"
    : isSecondAnswerInProgress
      ? "2차 답변을 녹음하고 있어요"
      : "1차 코칭 후 다시 답하기";
  const secondRecordingTitle = hasCompletedSecondAnswer
    ? "2차 답변 녹음을 완료했어요."
    : isSecondAnswerInProgress
      ? "2차 답변을 녹음하고 있어요."
      : canStartSecondRecording
        ? "같은 질문에 다시 답하기"
        : "1차 코칭을 완료하면 이용할 수 있어요.";

  const selectedQuestionInfo: PracticeQuestion = {
    questionType,
    question: selectedText,
    questionId:
      questionType === "preset" && selectedQuestion !== null
        ? `${selectedCategory.id}-${String(selectedQuestion + 1).padStart(2, "0")}`
        : null,
  };

  const changeQuestionType = (type: QuestionType) => {
    setQuestionType(type);
    setQuestionTypeChosen(true);
    setSelectedQuestion(null);
    setCustomQuestion("");
    setMicrophoneState("idle");
    setSetupError("");
    setRecordingPromptError("");
  };

  const changeCategory = (categoryId: string) => {
    setSelectedCategoryId(categoryId);
    setSelectedQuestion(null);
  };

  const openQuestionSelect = () => {
    if (!canContinueToQuestion) return;
    setView("question-select");
    setQuestionTypeChosen(false);
    setMicrophoneState("idle");
    setRecordingPromptError("");
  };

  const returnToJobSelect = () => {
    setView("job-select");
    setQuestionTypeChosen(false);
    setMicrophoneState("idle");
    setSetupError("");
    setRecordingPromptError("");
  };

  const applyRestart = (restart: PracticeRestart, message: string) => {
    const previousMessages = capturePracticeChat(coachThreadRef.current);
    setChatHistory((current) => [...current, ...previousMessages, { speaker: "assistant", text: message }]);
    practiceGenerationRef.current += 1;
    setRestartStage(restart.target);
    setNewGraduateOnly(restart.new_graduate_only);
    readmeRequestIdRef.current += 1;
    setSelectedNcsIds(restart.materials.selected_ncs_ids || []);
    setSubmittedNcsIds(restart.target === "ncs" ? null : restart.materials.selected_ncs_ids || []);
    setResumeProfile(restart.materials.resume_profile || null);
    setResumeSkipped(!["ncs", "resume"].includes(restart.target) && !restart.materials.resume_profile);
    setResumeStepOpened(restart.target !== "ncs");
    setReadmeStepOpened(["readme", "jobs", "questions"].includes(restart.target));
    setReadmeAnalysis(restart.materials.readme_analysis || null);
    setSubmittedReadmeUrl(restart.materials.readme_analysis?.source_url || null);
    setReadmeSkipped(["jobs", "questions"].includes(restart.target) && !restart.materials.readme_analysis);
    setReadmeUrlInput(""); setReadmeUrlError(""); setReadmeAnalysisError(""); setReadmeAnalysisLoading(false);
    setJobSearchStarted(["jobs", "questions"].includes(restart.target));
    setSaraminRecommendations([]); setSaraminLoading(false); setSaraminError(""); setSaraminSearched(false);
    setSaraminRetryCount((value) => value + 1);
    setAlioResults([]); setPublicEmploymentResults([]); setMofeResults([]);
    setAlioLoading(false); setPublicEmploymentLoading(false); setMofeLoading(false);
    setAnalyzingAnnouncementId(null); setAnalyzingPublicEmploymentAnnouncementId(null); setAnalyzingMofeAnnouncementId(null);
    setHasSearchedAlio(false); setHasSearchedPublicEmployment(false); setHasSearchedMofe(false);
    setSelectedJobId(restart.selection.job_posting_id);
    setSelectedRequirementIds(restart.selection.requirement_ids);
    setView(restart.target === "questions" ? "question-select" : "job-select");
    setQuestionType("preset");
    setQuestionTypeChosen(false);
    setSelectedCategoryId(INTERVIEW_QUESTION_CATEGORIES[0].id);
    setSelectedQuestion(null);
    setCustomQuestion("");
    setMicrophoneState("idle");
    setSetupError("");
    setRecordingPromptError("");
    setJobError("");
    setRecommendedReviewError("");
    setAnalyzingRecommendedUrl(null);
    setChatInput("");
    setChatMessages([]);
    setChatAssistantMessage("");
    setChatAssistantMessagePlacement("before-results");
    setChatSearchRequested(false);
    setChatIntentLoading(false);
    setActiveAnswerAnalysis(null);
    setCompletedAnswerAnalyses([]);
    setInlineComparisonRequested(false);
    setCoachingReadyAttempts(new Set());
    setRetryQuestion(null);
    setRetryRecordingOpen(false);
    setInlineRecordingActive(false);
    setPendingWav(null);
    setWavUploadPending(false);
    workspace.keepPreparation(restart.target);
    const thread = coachThreadRef.current;
    if (thread) {
      thread.dataset.historyBrowsing = "true";
      thread.dispatchEvent(new Event("workspace-browse"));
    }
    setJobSelectionRestart((value) => value + 1);
  };

  useEffect(() => {
    if (!jobSelectionRestart) return;
    const thread = coachThreadRef.current;
    const selector = restartStage === "ncs" ? ".coach-ncs-message" : restartStage === "resume" ? ".coach-resume-message"
      : restartStage === "readme" ? ".coach-readme-message" : restartStage === "questions" ? ".coach-question-message" : ".coach-job-search-message";
    const message = thread?.querySelector<HTMLElement>(selector);
    if (!thread || !message) return;
    const top = Math.max(0, thread.scrollTop + message.getBoundingClientRect().top - thread.getBoundingClientRect().top - 24);
    if (typeof thread.scrollTo === "function") thread.scrollTo({ top, behavior: "smooth" });
    else thread.scrollTop = top;
  }, [jobSelectionRestart, restartStage, coachThreadRef]);

  useEffect(() => {
    if (!selectedJobId) return;
    workspace.latest();
  }, [selectedJobId, workspace.latest]);

  useEffect(() => {
    if (view !== "question-select" || questionType !== "preset" || selectedQuestion === null) return;
    workspace.latest();
  }, [view, questionType, selectedQuestion, workspace.latest]);

  const chooseJob = (jobId: string) => {
    workspace.latest();
    if (selectedJobId && selectedJobId !== jobId) preparation.clear();
    setSelectedJobId(jobId);
    setSelectedRequirementIds([]);
    setJobError("");
  };

  const toggleRequirement = (requirementId: string) => {
    setSelectedRequirementIds((current) => {
      if (current.includes(requirementId)) {
        return current.filter((id) => id !== requirementId);
      }
      if (current.length >= 2) return current;
      return [...current, requirementId];
    });
  };

  const requestAlioSearch = async (query: string, fromChat = false) => {

    const generation = practiceGenerationRef.current;    const normalizedQuery = query.trim();
    if (!normalizedQuery || normalizedQuery.length > 80 || alioLoading) return;

    setAlioLoading(true);
    setAlioError("");
    setHasSearchedAlio(false);
    if (fromChat) {
      setChatSearchRequested(true);
      setChatAssistantMessage("");
      setChatAssistantMessagePlacement("before-results");
    }
    try {
      const { data } = await supabase().auth.getSession();
      if (!data.session) throw new Error("로그인이 필요하거나 세션이 만료되었습니다.");
      const { recruitments, totalCount } = await searchAlioRecruitments({
        accessToken: data.session.access_token,
        query: normalizedQuery,
      });
      if (generation !== practiceGenerationRef.current) return;
      setAlioResults(recruitments);
      setAlioTotalCount(totalCount);
      setHasSearchedAlio(true);
      if (fromChat) {
        setChatAssistantMessagePlacement("before-results");
        setChatAssistantMessage(
          recruitments.length > 0
            ? `ALIO에서 “${normalizedQuery}” 관련 진행 공고를 찾았어요. 원문 분석할 공고를 골라주세요.`
            : `ALIO에서 “${normalizedQuery}” 관련 진행 공고를 찾지 못했어요. 다른 키워드로 다시 물어봐 주세요.`,
        );
      }
    } catch (error) {
      if (generation !== practiceGenerationRef.current) return;
      if (generation !== practiceGenerationRef.current) return;
      setAlioResults([]);
      setAlioTotalCount(0);
      const message = error instanceof Error ? error.message : "ALIO 공고를 검색하지 못했습니다.";
      setAlioError(message);
      if (fromChat) {
        setChatAssistantMessagePlacement("before-results");
        setChatAssistantMessage(message);
      }
    } finally {
      if (generation !== practiceGenerationRef.current) return;
      setAlioLoading(false);
    }
  };

  const handleAlioSearch = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void requestAlioSearch(alioQuery);
  };

  const requestChatRecruitmentSearch = async (query: string) => {

    const generation = practiceGenerationRef.current;    const normalizedQuery = query.trim();
    if (!normalizedQuery || normalizedQuery.length > 80 || isRecruitmentSearchLoading) return;

    setChatSearchRequested(true);
    if (jobSearchStarted && submittedNcsIds && (resumeProfile || resumeSkipped) && (readmeAnalysis || readmeSkipped)) {
      setSaraminRetryCount((count) => count + 1);
    }
    setChatAssistantMessage("");
    setChatAssistantMessagePlacement("before-results");
    setChatIntentLoading(false);
    setAlioLoading(true);
    setPublicEmploymentLoading(true);
    setMofeLoading(true);
    setAlioError("");
    setPublicEmploymentError("");
    setMofeError("");
    setHasSearchedAlio(false);
    setHasSearchedPublicEmployment(false);
    setHasSearchedMofe(false);
    setAlioResults([]);
    setPublicEmploymentResults([]);
    setMofeResults([]);
    setAlioTotalCount(0);
    setPublicEmploymentTotalCount(0);
    setMofeTotalCount(0);

    try {
      const { data } = await supabase().auth.getSession();
      if (!data.session) throw new Error("로그인이 필요하거나 세션이 만료되었습니다.");
      const [alioResult, publicEmploymentResult, mofeResult] = await Promise.allSettled([
        searchAlioRecruitments({
          accessToken: data.session.access_token,
          query: normalizedQuery,
        }),
        searchPublicEmploymentRecruitments({
          accessToken: data.session.access_token,
          query: normalizedQuery,
        }),
        searchMofeRecruitments({
          accessToken: data.session.access_token,
          query: normalizedQuery,
        }),
      ]);

      if (generation !== practiceGenerationRef.current) return;
      const errors: string[] = [];
      let resultCount = 0;
      if (alioResult.status === "fulfilled") {
        setAlioResults(alioResult.value.recruitments);
        setAlioTotalCount(alioResult.value.totalCount);
        setHasSearchedAlio(true);
        resultCount += alioResult.value.recruitments.length;
      } else {
        const message = alioResult.reason instanceof Error
          ? alioResult.reason.message
          : "ALIO 공고를 검색하지 못했습니다.";
        setAlioError(message);
        errors.push(`ALIO 조회에 실패했어요: ${message}`);
      }

      if (publicEmploymentResult.status === "fulfilled") {
        setPublicEmploymentResults(publicEmploymentResult.value.recruitments);
        setPublicEmploymentTotalCount(publicEmploymentResult.value.totalCount);
        setHasSearchedPublicEmployment(true);
        resultCount += publicEmploymentResult.value.recruitments.length;
      } else {
        const message = publicEmploymentResult.reason instanceof Error
          ? publicEmploymentResult.reason.message
          : "공공취업정보 공고를 검색하지 못했습니다.";
        setPublicEmploymentError(message);
        errors.push(`공공취업정보 조회에 실패했어요: ${message}`);
      }

      if (mofeResult.status === "fulfilled") {
        setMofeResults(mofeResult.value.recruitments);
        setMofeTotalCount(mofeResult.value.totalCount);
        setHasSearchedMofe(true);
        resultCount += mofeResult.value.recruitments.length;
      } else {
        const message = mofeResult.reason instanceof Error
          ? mofeResult.reason.message
          : "공공기관 채용정보 공고를 검색하지 못했습니다.";
        setMofeError(message);
        errors.push(`공공기관 채용정보 조회에 실패했어요: ${message}`);
      }

      const guide = resultCount > 0
        ? `“${normalizedQuery}” 관련 공고를 찾았어요. 출처별 공고를 확인하고 분석 가능한 공고를 골라주세요.`
        : `“${normalizedQuery}” 관련 공고를 찾지 못했어요. 다른 키워드로 다시 물어봐 주세요.`;
      setChatAssistantMessage([guide, ...errors].join(" "));
    } catch (error) {
      if (generation !== practiceGenerationRef.current) return;
      const message = error instanceof Error ? error.message : "공고를 검색하지 못했습니다.";
      setAlioError(message);
      setPublicEmploymentError(message);
      setMofeError(message);
      setChatAssistantMessage(message);
    } finally {
      if (generation !== practiceGenerationRef.current) return;
      setAlioLoading(false);
      setPublicEmploymentLoading(false);
      setMofeLoading(false);
    }
  };

  const analyzeRecommendedJobPosting = (recommendation: SaraminRecommendation) => {
    const generation = practiceGenerationRef.current;
    workspace.latest();
    const existing = jobPostings.find((posting) =>
      posting.data_origin === "private_job" && posting.source_url === recommendation.source_url,
    );
    if (existing) {
      chooseJob(existing.id);
      setRecommendedReviewError("");
      setChatAssistantMessagePlacement("after-results");
      setChatAssistantMessage("이미 검토한 공고예요. 이번 답변에 연결할 요구사항을 골라주세요.");
      return;
    }
    setAnalyzingRecommendedUrl(recommendation.source_url);
    setRecommendedReviewError("");
    void supabase().auth.getSession().then(({ data }) => {
      if (!data.session) throw new Error("로그인이 필요하거나 세션이 만료되었습니다.");
      return analyzeRecommendedJob({
        accessToken: data.session.access_token,
        sourceUrl: recommendation.source_url,
      });
    }).then((posting) => {
      if (generation !== practiceGenerationRef.current) return;
      setJobPostings((current) => [posting, ...current.filter((item) => item.id !== posting.id)]);
      chooseJob(posting.id);
      setChatAssistantMessagePlacement("after-results");
      setChatAssistantMessage("공고 원문을 검토했어요. 요구사항을 1~2개 선택한 뒤 답변 연습을 시작해 주세요.");
    }).catch((error) => {
      if (generation !== practiceGenerationRef.current) return;
      setRecommendedReviewError(error instanceof Error ? error.message : "공고 원문을 검토하지 못했습니다.");
    }).finally(() => { if (generation === practiceGenerationRef.current) setAnalyzingRecommendedUrl(null); });
  };

  const analyzeAlioJobPosting = (recruitment: AlioRecruitment) => {

    const generation = practiceGenerationRef.current;    if (!recruitment.source_url) {
      setAlioError("HTTPS 원문 URL이 제공된 공고만 AI가 분석할 수 있어요.");
      return;
    }
    const sourceUrl = recruitment.source_url;
    const existing = jobPostings.find(
      (posting) => posting.data_origin === "alio" && posting.source_url === sourceUrl,
    );
    if (existing) {
      chooseJob(existing.id);
      setJobError("이미 AI 분석을 완료한 공고예요. 아래에서 요구사항을 선택해 주세요.");
      setChatAssistantMessagePlacement("after-results");
      setChatAssistantMessage("이미 분석한 공고예요. 아래에서 이번 답변에 연결할 요구사항을 골라주세요.");
      return;
    }
    setAnalyzingAnnouncementId(recruitment.announcement_id);
    setAlioError("");
    void supabase().auth.getSession().then(async ({ data }) => {
      if (!data.session) throw new Error("로그인이 필요하거나 세션이 만료되었습니다.");
      return analyzeAlioRecruitment({
        accessToken: data.session.access_token,
        input: {
          announcement_id: recruitment.announcement_id,
          company: recruitment.company,
          title: recruitment.title,
          source_url: sourceUrl,
        },
      });
    }).then((posting) => {
      if (generation !== practiceGenerationRef.current) return;
      setJobPostings((current) => [posting, ...current.filter((item) => item.id !== posting.id)]);
      chooseJob(posting.id);
      setJobError("");
      setChatAssistantMessagePlacement("after-results");
      setChatAssistantMessage(
        "공고 원문을 분석했어요. 아래의 요구사항 중 이번 답변과 연결할 항목을 1~2개 골라주세요.",
      );
    }).catch((error) => {
      if (generation !== practiceGenerationRef.current) return;
      setAlioError(error instanceof Error ? error.message : "AI 공고 분석을 저장하지 못했습니다.");
      setChatAssistantMessagePlacement("after-results");
      setChatAssistantMessage(error instanceof Error ? error.message : "AI 공고 분석을 저장하지 못했습니다.");
    }).finally(() => { if (generation === practiceGenerationRef.current) setAnalyzingAnnouncementId(null); });
  };

  const analyzePublicEmploymentJobPosting = (recruitment: PublicEmploymentRecruitment) => {

    const generation = practiceGenerationRef.current;    setAnalyzingPublicEmploymentAnnouncementId(recruitment.announcement_id);
    setPublicEmploymentError("");
    void supabase().auth.getSession().then(async ({ data }) => {
      if (!data.session) throw new Error("로그인이 필요하거나 세션이 만료되었습니다.");
      return analyzePublicEmploymentRecruitment({
        accessToken: data.session.access_token,
        input: {
          announcement_id: recruitment.announcement_id,
          company: recruitment.company,
          title: recruitment.title,
        },
      });
    }).then((posting) => {
      if (generation !== practiceGenerationRef.current) return;
      setJobPostings((current) => [posting, ...current.filter((item) => item.id !== posting.id)]);
      chooseJob(posting.id);
      setJobError("");
      setChatAssistantMessagePlacement("after-results");
      setChatAssistantMessage(
        "공고 원문을 분석했어요. 아래의 요구사항 중 이번 답변과 연결할 항목을 1~2개 골라주세요.",
      );
    }).catch((error) => {
      if (generation !== practiceGenerationRef.current) return;
      const message = error instanceof Error ? error.message : "AI 공고 분석을 저장하지 못했습니다.";
      setPublicEmploymentError(message);
      setChatAssistantMessagePlacement("after-results");
      setChatAssistantMessage(message);
    }).finally(() => { if (generation === practiceGenerationRef.current) setAnalyzingPublicEmploymentAnnouncementId(null); });
  };

  const analyzeMofeJobPosting = (recruitment: MofeRecruitment) => {

    const generation = practiceGenerationRef.current;    setAnalyzingMofeAnnouncementId(recruitment.announcement_id);
    setMofeError("");
    void supabase().auth.getSession().then(async ({ data }) => {
      if (!data.session) throw new Error("로그인이 필요하거나 세션이 만료되었습니다.");
      return analyzeMofeRecruitment({
        accessToken: data.session.access_token,
        input: {
          announcement_id: recruitment.announcement_id,
          company: recruitment.company,
          title: recruitment.title,
        },
      });
    }).then((posting) => {
      if (generation !== practiceGenerationRef.current) return;
      setJobPostings((current) => [posting, ...current.filter((item) => item.id !== posting.id)]);
      chooseJob(posting.id);
      setJobError("");
      setChatAssistantMessagePlacement("after-results");
      setChatAssistantMessage(
        "공고 원문을 분석했어요. 아래의 요구사항 중 이번 답변과 연결할 항목을 1~2개 골라주세요.",
      );
    }).catch((error) => {
      if (generation !== practiceGenerationRef.current) return;
      const message = error instanceof Error ? error.message : "AI 공고 분석을 저장하지 못했습니다.";
      setMofeError(message);
      setChatAssistantMessagePlacement("after-results");
      setChatAssistantMessage(message);
    }).finally(() => { if (generation === practiceGenerationRef.current) setAnalyzingMofeAnnouncementId(null); });
  };

  const persistPracticeSession = async (): Promise<PracticeQuestion> => {
    if (!selectedJob || selectedRequirementIds.length < 1) {
      throw new Error("공고와 요구사항을 먼저 선택해 주세요.");
    }
    const { data } = await supabase().auth.getSession();
    if (!data.session) throw new Error("로그인이 필요하거나 세션이 만료되었습니다.");
    const session = await createPracticeSession({
      accessToken: data.session.access_token,
      input: {
        applicant_context: {
          selected_ncs_ids: [...(submittedNcsIds || [])],
          readme_analysis: readmeAnalysis,
          resume_profile: resumeProfile,
        },
        job_posting_id: selectedJob.id,
        requirement_ids: selectedRequirementIds,
        question_type: selectedQuestionInfo.questionType,
        question_id: selectedQuestionInfo.questionId,
        custom_question_text: selectedQuestionInfo.questionType === "custom"
          ? selectedQuestionInfo.question
          : null,
      },
    });
    await preparation.bind(session.practice_session_id, data.session.access_token);
    return {
      ...selectedQuestionInfo,
      practiceSessionId: session.practice_session_id,
      jobPostingId: selectedJob.id,
      requirementIds: [...selectedRequirementIds],
    };
  };

  const checkMicrophone = async () => {
    if (!isLoggedIn) {
      onLogin();
      return;
    }
    const generation = practiceGenerationRef.current;
    setMicrophoneState("checking");
    setSetupError("");

    if (MOCK_ERROR_STATE === "mic-permission-denied") {
      setMicrophoneState("denied");
      return;
    }

    if (MOCK_ERROR_STATE === "mic-unavailable") {
      setMicrophoneState("error");
      return;
    }

    try {
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error("getUserMedia is not supported");
      }

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.getTracks().forEach((track) => track.stop());
      if (generation !== practiceGenerationRef.current) return;
      setMicrophoneState("granted");
    } catch (error) {
      if (generation !== practiceGenerationRef.current) return;
      console.error("[말해봄] 연습 준비 실패", error);

      const errorName =
        error instanceof DOMException ? error.name : "UnknownError";
      if (errorName === "NotAllowedError" || errorName === "PermissionDeniedError") {
        setMicrophoneState("denied");
      } else if (error instanceof Error && !error.message.includes("getUserMedia")) {
        setMicrophoneState("idle");
        setSetupError(error.message);
      } else {
        setMicrophoneState("error");
      }
    }
  };

  const handleStart = () => {
    if (!canStart) return;
    void checkMicrophone();
  };

  const handleRecordingStart = () => {
    void checkMicrophone();
  };

  const prepareQuestionForInlineRecording = async (): Promise<PracticeQuestion> => {
    if (isInlineRerecord && retryQuestion) return retryQuestion;
    return persistPracticeSession();
  };

  const handleInlineRecordingSubmit = (preparedQuestion: PracticeQuestion, audio: Blob) => {
    if (practiceGeneration !== practiceGenerationRef.current) return;
    workspace.latest();
    const attemptNo: 1 | 2 = isInlineRerecord ? 2 : 1;
    if (attemptNo === 2) coachThreadRef.current?.dispatchEvent(new Event("workspace-next-stage"));
    if (onAnalysisReady) {
      onAnalysisReady(preparedQuestion, audio, attemptNo);
      return;
    }
    workspace.register({ id: workspaceId("task", preparedQuestion.practiceSessionId || "current", "question"), messageId: workspaceId("message", preparedQuestion.practiceSessionId || "current", "question"), title: "면접 질문 선택", text: preparedQuestion.question, evidenceIds: [] });
    setActiveAnswerAnalysis({
      question: preparedQuestion,
      audio,
      attemptNo,
      practiceSessionId: preparedQuestion.practiceSessionId,
      contextEvidenceIds: workspace.evidence.filter((item) => item.taskId === workspaceId("task", "job", preparedQuestion.jobPostingId || "") || item.taskId === workspaceId("task", "requirements", preparedQuestion.jobPostingId || "", ...[...(preparedQuestion.requirementIds || [])].sort()) || (readmeAnalysis && item.taskId === workspaceId("task", "readme", readmeAnalysis.source_url, readmeAnalysis.readme_sha))).map((item) => item.id),
    });
    setRetryRecordingOpen(false);
  };

  const handleWavUpload = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    if (!isWavFile(file)) {
      setRecordingPromptError("WAV 파일만 올릴 수 있어요.");
      return;
    }
    if (!isLoggedIn) {
      onLogin();
      return;
    }
    if (!isInlineRerecord && (!questionTypeChosen || !canStart)) {
      setRecordingPromptError("먼저 질문 유형과 연습할 질문을 골라주세요.");
      return;
    }

    const generation = practiceGenerationRef.current;
    workspace.latest();
    setWavUploadPending(true);
    setRecordingPromptError("");
    void prepareQuestionForInlineRecording().then((preparedQuestion) => {
      if (generation !== practiceGenerationRef.current) return;
      setPendingWav({ file, question: preparedQuestion, url: createAudioUrl(file) });
    }).catch((error) => {
      if (generation !== practiceGenerationRef.current) return;
      setRecordingPromptError(
        error instanceof Error ? error.message : "WAV 파일을 준비하지 못했습니다.",
      );
    }).finally(() => { if (generation === practiceGenerationRef.current) setWavUploadPending(false); });
  };

  const discardPendingWav = () => setPendingWav(null);

  const submitPendingWav = () => {
    if (!pendingWav) return;
    handleInlineRecordingSubmit(pendingWav.question, pendingWav.file);
    setPendingWav(null);
  };

  const completeAnswerAnalysis = (result: AnalysisResult) => {
    if (!activeAnswerAnalysis || practiceGeneration !== practiceGenerationRef.current) return;
    const completed = { ...activeAnswerAnalysis, result };
    setCompletedAnswerAnalyses((current) => [...current, completed]);
    setActiveAnswerAnalysis(null);
    setRetryQuestion({
      ...activeAnswerAnalysis.question,
      practiceSessionId: result.practiceSessionId || activeAnswerAnalysis.question.practiceSessionId,
    });
    onAnalysisComplete?.(activeAnswerAnalysis.question, result);
  };

  const retryAnswer = () => {
    setView("question-select");
    setMicrophoneState("idle");
    setPendingWav(null);
    setRecordingPromptError("");
    setRetryRecordingOpen(true);
  };

  const markCoachingReady = (attemptNo: 1 | 2) => {
    setCoachingReadyAttempts((current) => {
      if (current.has(attemptNo)) return current;
      const next = new Set(current);
      next.add(attemptNo);
      return next;
    });
  };

  const showInlineComparison = () => {
    if (!canStartComparison) return;
    setInlineComparisonRequested(true);
    coachThreadRef.current?.dispatchEvent(new Event("workspace-comparison"));
  };

  const toggleNcsCompetency = (id: string) => {
    if (submittedNcsIds) return;
    setSelectedNcsIds((current) => current.includes(id)
      ? current.filter((selectedId) => selectedId !== id)
      : [...current, id]);
  };

  const requestReadmeAnalysis = (url: string) => {
    const requestId = ++readmeRequestIdRef.current;
    setReadmeAnalysis(null);
    setReadmeAnalysisError("");
    setReadmeAnalysisLoading(true);
    void supabase().auth.getSession().then(({ data }) => {
      if (!data.session) throw new Error("로그인이 필요하거나 세션이 만료되었습니다.");
      return analyzeGithubReadme({ accessToken: data.session.access_token, sourceUrl: url });
    }).then((result) => {
      if (readmeRequestIdRef.current === requestId) setReadmeAnalysis(result);
    }).catch((error) => {
      if (readmeRequestIdRef.current === requestId) {
        setReadmeAnalysisError(error instanceof Error ? error.message : "README를 분석하지 못했습니다.");
      }
    }).finally(() => {
      if (readmeRequestIdRef.current === requestId) setReadmeAnalysisLoading(false);
    });
  };

  const handleReadmeSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (submittedReadmeUrl || readmeSkipped || !submittedNcsIds) return;
    const url = githubReadmeUrl(readmeUrlInput);
    if (!url) {
      setReadmeUrlError("GitHub 저장소 또는 README.md 주소를 확인해 주세요.");
      return;
    }
    setReadmeUrlError("");
    setSubmittedReadmeUrl(url);
    requestReadmeAnalysis(url);
  };

  const handleReadmeSkip = () => {
    if (submittedReadmeUrl || readmeSkipped || !submittedNcsIds) return;
    setReadmeUrlInput("");
    setReadmeUrlError("");
    setReadmeSkipped(true);
  };

  const pendingPreparationStep: PreparationStage | null = isLoggedIn && !isInlineRerecord
    ? submittedNcsIds && !resumeStepOpened ? "ncs"
      : (resumeProfile || resumeSkipped) && !readmeStepOpened ? "resume"
        : (readmeAnalysis || readmeSkipped) && !jobSearchStarted ? "readme" : null
    : null;
  useEffect(() => {
    if (!resumeStepOpened && !readmeStepOpened && !jobSearchStarted) return;
    coachThreadRef.current?.dispatchEvent(new Event("workspace-next-stage"));
  }, [resumeStepOpened, readmeStepOpened, jobSearchStarted, coachThreadRef]);

  const advancePreparationStep = () => {
    if (preparation.loading || readmeAnalysisLoading) return;
    coachThreadRef.current?.dispatchEvent(new Event("workspace-next-stage"));
    if (pendingPreparationStep === "ncs") setResumeStepOpened(true);
    else if (pendingPreparationStep === "resume") setReadmeStepOpened(true);
    else if (pendingPreparationStep === "readme") setJobSearchStarted(true);
  };

  const renderPreparationGuide = (stage: "ncs" | "resume" | "readme") => <>
    {showPreparationStage(stage) && isLoggedIn && (stage === "ncs" ? Boolean(submittedNcsIds) : stage === "resume" ? Boolean(resumeProfile || resumeSkipped) : Boolean(readmeAnalysis || readmeSkipped)) && <article className="coach-message coach-message-assistant" aria-label="다음 단계 진행 안내">
      <span className="coach-message-avatar" aria-hidden="true">✦</span>
      <div><strong>말해봄 코치</strong>
        <p>{stage === "ncs"
          ? "NCS 선택을 완료했어요. 확인할 부분이나 궁금한 점이 있으면 채팅을 입력해 주세요."
          : stage === "resume"
            ? resumeSkipped
              ? "이력서 제출을 건너뛰었어요. 추가할 경력 사항이나 경험, 궁금한 부분이 있으면 채팅을 입력해 주세요."
              : "이력서 검토가 완료되었어요. 추가할 경력 사항이나 경험, 궁금한 부분이 있으면 채팅을 입력해 주세요."
            : readmeSkipped
              ? "README 제출을 건너뛰었어요. 추가할 경험이나 궁금한 점이 있으면 채팅을 입력해 주세요."
              : "README 검토가 완료되었어요. 본인의 구현 범위나 추가할 경험, 궁금한 부분이 있으면 채팅을 입력해 주세요."}</p>
        <p>진행하려면 ‘다음으로’라고 입력하거나 보내기 옆의 ‘다음 단계’ 버튼을 눌러 주세요.</p>
      </div>
            </article>}
  </>;

  const renderPreparationChat = (placement: PreparationChatPlacement) =>
    <PreparationConversationChat turns={preparation.turns.filter((turn) => turn.placement === placement)} disabled={preparation.loading}
      pendingToken={preparation.turns.at(-1)?.response?.restart?.token}
      onConfirm={(token, confirm) => handleChatSubmit({ preventDefault() {} } as FormEvent<HTMLFormElement>, confirm ? "네" : "취소", { token, confirm })} />;

  const firstAnswerAwaitingCoaching = completedAnswerAnalyses.some((item) => item.attemptNo === 1) && !coachingReadyAttempts.has(1);

  preparationSelectionFingerprint.current = JSON.stringify([selectedJobId, selectedRequirementIds, selectedNcsIds,
    submittedNcsIds, selectedQuestionInfo.questionId, customQuestion]);

  const handleChatSubmit = (event: FormEvent<HTMLFormElement>, forcedMessage?: string, restartConfirmation?: { token: string; confirm: boolean }) => {
    event.preventDefault();
    const message = (forcedMessage ?? chatInput).trim();
    if (!message) return;
    coachThreadRef.current?.dispatchEvent(new Event("workspace-next-stage"));
    if (pendingPreparationStep && /^(?:다음(?:\s*단계)?(?:으로|로)?)(?:\s*(?:진행해|넘어가|가)(?:줘|주세요))?[.!]?$/.test(message)) {
      if (preparation.loading) return;
      preparation.appendUserMessage(message, pendingPreparationStep, `${pendingPreparationStep}_review`);
      setChatInput("");
      advancePreparationStep();
      return;
    }
    if (canStartSecondRecording && !wavUploadPending && !pendingWav && !inlineRecordingActive
        && !isChatRequestLoading && !isAnalyzingRecruitment && isReanswerCommand(message)) {
      setChatInput("");
      retryAnswer();
      return;
    }
    const generation = practiceGenerationRef.current;
    const selectionFingerprint = preparationSelectionFingerprint.current;
    const first = completedAnswerAnalyses.find((item) => item.attemptNo === 1);
    const resetRequest = /(?:리드미|README|NCS|이력서|공고|질문).*(?:교체|변경|바꿔|다시\s*선택|선택\s*다시|재선택|다시\s*제출|처음부터|돌아|이동|만\s*보여)/i.test(message);
    const explicitJobSearch = !resetRequest && !newGraduateOnly && !pendingPreparationStep && !first
      && /공고|채용|\bJD\b/i.test(message)
      && !/^(?:이|해당|선택한|현재|아까).*공고.*만.*보여/.test(message)
      && (/검색|찾|공고.*추천|(?:공고|채용).*만.*보여/i.test(message)
        || (!selectedJob
          && !/원본|원문|사이트|마감|회사|요구사항|이 공고|선택한 공고|요약|피드백|설명|차이|비교|이력서|경험|질문/.test(message)));
    const preparationStage: PreparationStage = pendingPreparationStep ?? (first && coachingReadyAttempts.has(1)
      ? "first_coaching" : !submittedNcsIds ? "ncs" : !resumeProfile && !resumeSkipped ? "resume" : "readme");
    if (isLoggedIn && !explicitJobSearch) {
      setChatInput("");
      void preparation.send(message, preparationStage,
        first?.result.practiceSessionId || first?.question.practiceSessionId || retryQuestion?.practiceSessionId || null,
        { selected_ncs_ids: [...(submittedNcsIds || selectedNcsIds)], readme_analysis: readmeAnalysis, resume_profile: resumeProfile },
        () => { if (canStartSecondRecording) retryAnswer(); },
        first && coachingReadyAttempts.has(1) ? "first_coaching"
          : view === "question-select" ? "questions"
            : selectedJob ? "requirements"
              : jobSearchStarted ? "jobs"
                : readmeStepOpened ? (readmeAnalysis || readmeSkipped ? "readme_review" : "readme")
                  : resumeStepOpened ? (resumeProfile || resumeSkipped ? "resume_review" : "resume")
                    : submittedNcsIds ? "ncs_review" : "ncs",
        { job_posting_id: selectedJob?.id ?? null, requirement_ids: [...selectedRequirementIds],
          question_id: selectedQuestionInfo.questionId,
          custom_question_text: questionType === "custom" && customQuestion.trim() ? customQuestion.trim() : null },
        (selection, job) => {
          if (generation !== practiceGenerationRef.current || selectionFingerprint !== preparationSelectionFingerprint.current) return false;
          if (job) setJobPostings((items) => items.some((item) => item.id === job.id) ? items : [...items, job]);
          setSelectedJobId(selection.job_posting_id);
          setSelectedRequirementIds(selection.requirement_ids);
          setSelectedNcsIds(selection.selected_ncs_ids);
          if (submittedNcsIds) setSubmittedNcsIds((current) =>
            current?.join("|") === selection.selected_ncs_ids.join("|") ? current : selection.selected_ncs_ids);
          if (selection.question_id || selection.custom_question_text) setQuestionTypeChosen(true);
          if (selection.question_id) {
            setQuestionType("preset");
            setSelectedCategoryId("preset");
            setSelectedQuestion(Number(selection.question_id.slice(-2)) - 1);
            setCustomQuestion("");
          } else {
            setSelectedQuestion(null);
            setCustomQuestion(selection.custom_question_text || "");
            if (selection.custom_question_text) setQuestionType("custom");
          }
          return true;
        }, applyRestart, restartConfirmation);
      return;
    }
    setChatMessages((current) => [...current, message]);
    setChatInput("");
    if (!isLoggedIn) {
      setChatAssistantMessagePlacement("before-results");
      setChatAssistantMessage("공고를 찾고 분석하려면 먼저 로그인해 주세요.");
      return;
    }
    setChatSearchRequested(true);
    setChatIntentLoading(true);
    setChatAssistantMessage("");
    setChatAssistantMessagePlacement("before-results");
    void supabase().auth.getSession().then(async ({ data }) => {
      if (!data.session) throw new Error("로그인이 필요하거나 세션이 만료되었습니다.");
      return interpretJobSearchMessage({
        accessToken: data.session.access_token,
        message,
      });
    }).then((intent) => {
      if (generation !== practiceGenerationRef.current) return;
      if (intent.should_search && intent.query) {
        void requestChatRecruitmentSearch(intent.query);
        return;
      }
      setChatSearchRequested(false);
      setChatAssistantMessage("공고를 찾고 싶다면 원하는 직무나 기술을 자연스럽게 말씀해 주세요. 예: “백엔드 관련 공고 보여줘”");
    }).catch((error) => {
      if (generation !== practiceGenerationRef.current) return;
      setChatSearchRequested(false);
      setChatAssistantMessage(
        error instanceof Error ? error.message : "채팅 메시지를 이해하지 못했습니다.",
      );
    }).finally(() => { if (generation === practiceGenerationRef.current) setChatIntentLoading(false); });
  };

  useEffect(() => {
    if (!isLoggedIn) return;
    for (const experience of preparation.confirmedExperiences) {
      const taskId = workspaceId("task", "chat-experience", experience.id);
      const id = workspaceId("evidence", "chat-experience", experience.id);
      const confirmationTurn = [...preparation.turns].reverse().find((turn) => turn.response);
      const messageId = workspaceId("message", "preparation", confirmationTurn?.requestId || experience.id);
      workspace.register({ id: taskId, messageId, title: "추가 경험 확인 완료", evidenceIds: [id] }, [{
        id, taskId, messageId, title: "채팅으로 추가한 경험·경력", kind: "reference",
        text: experience.facts.map((fact) => `${fact.value}\n원문: ${fact.source_excerpt}`).join("\n\n"),
        summaryLines: [...new Set(experience.facts.map((fact) => fact.value))].slice(0, 5),
      }]);
    }
  }, [preparation.confirmedExperiences, preparation.turns, isLoggedIn, workspace.register]);

  useEffect(() => {
    if (!isLoggedIn) return;
    if (submittedNcsIds) workspace.register({ id: "task:ncs", messageId: "message:ncs", title: "역량 자기점검 완료", evidenceIds: [] });
    if (resumeProfile) workspace.register({ id: "task:resume", messageId: "message:resume", title: "이력서 정보 확인 완료", evidenceIds: ["evidence:resume"] }, [{ id: "evidence:resume", taskId: "task:resume", messageId: "message:resume", title: "확인한 이력서 정보", kind: "reference", text: resumeProfile.facts.map((fact) => fact.value).join("\n"), summaryLines: resumeProfile.facts.slice(0, 5).map((fact) => fact.value) }]);
    if (readmeAnalysis) {
      const taskId = workspaceId("task", "readme", readmeAnalysis.source_url, readmeAnalysis.readme_sha);
      const messageId = workspaceId("message", "readme", readmeAnalysis.source_url, readmeAnalysis.readme_sha);
      const id = workspaceId("evidence", "readme", readmeAnalysis.source_url, readmeAnalysis.readme_sha);
      workspace.register({ id: taskId, messageId, title: "README 분석 완료", evidenceIds: [id] }, [{ id, taskId, messageId, title: "GitHub README", kind: "reference", sourceUrl: readmeAnalysis.source_url, summaryLines: [...readmeAnalysis.technology_stack].sort((a, b) => technicalPriority(b.name + " " + b.description) - technicalPriority(a.name + " " + a.description)).slice(0, 3).map((item) => `${item.name} — ${item.description}`), text: [...readmeAnalysis.technology_stack.map((item) => item.source_excerpt), ...readmeAnalysis.project_flow.map((item) => item.source_excerpt)].filter(Boolean).join("\n") || "분석된 원문 링크를 확인해 주세요." }]);
    }
    if (selectedJob) {
      const taskId = workspaceId("task", "job", selectedJob.id);
      const messageId = workspaceId("message", "job", selectedJob.id);
      const id = workspaceId("evidence", "job", selectedJob.id);
      const recommendation = saraminRecommendations.find((item) => item.source_url === selectedJob.source_url);
      const jobSummary = [selectedJob.title, recommendation?.experience ? `경력 조건: ${recommendation.experience}` : "", recommendation?.deadline ? `마감일: ${recommendation.deadline}` : "", ...selectedJob.requirements.slice(0, 3).map((item) => item.text)].filter(Boolean);
      workspace.register({ id: taskId, messageId, title: "채용 공고 선택", evidenceIds: [id] }, [{ id, taskId, messageId, title: selectedJob.company, text: [selectedJob.title, ...selectedJob.requirements.map((item) => item.source_excerpt || item.text)].join("\n"), summaryLines: jobSummary, kind: "reference", sourceUrl: selectedJob.source_url }]);
      if (view === "question-select" && selectedRequirements.length) {
        const requirementTaskId = workspaceId("task", "requirements", selectedJob.id, ...[...selectedRequirementIds].sort());
        const requirementMessageId = workspaceId("message", "requirements", selectedJob.id, ...[...selectedRequirementIds].sort());
        const items = selectedRequirements.map((item) => ({ id: workspaceId("evidence", "requirement", requirementTaskId, item.id), taskId: requirementTaskId, messageId: requirementMessageId, title: `공고 요구사항 · ${item.text}`, text: item.source_excerpt || item.text, kind: "reference" as const, sourceUrl: selectedJob.source_url }));
        workspace.register({ id: requirementTaskId, parentId: taskId, messageId: requirementMessageId, title: "공고 요구사항 선택 완료", evidenceIds: items.map((item) => item.id) }, items);
      }
    }
    if (completedAnswerAnalyses.length) {
      for (const completed of completedAnswerAnalyses) if (completed.result.analysisJobId) workspace.register({ id: workspaceId("task", completed.result.analysisJobId, "analysis"), messageId: workspaceId("message", completed.result.analysisJobId, "analysis"), title: `${completed.attemptNo}차 답변 분석 완료`, evidenceIds: [] });
    }
    if (inlineComparisonRequested) workspace.register({ id: "task:comparison", messageId: "message:comparison", title: "재답변 비교 요청", evidenceIds: workspace.evidence.filter((item) => item.kind === "answer").map((item) => item.id) });
  }, [submittedNcsIds, resumeProfile, readmeAnalysis, selectedJob, saraminRecommendations, selectedRequirements, completedAnswerAnalyses, inlineComparisonRequested, isLoggedIn, view, workspace.register]);

  const changeSelectedJob = () => handleChatSubmit({ preventDefault() {} } as FormEvent<HTMLFormElement>, "공고 다시 선택해줘");

  return (
    <div className="practice-page coach-chat-page">
      <AppHeader />

      <main className="coach-chat-layout" id="practice">
        <aside className="coach-sidebar" aria-label="연습 진행 단계">
          <WorkspaceHistory tasks={workspace.tasks} selectedTaskId={workspace.selectedTaskId} onSelect={(task) => workspace.navigate(task.id, task.messageId)} onLatest={workspace.latest} />
          {activeAnswerAnalysis && <p className="workspace-empty" role="status">{activeAnswerAnalysis.attemptNo}차 답변을 분석하고 있어요.</p>}
          <nav className="coach-followup-menu" aria-label="설정 변경 후 연습 시작">
            <p>설정 변경 후 연습 시작</p>
            {([ ["NCS 변경", "NCS 다시 선택해줘"], ["이력서 교체", "이력서 다시 제출할게"], ["리드미 교체", "리드미 링크 교체해줘"], ["공고 변경", "공고 다시 선택해줘"], ["질문 변경", "질문 선택으로 이동해줘"] ] as const).map(([label, message]) => <button key={label} type="button" disabled={!isLoggedIn || (label !== "NCS 변경" && !submittedNcsIds) || (label === "질문 변경" && !canContinueToQuestion) || preparation.loading || firstAnswerAwaitingCoaching || Boolean(activeAnswerAnalysis) || inlineRecordingActive || isAnalyzingRecruitment || readmeAnalysisLoading} onClick={() => handleChatSubmit({ preventDefault() {} } as FormEvent<HTMLFormElement>, message)}><span aria-hidden="true">↻</span><strong>{label}</strong><small>변경 범위 확인 후 진행</small></button>)}
          </nav>
          <nav className="coach-followup-menu" aria-label="재연습 및 비교 분석">
            <p>다음 연습</p>
            <button
              type="button"
              className={secondRecordingClassName}
              disabled={!canStartSecondRecording}
              onClick={retryAnswer}
              title={secondRecordingTitle}
              aria-current={isSecondAnswerInProgress ? "step" : undefined}
            >
              <span aria-hidden="true">{hasCompletedSecondAnswer ? "✓" : "↻"}</span>
              <strong>2차 녹음</strong>
              <small>{secondRecordingHint}</small>
            </button>
            <button
              type="button"
              className={canStartComparison ? "is-available" : ""}
              disabled={!canStartComparison}
              onClick={showInlineComparison}
              title={canStartComparison ? "1차와 2차 답변 비교하기" : "2차 전사문을 확인하면 이용할 수 있어요."}
            >
              <span aria-hidden="true">↗</span>
              <strong>답변 비교 분석</strong>
              <small>1차 코칭 후 재답변 변화 확인</small>
            </button>
          </nav>
          <p className="coach-sidebar-note">선택한 연습 맥락은 이번 답변과 코칭을 연결하는 데만 사용해요.</p>
        </aside>

        <section className="coach-chat-panel" aria-labelledby="coach-chat-title">
          <header className="coach-chat-header">
            <div>
              <p>말해봄 AI 코치</p>
              <h1 id="coach-chat-title">
                {isInlineRerecord
                  ? "같은 질문으로 다시 답해볼까요?"
                  : currentPracticeStep === 4
                    ? "답변을 함께 다듬어볼까요?"
                    : currentPracticeStep === 3
                      ? "이제 답변을 들려주세요."
                      : currentPracticeStep === 2
                        ? "이제 질문을 골라볼까요?"
                        : "오늘의 면접 연습을 준비해볼까요?"}
              </h1>
            </div>
            <span className="coach-online-status"><i aria-hidden="true" />{activeAnswerAnalysis ? "답변 분석 중" : coachingReadyAttempts.size ? "코칭 결과 확인" : "연습 진행 중"}</span>
          </header>

          <div className="coach-thread" ref={coachThreadRef}>
            <PracticeChatHistory messages={chatHistory} />
            <article className="coach-message coach-message-assistant">
              <span className="coach-message-avatar" aria-hidden="true">✦</span>
              <div>
                <strong>말해봄 코치</strong>
                <p>
                  {isInlineRerecord
                    ? "앞선 피드백을 떠올리며 같은 질문에 한 번 더 답해보세요. 채팅 안에서 바로 녹음할 수 있어요."
                    : "안녕하세요. 지원할 공고와 연결할 요구사항을 먼저 정해볼게요. 선택한 맥락을 기준으로 답변을 함께 살펴봐요."}
                </p>
                <time>방금</time>
              </div>
            </article>

            {showPreparationStage("ncs") && !isInlineRerecord && (
              <article className="coach-message coach-message-assistant coach-ncs-message" aria-label="백엔드 개발 역량 자기점검">
                <span className="coach-message-avatar" aria-hidden="true">✦</span>
                <div className="coach-ncs-card">
                  <strong>백엔드 개발에 필요한 역량을 살펴볼까요?</strong>
                  <p>응용SW엔지니어링 NCS 능력단위를 참고해 말해봄이 정리한 지식·기술·태도 항목이에요. 자신이 보유했다고 생각하는 항목을 골라주세요.</p>
                  {!isLoggedIn ? (
                    <button className="coach-ncs-action" type="button" onClick={onLogin}>로그인하고 선택하기</button>
                  ) : ncsLoading ? (
                    <p role="status">NCS 역량을 불러오고 있어요.</p>
                  ) : ncsError ? (
                    <div role="alert"><p>{ncsError}</p><button className="coach-ncs-action" type="button" onClick={() => setNcsRetryCount((current) => current + 1)}>다시 시도</button></div>
                  ) : ncsCompetencies ? (
                    <>
                      {ncsCompetencies.data_source === "cached" && (
                        <p role="status">
                          DB에 저장된 마지막 정상 조회 NCS 목록을 사용하고 있어요.
                          {ncsCompetencies.fetched_at && ` 마지막 조회: ${new Date(ncsCompetencies.fetched_at).toLocaleString("ko-KR", { timeZone: "Asia/Seoul" })}`}
                        </p>
                      )}
                      {NCS_CATEGORY_LABELS.map((category) => (
                        <section className="coach-ncs-category" aria-label={category.label} key={category.id}>
                          <h2>{category.label}</h2>
                          <div className="coach-ncs-options">
                            {ncsCompetencies.options.filter((option) => option.category === category.id).map((option) => (
                              <button
                                type="button"
                                className={selectedNcsIds.includes(option.id) ? "coach-ncs-option is-selected" : "coach-ncs-option"}
                                key={option.id}
                                aria-pressed={selectedNcsIds.includes(option.id)}
                                disabled={submittedNcsIds !== null}
                                onClick={() => toggleNcsCompetency(option.id)}
                              >
                                <span aria-hidden="true">{selectedNcsIds.includes(option.id) ? "✓" : "+"}</span>
                                <span><strong>{option.label}</strong><small>NCS 근거: {option.ncs_unit_name}</small></span>
                              </button>
                            ))}
                          </div>
                        </section>
                      ))}
                      {submittedNcsIds ? <p>선택 내용을 현재 채팅에 표시했어요.</p> : (
                        <button className="coach-ncs-action" type="button" disabled={selectedNcsIds.length === 0} onClick={() => setSubmittedNcsIds([...selectedNcsIds])}>선택 완료</button>
                      )}
                      <small className="coach-ncs-source">출처: <a href={ncsCompetencies.source_url} target="_blank" rel="noreferrer">NCS {ncsCompetencies.job_name} 기준정보</a> · 지식·기술·태도 선택 문구는 말해봄이 작성했어요.</small>
                    </>
                  ) : null}
                </div>
              </article>
            )}

            {renderPreparationChat("ncs")}

            {showPreparationStage("ncs") && submittedNcsIds && ncsCompetencies && (
              <article id="message:ncs" className="coach-message coach-message-user coach-ncs-selection">
                <div>
                  <span>나 · 자기점검</span>
                  <strong>제가 보유했다고 선택한 역량</strong>
                  <ul>{NCS_CATEGORY_LABELS.map((category) => {
                    const labels = ncsCompetencies.options
                      .filter((option) => option.category === category.id && submittedNcsIds.includes(option.id))
                      .map((option) => option.label);
                    return labels.length ? <li key={category.id}>{category.label}: {labels.join(", ")}</li> : null;
                  })}</ul>
                </div>
              </article>
            )}

            {renderPreparationGuide("ncs")}
            {renderPreparationChat("ncs_review")}

            {showPreparationStage("resume") && resumeSkipped && !isInlineRerecord && (
              <article className="coach-message coach-message-user coach-resume-skip-selection" aria-label="사용자가 이력서 제출을 건너뛰고 진행">
                <div>
                  <span>나 · 이력서</span>
                  <strong>이번에는 이력서 제출을 건너뛸게요.</strong>
                </div>
              </article>
            )}

            {showPreparationStage("resume") && resumeStepOpened && submittedNcsIds && ncsCompetencies && !isInlineRerecord && <ResumeSubmissionChat onSourceFile={setResumeSourceFile} profile={resumeProfile} onConfirm={setResumeProfile} skipped={resumeSkipped} onSkip={() => { setResumeSkipped(true); coachThreadRef.current?.dispatchEvent(new Event("workspace-next-stage")); }} />}

            {renderPreparationChat("resume")}
            {renderPreparationGuide("resume")}
            {renderPreparationChat("resume_review")}

            {showPreparationStage("readme") && readmeStepOpened && submittedNcsIds && (resumeProfile || resumeSkipped) && ncsCompetencies && !isInlineRerecord && (
              <article className="coach-message coach-message-assistant coach-readme-message" aria-label="GitHub README 링크 요청">
                <span className="coach-message-avatar" aria-hidden="true">✦</span>
                <div>
                  <strong>프로젝트 README 링크를 보내주세요. (선택)</strong>
                  <p>선택한 역량을 보여줄 프로젝트의 GitHub 저장소 또는 README.md 주소를 입력해 주세요.</p>
                  {submittedReadmeUrl ? <p>제출한 README를 분석해 기술 스택과 프로젝트 흐름을 확인할게요.</p> : readmeSkipped ? (
                    <p>README 제출을 건너뛰었어요. 공고를 선택하거나 채팅으로 연습을 계속해 주세요.</p>
                  ) : (
                    <form className="coach-readme-form" onSubmit={handleReadmeSubmit} noValidate>
                      <label className="sr-only" htmlFor="coach-readme-url">GitHub README 링크</label>
                      <input
                        id="coach-readme-url"
                        type="url"
                        inputMode="url"
                        placeholder="https://github.com/사용자/저장소"
                        value={readmeUrlInput}
                        onChange={(event) => { setReadmeUrlInput(event.target.value); setReadmeUrlError(""); }}
                        aria-invalid={Boolean(readmeUrlError)}
                        aria-describedby={readmeUrlError ? "coach-readme-error" : undefined}
                      />
                      <button type="submit">링크 제출</button>
                      <button className="coach-readme-skip" type="button" onClick={handleReadmeSkip}>건너뛰기</button>
                      {readmeUrlError && <p id="coach-readme-error" role="alert">{readmeUrlError}</p>}
                    </form>
                  )}
                </div>
              </article>
            )}

            {renderPreparationChat("readme")}

            {showPreparationStage("readme") && submittedReadmeUrl && (
              <article className="coach-message coach-message-user coach-readme-selection" aria-label="제출한 GitHub README 링크">
                <div>
                  <span>나 · 프로젝트 README</span>
                  <a href={submittedReadmeUrl} target="_blank" rel="noreferrer noopener">{submittedReadmeUrl}</a>
                </div>
              </article>
            )}

            {showPreparationStage("readme") && readmeSkipped && (
              <article className="coach-message coach-message-user coach-readme-skip-selection" aria-label="GitHub README 제출 건너뛰기">
                <div>
                  <span>나 · 프로젝트 README</span>
                  <strong>이번에는 README 제출을 건너뛸게요.</strong>
                </div>
              </article>
            )}

            {showPreparationStage("readme") && submittedReadmeUrl && readmeAnalysisLoading && (
              <CoachLoadingCard className="coach-readme-analysis-loading" label="README 분석 중" badge="README 분석 중" title="README를 읽고 분석하고 있어요.">
                기술 스택과 프로젝트 흐름을 정리하고 있어요.<br />완료되면 분석 결과를 확인할 수 있어요.
              </CoachLoadingCard>
            )}

            {showPreparationStage("readme") && submittedReadmeUrl && readmeAnalysisError && !readmeAnalysisLoading && (
              <article className="coach-message coach-message-assistant coach-readme-analysis-error" role="alert">
                <span className="coach-message-avatar" aria-hidden="true">✦</span>
                <div>
                  <strong>README 분석을 완료하지 못했어요.</strong>
                  <p>{readmeAnalysisError}</p>
                  <div className="coach-readme-actions">
                    <button type="button" onClick={() => requestReadmeAnalysis(submittedReadmeUrl)}>다시 분석</button>
                    <button type="button" onClick={() => {
                      readmeRequestIdRef.current += 1;
                      setSubmittedReadmeUrl(null);
                      setReadmeAnalysisError("");
                      setReadmeAnalysis(null);
                    }}>주소 수정</button>
                  </div>
                </div>
              </article>
            )}

            {showPreparationStage("readme") && submittedReadmeUrl && readmeAnalysis && !readmeAnalysisLoading && (
              <article id={workspaceId("message", "readme", readmeAnalysis.source_url, readmeAnalysis.readme_sha)} className="coach-message coach-message-assistant coach-readme-analysis-result" aria-label="GitHub README 분석 결과">
                <span className="coach-message-avatar" aria-hidden="true">✦</span>
                <div>
                  <strong>README 분석 결과</strong>
                  <section className="coach-readme-analysis-section">
                    <h3>기술 스택</h3>
                    <ul>{readmeAnalysis.technology_stack.map((item, index) => (
                      <li key={`${item.name}-${index}`}>
                        <strong>{item.name}</strong> — {item.description}
                        <small>README 근거: {item.source_excerpt}</small>
                      </li>
                    ))}</ul>
                  </section>
                  <section className="coach-readme-analysis-section">
                    <h3>프로젝트 흐름</h3>
                    <ol>{readmeAnalysis.project_flow.map((item, index) => (
                      <li key={index}>
                        {item.description}
                        <small>README 근거: {item.source_excerpt}</small>
                      </li>
                    ))}</ol>
                  </section>
                  <p className="coach-readme-caution">팀 README에 적힌 내용이며, 개인의 구현 범위나 숙련도를 확인한 결과는 아니에요.</p>
                  <small className="coach-readme-source">출처: <a href={readmeAnalysis.source_url} target="_blank" rel="noreferrer noopener">GitHub README</a> · {readmeAnalysis.readme_sha.slice(0, 7)}</small>
                </div>
              </article>
            )}

            {renderPreparationGuide("readme")}
            {renderPreparationChat("readme_review")}

            {showPreparationStage("jobs") && jobSearchStarted && submittedNcsIds && (resumeProfile || resumeSkipped) && (readmeAnalysis || readmeSkipped) && (saraminLoading ? <CoachLoadingCard className="coach-job-search-message" label="공고 검색" badge="공고 검색 중" title="웹에서 백엔드 공고를 찾고 마감 여부를 확인하고 있어요">
              지원 조건과 마감은 공고 원문에서 확인해 주세요.
            </CoachLoadingCard> : (
              <article className="coach-message coach-message-assistant coach-search-message coach-job-search-message" aria-label="공고 검색">
                <span className="coach-message-avatar" aria-hidden="true">✦</span>
                <div className="coach-search-results">
                  <strong>공고 검색</strong>
                  {newGraduateOnly && <p role="status">신입 지원 가능 공고만 표시 중 · 신입·경력무관 포함, 경력 조건 미확인 공고 제외</p>}
                  {saraminLoading ? (
                    <p role="status">웹에서 백엔드 공고를 찾고 마감 여부를 확인하고 있어요 <span className="coach-typing-dots" aria-hidden="true"><i /><i /><i /></span></p>
                  ) : saraminError ? (
                    <p role="alert">{saraminError}</p>
                  ) : saraminSearched && saraminRecommendations.length === 0 ? (
                    <p>현재 검색에서 확인된 백엔드 공고가 없어요.</p>
                  ) : null}
                  {!saraminLoading && saraminSearched && !saraminError && (
                    <div className="coach-job-source-browser">
                      <div className="coach-job-source-tabs" role="tablist" aria-label="채용 공고 사이트">
                        {sourceJobGroups.map((source, index) => (
                          <button
                            type="button" role="tab" key={source.domain}
                            id={`job-source-tab-${index}`} aria-controls={`job-source-panel-${index}`}
                            aria-selected={activeJobSource === source.domain}
                            tabIndex={activeJobSource === source.domain ? 0 : -1}
                            onClick={() => setActiveJobSource(source.domain)}
                            onKeyDown={(event) => {
                              let next = index;
                              if (event.key === "ArrowRight") next = (index + 1) % JOB_SOURCES.length;
                              else if (event.key === "ArrowLeft") next = (index + JOB_SOURCES.length - 1) % JOB_SOURCES.length;
                              else if (event.key === "Home") next = 0;
                              else if (event.key === "End") next = JOB_SOURCES.length - 1;
                              else return;
                              event.preventDefault();
                              setActiveJobSource(JOB_SOURCES[next].domain);
                              document.getElementById(`job-source-tab-${next}`)?.focus();
                            }}
                          >{source.name}<span>{source.jobs.length}</span></button>
                        ))}
                      </div>
                      {sourceJobGroups.map((source, index) => {
                        const jobs = source.jobs;
                        return (
                          <section className="coach-job-source-section" role="tabpanel" id={`job-source-panel-${index}`} aria-labelledby={`job-source-tab-${index}`} hidden={activeJobSource !== source.domain} aria-label={`${source.name} 공고`} key={source.domain}>
                            <h3>{source.name} 공고 <small>{jobs.length}개</small></h3>
                            {jobs.length === 0 ? <p>현재 검색에서 확인된 {source.name} 공고가 없어요.</p> : (
                              <div className="coach-job-result-list">
                                {jobs.map((job) => (
                                  <article className="coach-job-result" key={job.source_url}>
                                    <span>{job.company}</span>
                                    <strong>{job.title}</strong>
                                    <small>{job.experience} · {job.deadline ? `마감일 ${job.deadline}` : "채용 시 마감"}</small>
                                    <p className="coach-job-reason">추천 이유: {recommendationReason(job, Boolean(readmeAnalysis))}</p>
                                    <div>
                                      <a href={job.source_url} target="_blank" rel="noreferrer noopener">공고 원문 확인</a>
                                      <button
                                        type="button"
                                        disabled={analyzingRecommendedUrl !== null}
                                        onClick={() => analyzeRecommendedJobPosting(job)}
                                      >
                                        {analyzingRecommendedUrl === job.source_url ? "공고 검토 중..." : "공고 선택"}
                                      </button>
                                    </div>
                                  </article>
                                ))}
                              </div>
                            )}
                          </section>
                        );
                      })}
                    </div>
                  )}
                  {recommendedReviewError && <p role="alert">{recommendedReviewError}</p>}
                  {!saraminLoading && <div className="coach-search-retry"><button type="button" onClick={() => setSaraminRetryCount((count) => count + 1)}>다시 검색</button></div>}
                  <p>지원 조건과 마감은 공고 원문에서 확인해 주세요.</p>
                </div>
              </article>
            ))}

            {renderPreparationChat("jobs")}

            {chatMessages.map((message, index) => (
              <article className="coach-message coach-message-user coach-message-user-input" key={`${message}-${index}`}>
                <div>
                  <span>나</span>
                  <strong>{message}</strong>
                </div>
              </article>
            ))}

            {isChatRequestLoading && chatSearchRequested ? (
              <article className="coach-message coach-message-assistant coach-typing-message" role="status" aria-live="polite">
                <span className="coach-message-avatar" aria-hidden="true">✦</span>
                <div>
                  <strong>말해봄 코치</strong>
                  <span className="coach-typing-label">
                    {isAnalyzingRecruitment
                      ? "공고 원문을 분석하고 있어요"
                      : chatIntentLoading
                        ? "메시지를 이해하고 있어요"
                        : "공고를 찾고 있어요"}
                  </span>
                  <span className="coach-typing-dots" aria-label="입력 중">
                    <i /><i /><i />
                  </span>
                </div>
              </article>
            ) : null}

            {chatAssistantMessage
              && chatAssistantMessagePlacement === "before-results"
              && !isChatRequestLoading
              && !isAnalyzingRecruitment && (
              <article className="coach-message coach-message-assistant coach-message-reply" aria-live="polite">
                <span className="coach-message-avatar" aria-hidden="true">✦</span>
                <div>
                  <strong>말해봄 코치</strong>
                  <p>{chatAssistantMessage}</p>
                </div>
              </article>
            )}

            {!newGraduateOnly && chatSearchRequested && (hasSearchedAlio || hasSearchedPublicEmployment || hasSearchedMofe) && !isRecruitmentSearchLoading && (
              <article className="coach-message coach-message-assistant coach-search-message">
                <span className="coach-message-avatar" aria-hidden="true">✦</span>
                <div className="coach-search-results">
                  <strong>공고 검색 결과</strong>
                  <p>출처별로 최대 3건을 보여드려요. 분석 가능한 공고는 AI가 원문을 분석하고, 요구사항은 직접 선택할 수 있어요.</p>
                  {hasSearchedAlio && (
                    <section className="coach-provider-result-section" aria-label="ALIO 공공기관 채용 공고">
                      <header><strong>ALIO 공공기관 채용</strong><span>총 {alioTotalCount}건</span></header>
                      {alioResults.length === 0 ? <p className="coach-provider-empty">검색 결과가 없어요.</p> : (
                        <div className="coach-job-result-list">
                          {alioResults.slice(0, 3).map((recruitment) => (
                            <article className="coach-job-result" key={`alio-${recruitment.announcement_id}`}>
                              <span>{recruitment.company}</span>
                              <strong>{recruitment.title}</strong>
                              <small>
                                {[recruitment.location, recruitment.employment_type, recruitment.recruitment_type]
                                  .filter(Boolean)
                                  .join(" · ") || "세부 조건은 원문에서 확인"}
                              </small>
                              <div>
                                {recruitment.source_url && (
                                  <a href={recruitment.source_url} target="_blank" rel="noreferrer">원문 확인</a>
                                )}
                                <button
                                  type="button"
                                  disabled={!recruitment.source_url || isAnalyzingRecruitment}
                                  onClick={() => analyzeAlioJobPosting(recruitment)}
                                >
                                  이 공고 분석하기
                                </button>
                              </div>
                            </article>
                          ))}
                        </div>
                      )}
                    </section>
                  )}
                  {hasSearchedPublicEmployment && (
                    <section className="coach-provider-result-section" aria-label="인사혁신처 공공취업정보 공고">
                      <header><strong>인사혁신처 공공취업정보</strong><span>총 {publicEmploymentTotalCount}건</span></header>
                      {publicEmploymentResults.length === 0 ? <p className="coach-provider-empty">검색 결과가 없어요.</p> : (
                        <div className="coach-job-result-list">
                          {publicEmploymentResults.slice(0, 3).map((recruitment) => (
                            <article className="coach-job-result" key={`public-${recruitment.announcement_id}`}>
                              <span>{recruitment.company}</span>
                              <strong>{recruitment.title}</strong>
                              <small>
                                {[recruitment.location, recruitment.employment_type, recruitment.recruitment_type]
                                  .filter(Boolean)
                                  .join(" · ") || "세부 조건은 원문 분석 후 확인"}
                              </small>
                              <div>
                                <button
                                  type="button"
                                  disabled={isAnalyzingRecruitment}
                                  onClick={() => analyzePublicEmploymentJobPosting(recruitment)}
                                >
                                  이 공고 분석하기
                                </button>
                              </div>
                            </article>
                          ))}
                        </div>
                      )}
                    </section>
                  )}
                  {hasSearchedMofe && (
                    <section className="coach-provider-result-section" aria-label="재정경제부 공공기관 채용정보 공고">
                      <header><strong>재정경제부 공공기관 채용정보</strong><span>총 {mofeTotalCount}건</span></header>
                      {mofeResults.length === 0 ? <p className="coach-provider-empty">검색 결과가 없어요.</p> : (
                        <div className="coach-job-result-list">
                          {mofeResults.slice(0, 3).map((recruitment) => (
                            <article className="coach-job-result" key={`mofe-${recruitment.announcement_id}`}>
                              <span>{recruitment.company}</span>
                              <strong>{recruitment.title}</strong>
                              <small>
                                {[recruitment.location, recruitment.employment_type, recruitment.recruitment_type]
                                  .filter(Boolean)
                                  .join(" · ") || "세부 조건은 원문 분석 후 확인"}
                              </small>
                              <div>
                                {recruitment.source_url && (
                                  <a href={recruitment.source_url} target="_blank" rel="noreferrer">원문 확인</a>
                                )}
                                <button
                                  type="button"
                                  disabled={isAnalyzingRecruitment}
                                  onClick={() => analyzeMofeJobPosting(recruitment)}
                                >
                                  이 공고 분석하기
                                </button>
                              </div>
                            </article>
                          ))}
                        </div>
                      )}
                    </section>
                  )}
                </div>
              </article>
            )}

            {isAnalyzingRecruitment ? (
              <article className="coach-message coach-message-assistant coach-typing-message" role="status" aria-live="polite">
                <span className="coach-message-avatar" aria-hidden="true">✦</span>
                <div>
                  <strong>말해봄 코치</strong>
                  <span className="coach-typing-label">공고 원문을 분석하고 있어요</span>
                  <span className="coach-typing-dots" aria-label="입력 중">
                    <i /><i /><i />
                  </span>
                </div>
              </article>
            ) : null}

            {chatAssistantMessage
              && chatAssistantMessagePlacement === "after-results"
              && !isChatRequestLoading
              && !isAnalyzingRecruitment && (
              <article className="coach-message coach-message-assistant coach-message-reply" aria-live="polite">
                <span className="coach-message-avatar" aria-hidden="true">✦</span>
                <div>
                  <strong>말해봄 코치</strong>
                  <p>{chatAssistantMessage}</p>
                </div>
              </article>
            )}

            {selectedJob && (
              <article id={workspaceId("message", "job", selectedJob.id)} className="coach-message coach-message-user coach-selection-summary">
                <div>
                  <span>나 · 이번 연습</span>
                  <dl className="coach-selection-markdown">
                    <div>
                      <dt>## 공고</dt>
                      <dd><strong>{selectedJob.company}</strong><p>{selectedJob.title}</p></dd>
                    </div>
                    <div>
                      <dt>## 출처</dt>
                      <dd><p>{jobOriginLabel(selectedJob)}</p></dd>
                    </div>
                    <div id={workspaceId("message", "requirements", selectedJob.id, ...[...selectedRequirementIds].sort())}>
                      <dt>## 요구사항</dt>
                      <dd>
                        {selectedRequirements.length > 0 ? (
                          <><ul>{selectedRequirements.map((requirement) => <li key={requirement.id}>{requirement.text}</li>)}</ul><p>요구사항 {selectedRequirements.length}개를 연결했어요.</p></>
                        ) : <p>선택 중</p>}
                      </dd>
                    </div>
                    {selectedPracticeQuestion && <div>
                      <dt>## 질문</dt>
                      <dd><p>{selectedPracticeQuestion}</p></dd>
                    </div>}
                  </dl>
                </div>
              </article>
            )}

            {(selectedJob?.data_origin === "alio"
              || selectedJob?.data_origin === "public_job"
              || selectedJob?.data_origin === "mofe_job"
              || selectedJob?.data_origin === "private_job"
              || selectedJob?.data_origin === "reviewed") && (
              <article className="coach-message coach-message-assistant coach-requirement-message">
                <span className="coach-message-avatar" aria-hidden="true">✦</span>
                <div className="coach-requirement-picker">
                  <strong>이번 답변에 연결할 요구사항</strong>
                  <p>원문 근거를 확인한 항목만 보여드려요. 최대 2개까지 선택할 수 있어요.</p>
                  <div className="coach-requirement-list">
                    {selectedJob.requirements.map((requirement) => {
                      const checked = selectedRequirementIds.includes(requirement.id);
                      const disabled = !checked && selectedRequirementIds.length >= 2;
                      return (
                        <button
                          className={checked ? "coach-requirement-option is-selected" : "coach-requirement-option"}
                          key={requirement.id}
                          type="button"
                          disabled={disabled}
                          aria-pressed={checked}
                          onClick={() => toggleRequirement(requirement.id)}
                        >
                          <span>{checked ? "✓" : "+"}</span>
                          <span>
                            <strong>{requirement.text}</strong>
                            {requirement.source_excerpt && <small>원문 근거: {requirement.source_excerpt}</small>}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                  <small className="coach-requirement-count">{selectedRequirementIds.length} / 2개 선택</small>
                  {canContinueToQuestion && (
                    <button
                      className="coach-practice-start"
                      type="button"
                      onClick={openQuestionSelect}
                    >
                      이 공고로 질문 유형 고르기
                    </button>
                  )}
                </div>
              </article>
            )}

            {renderPreparationChat("requirements")}

            {view === "question-select" && !isInlineRerecord && (
              <article className="coach-message coach-message-assistant coach-message-reply">
                <span className="coach-message-avatar" aria-hidden="true">✦</span>
                <div><strong>말해봄 코치</strong><p>좋아요. 공고 맥락을 연결했어요. 어떤 질문으로 경험을 들려주고 싶은지 골라주세요.</p></div>
              </article>
            )}

            {view === "question-select" && !isInlineRerecord && (
              <article className="coach-message coach-message-assistant coach-question-message">
                <span className="coach-message-avatar" aria-hidden="true">✦</span>
                <div className="coach-question-picker">
                  <strong>답변할 질문 유형</strong>
                  <p>{questionTypeChosen ? "질문을 고른 뒤 녹음을 시작해 보세요." : "기본 질문 또는 직접 입력 질문을 골라주세요."}</p>
                  <div className="coach-question-type-list" role="tablist" aria-label="질문 유형">
                    <button
                      className={questionTypeChosen && questionType === "preset" ? "is-selected" : ""}
                      type="button"
                      role="tab"
                      aria-selected={questionTypeChosen && questionType === "preset"}
                      onClick={() => changeQuestionType("preset")}
                    >
                      기본 질문
                    </button>
                    <button
                      className={questionTypeChosen && questionType === "custom" ? "is-selected" : ""}
                      type="button"
                      role="tab"
                      aria-selected={questionTypeChosen && questionType === "custom"}
                      onClick={() => changeQuestionType("custom")}
                    >
                      내 질문
                    </button>
                  </div>

                  {questionTypeChosen && questionType === "preset" && (
                    <div className="coach-preset-picker" role="tabpanel">
                      <div className="coach-category-list" role="tablist" aria-label="직무 카테고리">
                        {INTERVIEW_QUESTION_CATEGORIES.map((category) => (
                          <button
                            className={selectedCategory.id === category.id ? "is-selected" : ""}
                            key={category.id}
                            type="button"
                            role="tab"
                            aria-selected={selectedCategory.id === category.id}
                            onClick={() => changeCategory(category.id)}
                          >
                            {category.label}
                          </button>
                        ))}
                      </div>
                      <div className="coach-question-list" aria-label={`${selectedCategory.label} 질문`}>
                        {selectedCategory.questions.map((question, index) => (
                          <button
                            className={selectedQuestion === index ? "is-selected" : ""}
                            key={question}
                            type="button"
                            aria-pressed={selectedQuestion === index}
                            onClick={() => setSelectedQuestion(index)}
                          >
                            <span>{String(index + 1).padStart(2, "0")}</span>
                            {question}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {questionTypeChosen && questionType === "custom" && (
                    <div className="coach-custom-question" role="tabpanel">
                      <label htmlFor="coach-custom-question">연습할 면접 질문</label>
                      <textarea
                        id="coach-custom-question"
                        value={customQuestion}
                        maxLength={200}
                        placeholder="질문을 직접 입력해 주세요."
                        aria-invalid={Boolean(customError)}
                        onChange={(event) => setCustomQuestion(event.target.value)}
                      />
                      <small>{customError || `${customQuestion.length} / 200`}</small>
                    </div>
                  )}
                </div>
              </article>
            )}

            {view === "question-select" && !activeAnswerAnalysis && !pendingWav && !isInlineRerecord && !hasCompletedAttempt(1) && questionTypeChosen && canStart && (
              <InlineChatRecorder
                questionText={selectedText}
                isRerecord={false}
                onPrepareQuestion={prepareQuestionForInlineRecording}
                onSubmit={handleInlineRecordingSubmit}
                onStateChange={setInlineRecordingActive}
              />
            )}

            {renderPreparationChat("questions")}

            {pendingWav && !isInlineRerecord && (
              <ChatAudioAttachment
                file={pendingWav.file}
                audioUrl={pendingWav.url}
                onDiscard={discardPendingWav}
                onSubmit={submitPendingWav}
              />
            )}

            {recordingPromptError && (
              <article className="coach-message coach-message-assistant coach-recording-message" role="alert">
                <span className="coach-message-avatar" aria-hidden="true">✦</span>
                <div className="coach-recording-panel"><strong>말해봄 코치</strong><p>{recordingPromptError}</p></div>
              </article>
            )}

            <div className="practice-main is-question-select coach-message-workspace">
        {view === "job-select" && !newGraduateOnly && (
          <section className="question-card question-select-card job-select-card card coach-message-card" aria-labelledby="job-title">
            <div className="question-heading">
              <p className="eyebrow">1단계 · 연습 조건</p>
              <h2 id="job-title">지원할 공고와 요구사항을 골라주세요.</h2>
              <p>검토된 공고 1개와 이번 답변에 연결할 요구사항 1~2개를 선택합니다.</p>
            </div>

            {!isLoggedIn ? (
              <div className="job-empty-state">
                <strong>공고를 선택하려면 로그인이 필요해요.</strong>
                <p>선택한 연습 조건은 본인의 24시간 연습 세션에만 저장됩니다.</p>
                <button className="start-button" type="button" onClick={onLogin}>로그인하기</button>
              </div>
            ) : jobLoading ? (
              <div className="job-empty-state" role="status">검토된 공고를 불러오고 있어요.</div>
            ) : (
              <>
                {jobError && <p className="error-message job-error" role="alert">{jobError}</p>}
                <section className="alio-search" aria-labelledby="alio-search-title">
                  <div className="alio-search-heading">
                    <div>
                      <h3 id="alio-search-title">ALIO에서 공고 검색</h3>
                      <p>AI가 HTTPS 원문을 읽어 요구사항과 근거를 추출해 이후 코칭에 사용해요.</p>
                    </div>
                    <span>검색 결과는 AI 분석 전 자료예요.</span>
                  </div>
                  <form className="alio-search-form" onSubmit={handleAlioSearch}>
                    <label className="sr-only" htmlFor="alio-query">ALIO 공고 제목 검색</label>
                    <input
                      id="alio-query"
                      type="search"
                      value={alioQuery}
                      maxLength={80}
                      placeholder="예: 백엔드, 정보통신, 개발"
                      onChange={(event) => setAlioQuery(event.target.value)}
                    />
                    <button type="submit" disabled={!alioQuery.trim() || alioLoading}>
                      {alioLoading ? "검색 중" : "검색"}
                    </button>
                  </form>
                  {alioError && <p className="error-message alio-error" role="alert">{alioError}</p>}
                  {hasSearchedAlio && (
                    <div className="alio-results" aria-live="polite">
                      <p className="alio-result-summary">
                        {alioTotalCount > 0 ? `총 ${alioTotalCount}건 중 최대 10건을 표시합니다.` : "검색 결과가 없습니다."}
                      </p>
                      {alioResults.map((recruitment) => (
                        <article className="alio-result" key={recruitment.announcement_id}>
                          <div>
                            <span>{recruitment.company}</span>
                            <strong>{recruitment.title}</strong>
                            <small>
                              {[recruitment.location, recruitment.employment_type, recruitment.recruitment_type]
                                .filter(Boolean)
                                .join(" · ") || "세부 조건은 원문에서 확인"}
                            </small>
                          </div>
                          <div className="alio-result-action">
                            <span>{recruitment.deadline ? `마감 ${recruitment.deadline}` : "마감일 미제공"}</span>
                            {recruitment.source_url && (
                              <a href={recruitment.source_url} target="_blank" rel="noreferrer">원문 보기</a>
                            )}
                            <button
                              type="button"
                              disabled={!recruitment.source_url || analyzingAnnouncementId !== null}
                              onClick={() => analyzeAlioJobPosting(recruitment)}
                            >
                              {analyzingAnnouncementId === recruitment.announcement_id
                                ? "AI 분석 중"
                                : "AI 분석하고 요구사항 선택"}
                            </button>
                          </div>
                        </article>
                      ))}
                    </div>
                  )}
                </section>
                <>
                  <p className="reviewed-job-caption">AI가 원문 근거와 함께 분석한 공고의 요구사항만 면접 코칭에 사용할 수 있어요.</p>
                  <div className="job-posting-list" aria-label="AI 분석 완료 채용공고">
                  {jobPostings.map((posting) => (
                    <button
                      className={selectedJobId === posting.id ? "job-posting-option is-selected" : "job-posting-option"}
                      key={posting.id}
                      type="button"
                      aria-pressed={selectedJobId === posting.id}
                      onClick={() => chooseJob(posting.id)}
                    >
                      <span>{posting.company}</span>
                      <strong>{posting.title}</strong>
                      <small>{posting.data_origin === "demo"
                        ? "연습용 가상 공고"
                        : posting.data_origin === "alio"
                          ? "AI 분석 완료 ALIO 공고"
                          : posting.data_origin === "public_job"
                            ? "AI 분석 완료 공공취업정보 공고"
                            : posting.data_origin === "mofe_job"
                              ? "AI 분석 완료 재정경제부 공공기관 채용정보 공고"
                              : posting.data_origin === "private_job"
                                ? "AI 검토 완료 민간 공고"
                          : `기준일 ${posting.captured_at.slice(0, 10)}`}</small>
                    </button>
                  ))}
                  </div>

                  {selectedJob && (
                  <>
                    <div className="job-source-meta">
                      <span>기준일 {selectedJob.captured_at.slice(0, 10)}</span>
                      <a href={selectedJob.source_url} target="_blank" rel="noreferrer">공고 출처 확인</a>
                    </div>
                    <fieldset className="requirement-picker">
                      <legend>관련 요구사항을 1~2개 선택해 주세요.</legend>
                      {selectedJob.requirements.map((requirement) => {
                        const checked = selectedRequirementIds.includes(requirement.id);
                        const disabled = !checked && selectedRequirementIds.length >= 2;
                        return (
                          <label className={checked ? "requirement-option is-selected" : "requirement-option"} key={requirement.id}>
                            <input
                              type="checkbox"
                              checked={checked}
                              disabled={disabled}
                              onChange={() => toggleRequirement(requirement.id)}
                            />
                            <span>
                              <strong>{requirement.code}</strong>{requirement.text}
                              {requirement.source_excerpt && <small>원문 근거: {requirement.source_excerpt}</small>}
                            </span>
                          </label>
                        );
                      })}
                      <small>{selectedRequirementIds.length} / 2개 선택</small>
                    </fieldset>
                  </>
                  )}

                  <div className="cta-area">
                    <button className="start-button" type="button" disabled={!canContinueToQuestion} onClick={openQuestionSelect}>
                      질문 선택으로 이동 <span aria-hidden="true">→</span>
                    </button>
                  </div>
                </>
              </>
            )}
          </section>
        )}

        {view === "question-select" && (
          <section
            className={`question-card question-select-card card${
              microphoneState !== "idle" ? " is-microphone-check" : ""
            } coach-message-card`}
            aria-labelledby={
              microphoneState === "idle" ? "question-title" : undefined
            }
            aria-label={microphoneState !== "idle" ? "마이크 확인" : undefined}
          >
            <button
              className="practice-back-button"
              type="button"
              onClick={returnToJobSelect}
            >
              ← 공고 선택으로
            </button>

            {microphoneState === "idle" && (
              <div className="question-heading">
                <p className="eyebrow">2단계 · 면접 질문</p>
                <h2 id="question-title">어떤 질문으로 시작할까요?</h2>
                <p>기본 질문을 고르거나, 연습하고 싶은 질문을 직접 입력해 주세요.</p>
                {selectedJob && (
                  <div className="selected-job-summary">
                    <div>
                      <strong>{selectedJob.title}</strong>
                      <p>연결할 요구사항: {selectedJob.requirements
                        .filter((requirement) => selectedRequirementIds.includes(requirement.id))
                        .map((requirement) => requirement.text)
                        .join(" · ")}</p>
                    </div>
                    <span>요구사항 {selectedRequirementIds.length}개 선택</span>
                  </div>
                )}
              </div>
            )}

            {microphoneState === "idle" ? (
              <>
                <div className="question-tabs" role="tablist" aria-label="질문 유형">
                  <button
                    className={questionType === "preset" ? "tab is-selected" : "tab"}
                    type="button"
                    role="tab"
                    aria-selected={questionType === "preset"}
                    onClick={() => changeQuestionType("preset")}
                  >
                    기본 질문
                  </button>
                  <button
                    className={questionType === "custom" ? "tab is-selected" : "tab"}
                    type="button"
                    role="tab"
                    aria-selected={questionType === "custom"}
                    onClick={() => changeQuestionType("custom")}
                  >
                    내 질문
                  </button>
                </div>

                {questionType === "preset" ? (
                  <div className="preset-panel" role="tabpanel">
                    <div
                      className="category-picker"
                      role="tablist"
                      aria-label="직무 카테고리"
                    >
                      {INTERVIEW_QUESTION_CATEGORIES.map((category) => (
                        <button
                          className={
                            selectedCategory.id === category.id
                              ? "category-button is-selected"
                              : "category-button"
                          }
                          key={category.id}
                          type="button"
                          role="tab"
                          aria-selected={selectedCategory.id === category.id}
                          onClick={() => changeCategory(category.id)}
                        >
                          {category.label}
                        </button>
                      ))}
                    </div>

                    <p className="panel-caption">
                      {selectedCategory.label} 질문 중 하나를 선택해주세요.
                    </p>

                    <div className="question-list">
                      {selectedCategory.questions.map((question, index) => (
                        <button
                          className={
                            selectedQuestion === index
                              ? "preset-question is-selected"
                              : "preset-question"
                          }
                          key={question}
                          type="button"
                          onClick={() => setSelectedQuestion(index)}
                          aria-pressed={selectedQuestion === index}
                        >
                          <span className="question-index">
                            {String(index + 1).padStart(2, "0")}
                          </span>
                          <span>{question}</span>
                          {index === 3 && <em className="core-question-badge">핵심 질문</em>}
                          <span className="checkmark" aria-hidden="true">
                            {selectedQuestion === index ? "✓" : ""}
                          </span>
                        </button>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="custom-panel" role="tabpanel">
                    <label className="panel-caption" htmlFor="custom-question">
                      연습하고 싶은 면접 질문을 입력해 주세요.
                    </label>
                    <textarea
                      id="custom-question"
                      value={customQuestion}
                      maxLength={200}
                      onChange={(event) => setCustomQuestion(event.target.value)}
                      placeholder="질문을 입력해 주세요."
                      aria-invalid={Boolean(customError)}
                      aria-describedby="custom-helper custom-error"
                    />
                    <div className="custom-meta">
                      <span id="custom-error" className="error-message">
                        {customError}
                      </span>
                      <span id="custom-helper" className="character-count">
                        {customQuestion.length} / 200
                      </span>
                    </div>
                  </div>
                )}

                <div className="cta-area">
                  {setupError && <p className="error-message setup-error" role="alert">{setupError}</p>}
                  <button
                    className="start-button"
                    type="button"
                    disabled={!canStart}
                    onClick={handleStart}
                  >
                    이 질문으로 시작하기 <span aria-hidden="true">→</span>
                  </button>
                </div>
              </>
            ) : (
              <MicrophoneCheckPanel
                state={microphoneState}
                question={selectedText}
                onRetry={checkMicrophone}
                onStart={handleRecordingStart}
              />
            )}
          </section>
        )}
            </div>
            {workspace.tasks.filter((task) => task.title === "면접 질문 선택").map((task) => <article key={task.id} id={task.messageId} className="coach-message coach-message-assistant"><span className="coach-message-avatar" aria-hidden="true">✦</span><div><strong>선택한 질문</strong><p>{task.text}</p></div></article>)}
            {completedAnswerAnalyses.map((completed) => <Fragment key={`${completed.result.analysisJobId ?? "analysis"}-${completed.attemptNo}`}>
              <article className="coach-message coach-message-user coach-audio-message">
                <div><span>나 · {completed.attemptNo}차 답변</span><strong>{completed.audio instanceof File ? "WAV 파일을 보냈어요." : "답변 녹음을 보냈어요."}</strong></div>
              </article>
              <CoachingChatMessages
                onWorkspaceReady={(revision, coaching) => { if (practiceGeneration === practiceGenerationRef.current) workspace.confirmed(revision, `${completed.attemptNo}차`, coaching, completed.contextEvidenceIds); }}
                onEvidenceSelect={workspace.navigate}
                question={completed.question}
                result={completed.result}
                stepLabel={`${completed.attemptNo}차` as "1차" | "2차"}
                nextLabel={completed.attemptNo === 1 ? "재녹음 하기" : "1·2차 답변 비교하기"}
                onNext={completed.attemptNo === 1 ? retryAnswer : showInlineComparison}
                onCoachingReady={() => { if (practiceGeneration === practiceGenerationRef.current) markCoachingReady(completed.attemptNo); }}
                comparisonOnly={completed.attemptNo === 2}
                showNextAction={completed.attemptNo === 2}
              />
              {completed.attemptNo === 1 && renderPreparationChat("first_coaching")}
            </Fragment>)}
            {activeAnswerAnalysis && <>
              <article className="coach-message coach-message-user coach-audio-message">
                <div><span>나 · {activeAnswerAnalysis.attemptNo}차 답변</span><strong>{activeAnswerAnalysis.audio instanceof File ? "WAV 파일을 보냈어요." : "답변 녹음을 보냈어요."}</strong></div>
              </article>
              <AnswerAnalysisChat
                question={activeAnswerAnalysis.question}
                attemptNo={activeAnswerAnalysis.attemptNo}
                audio={activeAnswerAnalysis.audio}
                practiceSessionId={activeAnswerAnalysis.practiceSessionId}
                isLoggedIn={isLoggedIn}
                onLogin={onLogin}
                onBack={() => setActiveAnswerAnalysis(null)}
                onComplete={completeAnswerAnalysis}
                showSubmittedAnswer={false}
              />
            </>}
            {isLoggedIn && inlineComparisonRequested && (() => {
              const first = completedAnswerAnalyses.find((completed) => completed.attemptNo === 1);
              const second = completedAnswerAnalyses.find((completed) => completed.attemptNo === 2);
              if (!first || !second) return null;
              return <Fragment>
                <article id="message:comparison" data-task-id="task:comparison" data-message-id="message:comparison" className="coach-message coach-message-user coach-message-user-input">
                  <div><span>나</span><strong>1·2차 답변 비교하기</strong></div>
                </article>
                <InlineAttemptComparisonChat
                  question={second.question}
                  firstResult={first.result}
                  secondResult={second.result}
                  resumeDraftMaterials={{ resumeProfile, resumeFile: resumeSourceFile, readmeAnalysis,
                    confirmedExperiences: preparation.confirmedExperiences.flatMap((experience) => experience.facts.map((fact) => fact.value)),
                    ncsLabels: ncsCompetencies?.options.filter((option) => (submittedNcsIds || selectedNcsIds).includes(option.id)).map((option) => option.label) ?? [] }}
                />
              </Fragment>;
            })()}
            {isInlineRerecord && view === "question-select" && !activeAnswerAnalysis && !pendingWav && retryRecordingOpen && retryQuestion && (
              <InlineChatRecorder
                questionText={retryQuestion.question}
                isRerecord
                onPrepareQuestion={prepareQuestionForInlineRecording}
                onSubmit={handleInlineRecordingSubmit}
                onStateChange={setInlineRecordingActive}
              />
            )}
            {isInlineRerecord && pendingWav && (
              <ChatAudioAttachment
                file={pendingWav.file}
                audioUrl={pendingWav.url}
                onDiscard={discardPendingWav}
                onSubmit={submitPendingWav}
              />
            )}
          </div>
          {!activeAnswerAnalysis && !inlineComparisonRequested && <form className="coach-composer" onSubmit={handleChatSubmit}>
            <input
              ref={wavUploadInputRef}
              className="coach-upload-input"
              type="file"
              accept="audio/wav,.wav"
              onChange={handleWavUpload}
            />
            <button
              className="coach-upload-button"
              type="button"
              aria-label="WAV 파일 업로드"
              title="WAV 파일 업로드"
              disabled={wavUploadPending || inlineRecordingActive || isChatRequestLoading || isAnalyzingRecruitment || (hasCompletedAttempt(1) && !retryRecordingOpen) || hasCompletedSecondAnswer}
              onClick={() => wavUploadInputRef.current?.click()}
            >
              <span aria-hidden="true">+</span>
            </button>
            <label className="sr-only" htmlFor="coach-chat-input">코치에게 메시지 입력</label>
            <input
              id="coach-chat-input"
              type="text"
              value={chatInput}
              maxLength={300}
              placeholder={coachingReadyAttempts.has(1) ? "코칭 내용에서 궁금한 점을 물어보세요." : "궁금한 점이나 추가 경력·경험을 입력해 보세요."}
              disabled={isChatRequestLoading || isAnalyzingRecruitment || preparation.loading || inlineRecordingActive || firstAnswerAwaitingCoaching}
              onChange={(event) => setChatInput(event.target.value)}
            />
            <button type="submit" disabled={!chatInput.trim() || isChatRequestLoading || isAnalyzingRecruitment || preparation.loading || inlineRecordingActive || firstAnswerAwaitingCoaching}>
              보내기 <span aria-hidden="true">↑</span>
            </button>
            {pendingPreparationStep && <button className="coach-next-stage-button" type="button"
              disabled={preparation.loading || readmeAnalysisLoading || isChatRequestLoading || isAnalyzingRecruitment}
              onClick={advancePreparationStep}>다음 단계</button>}
            {hasCompletedAttempt(1) && !hasCompletedSecondAnswer && <button
              className="coach-reanswer-button"
              type="button"
              disabled={!canStartSecondRecording || wavUploadPending || Boolean(pendingWav) || inlineRecordingActive || isChatRequestLoading || isAnalyzingRecruitment}
              onClick={retryAnswer}
            >
              재답변하기
            </button>}
          </form>}
        </section>

        <aside className="coach-context-panel" aria-label="현재 연습 정보">
          {preparation.confirmedError && <p role="alert">{preparation.confirmedError}</p>}
          <WorkspaceLibrary onChangeJob={changeSelectedJob} items={workspace.evidence} relatedEvidenceIds={workspace.tasks.find((task) => task.id === workspace.selectedTaskId)?.evidenceIds} selectedTaskId={workspace.selectedTaskId} selectedEvidenceId={workspace.selectedEvidenceId} onSelect={(item) => workspace.navigate(item.taskId, item.messageId, item.id)} />
          {activeAnswerAnalysis && <p className="coach-context-progress" role="status">답변을 분석하고 있어요.</p>}
          <div className="coach-context-tip">
            <span aria-hidden="true">✦</span>
            <p>답변에 실제로 말한 경험만 바탕으로 코칭해요.</p>
          </div>
        </aside>
      </main>
    </div>
  );
}

type MicrophoneCheckPanelProps = {
  state: Exclude<MicrophoneState, "idle">;
  question: string;
  onRetry: () => void | Promise<void>;
  onStart: () => void;
};

type InlineChatRecorderProps = {
  questionText: string;
  isRerecord: boolean;
  onPrepareQuestion: () => Promise<PracticeQuestion>;
  onSubmit: (question: PracticeQuestion, audio: Blob) => void;
  onStateChange: (isActive: boolean) => void;
};

function InlineChatRecorder({ questionText, isRerecord, onPrepareQuestion, onSubmit, onStateChange }: InlineChatRecorderProps) {
  const [state, setState] = useState<InlineRecordingState>("ready");
  const [elapsedMs, setElapsedMs] = useState(0);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [error, setError] = useState("");
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);
  const preparedQuestionRef = useRef<PracticeQuestion | null>(null);
  const elapsedMsRef = useRef(0);
  const startedAtRef = useRef(0);
  const audioUrlRef = useRef<string | null>(null);
  const failedRef = useRef(false);
  const recorderMountedRef = useRef(true);

  const stopStream = () => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  };

  const clearAudio = () => {
    if (audioUrlRef.current) URL.revokeObjectURL(audioUrlRef.current);
    audioUrlRef.current = null;
    setAudioUrl(null);
    setAudioBlob(null);
  };

  const fail = (message: string) => {
    stopStream();
    onStateChange(false);
    setError(message);
    setState("error");
  };

  useEffect(() => {
    if (state !== "recording") return undefined;
    const timer = window.setInterval(() => {
      const nextElapsed = Date.now() - startedAtRef.current;
      elapsedMsRef.current = nextElapsed;
      setElapsedMs(nextElapsed);
      if (nextElapsed >= MAX_RECORDING_MS) {
        const recorder = recorderRef.current;
        if (recorder && recorder.state !== "inactive") recorder.stop();
      }
    }, 100);
    return () => window.clearInterval(timer);
  }, [state]);

  useEffect(() => {
    recorderMountedRef.current = true;
    return () => {
      recorderMountedRef.current = false;
      const recorder = recorderRef.current;
      if (recorder && recorder.state !== "inactive") recorder.stop();
      stopStream();
      if (audioUrlRef.current) URL.revokeObjectURL(audioUrlRef.current);
    };
  }, []);

  const finishRecording = (recorder: MediaRecorder) => {
    stopStream();
    if (!recorderMountedRef.current) return;
    onStateChange(false);
    if (failedRef.current) return;
    if (elapsedMsRef.current < MIN_RECORDING_MS) {
      fail("답변은 5초 이상 녹음한 뒤 분석할 수 있어요.");
      return;
    }
    try {
      const nextAudio = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
      if (nextAudio.size === 0) throw new Error("Empty recording blob");
      clearAudio();
      const nextAudioUrl = createAudioUrl(nextAudio);
      audioUrlRef.current = nextAudioUrl;
      setAudioUrl(nextAudioUrl);
      setAudioBlob(nextAudio);
      setState("completed");
    } catch {
      fail("녹음 파일을 만들지 못했어요. 다시 시도해 주세요.");
    }
  };

  const startRecording = async () => {
    clearAudio();
    chunksRef.current = [];
    preparedQuestionRef.current = null;
    elapsedMsRef.current = 0;
    setElapsedMs(0);
    setError("");
    failedRef.current = false;
    onStateChange(true);
    setState("preparing");
    try {
      if (!navigator.mediaDevices?.getUserMedia) throw new Error("getUserMedia is not supported");
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (!recorderMountedRef.current) {
        stream.getTracks().forEach((track) => track.stop());
        return;
      }
      streamRef.current = stream;
      const preparedQuestion = await onPrepareQuestion();
      if (!recorderMountedRef.current) { stopStream(); return; }
      preparedQuestionRef.current = preparedQuestion;
      const mimeType = RECORDING_MIME_TYPES.find((candidate) => MediaRecorder.isTypeSupported(candidate));
      const recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
      recorderRef.current = recorder;
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };
      recorder.onerror = () => {
        failedRef.current = true;
        fail("녹음이 중단됐어요. 마이크 연결 상태를 확인해 주세요.");
      };
      recorder.onstop = () => finishRecording(recorder);
      recorder.start();
      startedAtRef.current = Date.now();
      setState("recording");
    } catch (cause) {
      if (!recorderMountedRef.current) return;
      const message = cause instanceof DOMException && (cause.name === "NotAllowedError" || cause.name === "PermissionDeniedError")
        ? "마이크 사용 권한을 허용한 뒤 다시 시도해 주세요."
        : cause instanceof Error && cause.message.includes("세션")
          ? cause.message
          : "녹음을 시작하지 못했어요. 마이크 연결 상태를 확인해 주세요.";
      fail(message);
    }
  };

  const stopRecording = () => {
    const recorder = recorderRef.current;
    if (!recorder || recorder.state === "inactive") return;
    recorder.stop();
  };

  const resetRecording = () => {
    clearAudio();
    setElapsedMs(0);
    elapsedMsRef.current = 0;
    setError("");
    setState("ready");
  };

  const submitRecording = () => {
    if (!audioBlob || !preparedQuestionRef.current) return;
    onSubmit(preparedQuestionRef.current, audioBlob);
  };

  if (state === "preparing") {
    return (
      <article className="coach-message coach-message-assistant coach-typing-message" role="status" aria-live="polite">
        <span className="coach-message-avatar" aria-hidden="true">✦</span>
        <div><strong>말해봄 코치</strong><span className="coach-typing-label">마이크와 연습을 준비하고 있어요</span><span className="coach-typing-dots" aria-label="입력 중"><i /><i /><i /></span></div>
      </article>
    );
  }

  if (state === "recording") {
    return (
      <article className="coach-message coach-message-user coach-audio-message coach-audio-recording" role="status" aria-live="polite">
        <div className="coach-recording-live-card">
          <img className="coach-state-mascot coach-recording-mascot" src={coachRecording} alt="마이크로 답변을 듣는 말해봄 코치" />
          <div className="coach-recording-live-copy">
            <span className="coach-recording-live-badge"><i className="coach-audio-record-dot" aria-hidden="true" />녹음 중</span>
            <strong className="coach-recording-live-title">답변을 듣고 있어요</strong>
            <div className="coach-audio-row"><strong>{formatRecordingTime(elapsedMs)} <small>/ 01:00</small></strong></div>
            <p>편하게 말씀해 주세요.</p>
          </div>
          <button className="coach-audio-stop" type="button" onClick={stopRecording}>■ 녹음 마치기</button>
        </div>
      </article>
    );
  }

  if (state === "completed") {
    return (
      <article className="coach-message coach-message-user coach-audio-message">
        <div>
          <span>나 · 답변 녹음</span>
          <div className="coach-audio-row"><i className="coach-audio-play" aria-hidden="true">▶</i><strong>{formatRecordingTime(elapsedMs)}</strong></div>
          {audioUrl && <audio className="coach-audio-player" controls src={audioUrl} />}
          <div className="coach-audio-actions"><button type="button" onClick={resetRecording}>다시 녹음</button><button type="button" onClick={submitRecording}>분석 시작</button></div>
        </div>
      </article>
    );
  }

  if (state === "error") {
    return (
      <article className="coach-message coach-message-assistant coach-recording-message" role="alert">
        <span className="coach-message-avatar" aria-hidden="true">✦</span>
        <div className="coach-recording-panel"><strong>말해봄 코치</strong><p>{error}</p><button className="coach-recording-button" type="button" onClick={() => void startRecording()}>다시 녹음하기</button></div>
      </article>
    );
  }

  return (
    <article className="coach-message coach-message-assistant coach-recording-message">
      <span className="coach-message-avatar" aria-hidden="true">✦</span>
      <div className="coach-recording-panel">
        <strong>말해봄 코치</strong>
        <p><b>{questionText}</b> 질문이에요. {isRerecord ? "앞선 피드백을 적용해 다시 답해볼까요? 녹음으로 답변해 주세요." : "채팅 안에서 바로 답변을 녹음해 보거나, 아래 + 버튼으로 WAV 파일을 올려보세요."}</p>
        <button className="coach-recording-button" type="button" onClick={() => void startRecording()}><span aria-hidden="true">🎙️</span> 녹음 시작하기</button>
      </div>
    </article>
  );
}

function ChatAudioAttachment({ file, audioUrl, onDiscard, onSubmit }: { file: File; audioUrl: string | null; onDiscard: () => void; onSubmit: () => void }) {
  return (
    <article className="coach-message coach-message-user coach-audio-message coach-wav-message">
      <div>
        <span>나 · WAV 파일</span>
        <div className="coach-audio-row"><i className="coach-audio-play" aria-hidden="true">▶</i><strong>{file.name}</strong></div>
        {audioUrl && <audio className="coach-audio-player" controls src={audioUrl} />}
        <div className="coach-audio-actions"><button type="button" onClick={onDiscard}>다른 파일</button><button type="button" onClick={onSubmit}>분석 시작</button></div>
      </div>
    </article>
  );
}

function MicrophoneCheckPanel({
  state,
  question,
  onRetry,
  onStart,
}: MicrophoneCheckPanelProps) {
  if (state === "checking") {
    return (
      <div className="microphone-panel is-centered" role="status" aria-live="polite">
        <span className="microphone-icon" aria-hidden="true">🎙️</span>
        <h3>마이크를 확인하고 있어요.</h3>
        <p>브라우저에서 마이크 사용을 허용해 주세요.</p>
        <span className="loading-indicator" aria-label="확인 중" />
        <button className="start-button" type="button" disabled>
          확인 중이에요...
        </button>
      </div>
    );
  }

  if (state === "granted") {
    return (
      <div className="microphone-panel" role="status" aria-live="polite">
        <span className="microphone-icon" aria-hidden="true">🎙️</span>
        <h3>마이크 준비가 완료됐어요.</h3>
        <p>이제 선택한 질문으로 연습을 시작할 수 있어요.</p>
        <div className="selected-question-preview">
          <span>선택한 질문</span>
          <strong>{question}</strong>
        </div>
        <button className="start-button" type="button" onClick={onStart}>
          연습 시작하기 <span aria-hidden="true">→</span>
        </button>
      </div>
    );
  }

  const isDenied = state === "denied";

  return (
    <div className="microphone-panel" role="alert">
      <span className="microphone-icon" aria-hidden="true">🎙️</span>
      <h3>
        {isDenied
          ? "마이크 사용 권한이 필요해요."
          : MOCK_ERROR_STATE === "mic-unavailable"
            ? "마이크를 사용할 수 없어요."
            : "마이크를 확인할 수 없어요."}
      </h3>
      <p>
        {isDenied
          ? MOCK_ERROR_STATE === "mic-permission-denied"
            ? "브라우저 설정에서 마이크 권한을 허용한 뒤 다시 시도해 주세요."
            : "답변을 녹음하려면 브라우저에서 마이크 사용을 허용해 주세요."
          : "마이크 연결 상태를 확인한 뒤 다시 시도해 주세요."}
      </p>
      {isDenied && (
        <small>브라우저 주소창의 마이크 설정에서도 권한을 변경할 수 있어요.</small>
      )}
      <button className="start-button" type="button" onClick={onRetry}>
        다시 확인하기
      </button>
    </div>
  );
}

export default PracticePage;
