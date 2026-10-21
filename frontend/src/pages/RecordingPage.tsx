import { useEffect, useRef, useState } from "react";
import type { PracticeQuestion } from "./PracticePage";
import type { CoachAudioState } from "../mocks/analysisMock";
import { AppHeader } from "../navigation";
import { supabase } from "../api/supabaseAuth";
import { getPresetQuestionAudioUrl } from "../api/presetQuestionAudio";
import { MOCK_ERROR_STATE } from "../mocks/errorStateMock";
import { MOCK_QUESTION_TTS, type QuestionTtsMock, type QuestionTtsState } from "../mocks/questionTtsMock";
import { playQuestionTtsStream, type QuestionTtsPlaybackHandle } from "../services/questionTtsStream";
import { playBrowserQuestionTts, type BrowserQuestionTtsHandle } from "../services/browserQuestionTts";
import { API_BASE_URL } from "../config/apiBase";
import "../styles/recording-page.css";

type RecordingPageProps = {
  question: PracticeQuestion;
  attemptNo: 1 | 2;
  isRerecord?: boolean;
  coachAudioState?: CoachAudioState;
  onAnalysis: (attemptNo: 1 | 2, audio: Blob) => void;
  isLoggedIn: boolean;
  onLogin: () => void;
  autoStart?: boolean;
  initialAudioFile?: File;
};
type RecordingStatus = "ready" | "recording" | "paused" | "completed" | "error";
type RecordingError = "microphone" | "start" | "interrupted" | "blob" | "too-short" | "file";

const MAX_RECORDING_MS = 60_000;
const MIN_RECORDING_MS = 5_000;
const MIME_TYPES = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg;codecs=opus"];
const WAV_MIME_TYPES = new Set(["audio/wav", "audio/x-wav", "audio/wave", "audio/vnd.wave"]);

function formatTime(milliseconds: number) {
  const seconds = Math.floor(milliseconds / 1000);
  return `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
}

function createQuestionTtsMock(question: string): QuestionTtsMock {
  return {
    ...MOCK_QUESTION_TTS,
    originalText: question,
    normalizedText: question.trim().replace(/\s+/g, " "),
    state: "loading",
  };
}

export function getPresetQuestionPlaybackUrl(
  question: PracticeQuestion,
  apiBase?: string,
): string | null {
  if (question.questionType !== "preset" || !question.questionId) return null;
  return getPresetQuestionAudioUrl(question.questionId, apiBase);
}

export function getCustomQuestionTtsEndpoint(
  question: PracticeQuestion,
  apiBase = API_BASE_URL,
): string | null {
  if (question.questionType !== "custom") return null;
  return `${apiBase.replace(/\/$/, "")}/api/questions/tts/stream`;
}

export function getQuestionTtsStreamEndpoint(
  question: PracticeQuestion,
  apiBase = API_BASE_URL,
): string {
  return getCustomQuestionTtsEndpoint(question, apiBase)
    ?? `${apiBase.replace(/\/$/, "")}/api/questions/tts/stream`;
}

function RecordingPage({ question, attemptNo, isRerecord = false, coachAudioState = "unavailable", onAnalysis, isLoggedIn, onLogin, autoStart = false, initialAudioFile }: RecordingPageProps) {
  const [status, setStatus] = useState<RecordingStatus>("ready");
  const [questionTts, setQuestionTts] = useState<QuestionTtsMock>(() => createQuestionTtsMock(question.question));
  const [elapsedMs, setElapsedMs] = useState(0);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [errorType, setErrorType] = useState<RecordingError | null>(null);
  const [showLoginRequired, setShowLoginRequired] = useState(false);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const uploadInputRef = useRef<HTMLInputElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);
  const audioBlobRef = useRef<Blob | null>(null);
  const audioUrlRef = useRef<string | null>(null);
  const elapsedMsRef = useRef(0);
  const startedAtRef = useRef(0);
  const elapsedBeforeResumeRef = useRef(0);
  const recorderErrorRef = useRef(false);
  const questionTtsTimerRef = useRef<number | null>(null);
  const presetAudioRef = useRef<HTMLAudioElement | null>(null);
  const streamPlaybackRef = useRef<QuestionTtsPlaybackHandle | null>(null);
  const browserSpeechRef = useRef<BrowserQuestionTtsHandle | null>(null);
  const streamAudioContextRef = useRef<AudioContext | null>(null);
  const questionTtsRequestRef = useRef(0);

  const stopStream = () => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  };

  const revokeAudioUrl = () => {
    if (audioUrlRef.current) {
      URL.revokeObjectURL(audioUrlRef.current);
      audioUrlRef.current = null;
    }
    setAudioUrl(null);
  };

  const finishRecorder = () => {
    recorderRef.current = null;
    stopStream();
  };

  const setElapsed = (value: number) => {
    const nextValue = Math.min(value, MAX_RECORDING_MS);
    elapsedMsRef.current = nextValue;
    setElapsedMs(nextValue);
  };

  const stopQuestionTtsPlayback = () => {
    if (questionTtsTimerRef.current !== null) {
      window.clearTimeout(questionTtsTimerRef.current);
      questionTtsTimerRef.current = null;
    }
    if (presetAudioRef.current) {
      presetAudioRef.current.onplaying = null;
      presetAudioRef.current.onended = null;
      presetAudioRef.current.onerror = null;
      presetAudioRef.current.pause();
      presetAudioRef.current.currentTime = 0;
      presetAudioRef.current = null;
    }
    streamPlaybackRef.current?.cancel();
    streamPlaybackRef.current = null;
    browserSpeechRef.current?.cancel();
    browserSpeechRef.current = null;
    void streamAudioContextRef.current?.close();
    streamAudioContextRef.current = null;
  };

  const playBrowserFallback = (requestId: number) => {
    if (questionTtsRequestRef.current !== requestId) return;
    try {
      browserSpeechRef.current = playBrowserQuestionTts({
        text: question.question,
        onStart: () => {
          if (questionTtsRequestRef.current === requestId) {
            setQuestionTts((current) => ({ ...current, state: "playing" }));
          }
        },
        onEnd: () => {
          if (questionTtsRequestRef.current === requestId) {
            browserSpeechRef.current = null;
            setQuestionTts((current) => ({ ...current, state: "completed" }));
          }
        },
        onError: () => {
          if (questionTtsRequestRef.current === requestId) {
            browserSpeechRef.current = null;
            setQuestionTts((current) => ({ ...current, state: "error" }));
          }
        },
      });
    } catch {
      setQuestionTts((current) => ({ ...current, state: "error" }));
    }
  };

  const playPresetQuestionAudio = (url: string) => {
    stopQuestionTtsPlayback();
    const requestId = ++questionTtsRequestRef.current;
    const audio = new Audio(url);
    presetAudioRef.current = audio;
    setQuestionTts((current) => ({ ...current, state: "loading" }));

    const finish = (state: QuestionTtsState) => {
      if (questionTtsRequestRef.current !== requestId) return;
      audio.onplaying = null;
      audio.onended = null;
      audio.onerror = null;
      presetAudioRef.current = null;
      setQuestionTts((current) => ({ ...current, state }));
    };
    audio.onplaying = () => {
      if (questionTtsRequestRef.current === requestId) {
        setQuestionTts((current) => ({ ...current, state: "playing" }));
      }
    };
    audio.onended = () => finish("completed");
    audio.onerror = () => {
      finish("loading");
      playBrowserFallback(requestId);
    };
    void audio.play().catch(() => {
      finish("loading");
      playBrowserFallback(requestId);
    });
  };

  useEffect(() => {
    setQuestionTts(createQuestionTtsMock(question.question));
    stopQuestionTtsPlayback();
    questionTtsTimerRef.current = window.setTimeout(() => {
      setQuestionTts((current) => ({
        ...current,
        state: MOCK_ERROR_STATE === "question-tts-failed" || MOCK_ERROR_STATE === "question-tts-unavailable" ? "error" : "ready",
      }));
    }, 700);
    return () => {
      stopQuestionTtsPlayback();
    };
  }, [question.question]);

  useEffect(() => {
    if (status !== "recording") return undefined;
    const timer = window.setInterval(() => {
      const nextValue = elapsedBeforeResumeRef.current + (Date.now() - startedAtRef.current);
      if (nextValue >= MAX_RECORDING_MS) {
        setElapsed(MAX_RECORDING_MS);
        const recorder = recorderRef.current;
        if (recorder && recorder.state !== "inactive") recorder.stop();
        return;
      }
      setElapsed(nextValue);
    }, 100);
    return () => window.clearInterval(timer);
  }, [status]);

  useEffect(() => () => {
    stopStream();
    recorderRef.current = null;
    stopQuestionTtsPlayback();
    if (audioUrlRef.current) URL.revokeObjectURL(audioUrlRef.current);
  }, []);

  const handleRecorderStop = (recorder: MediaRecorder) => {
    finishRecorder();
    if (recorderErrorRef.current) return;
    if (elapsedMsRef.current < MIN_RECORDING_MS) {
      setErrorType("too-short");
      setStatus("error");
      return;
    }
    try {
      const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
      if (blob.size === 0) throw new Error("Empty recording blob");
      audioBlobRef.current = blob;
      revokeAudioUrl();
      const nextAudioUrl = URL.createObjectURL(blob);
      audioUrlRef.current = nextAudioUrl;
      setAudioUrl(nextAudioUrl);
      setStatus("completed");
    } catch (error) {
      console.error("[말해봄] 녹음 Blob 생성 실패", error);
      setErrorType("blob");
      setStatus("error");
    }
  };

  const startRecording = async () => {
    revokeAudioUrl();
    chunksRef.current = [];
    recorderErrorRef.current = false;
    setErrorType(null);
    setElapsed(0);
    elapsedBeforeResumeRef.current = 0;
    if (MOCK_ERROR_STATE === "recording-failed") {
      setErrorType("start");
      setStatus("error");
      return;
    }
    try {
      if (!navigator.mediaDevices?.getUserMedia) throw new Error("getUserMedia is not supported");
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      stream.getAudioTracks().forEach((track) => {
        track.onended = () => {
          const activeRecorder = recorderRef.current;
          if (!activeRecorder || activeRecorder.state === "inactive") return;
          console.error("[말해봄] 녹음 중 마이크 연결 종료");
          recorderErrorRef.current = true;
          setErrorType("interrupted");
          setStatus("error");
          activeRecorder.stop();
        };
      });
      const mimeType = MIME_TYPES.find((candidate) => MediaRecorder.isTypeSupported(candidate));
      const recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
      recorderRef.current = recorder;
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };
      recorder.onerror = (event) => {
        console.error("[말해봄] 녹음 중 오류", event);
        recorderErrorRef.current = true;
        stopStream();
        setErrorType("interrupted");
        setStatus("error");
      };
      recorder.onstop = () => handleRecorderStop(recorder);
      recorder.start();
      startedAtRef.current = Date.now();
      setStatus("recording");
    } catch (error) {
      console.error("[말해봄] 녹음 시작 실패", error);
      stopStream();
      setErrorType(error instanceof DOMException ? "microphone" : "start");
      setStatus("error");
    }
  };

  useEffect(() => {
    if (autoStart) void startRecording();
  }, [autoStart]);

  const stopRecording = () => {
    const recorder = recorderRef.current;
    if (recorder && recorder.state !== "inactive") recorder.stop();
    if (MOCK_ERROR_STATE === "too-short") {
      recorderErrorRef.current = true;
      stopStream();
      setElapsed(3000);
      setErrorType("too-short");
      setStatus("error");
    }
  };

  const pauseRecording = () => {
    const recorder = recorderRef.current;
    if (!recorder || recorder.state !== "recording") return;
    setElapsed(elapsedBeforeResumeRef.current + (Date.now() - startedAtRef.current));
    recorder.pause();
    setStatus("paused");
  };

  const resumeRecording = () => {
    const recorder = recorderRef.current;
    if (!recorder || recorder.state !== "paused") return;
    elapsedBeforeResumeRef.current = elapsedMsRef.current;
    startedAtRef.current = Date.now();
    recorder.resume();
    setStatus("recording");
  };

  const resetRecording = () => {
    const recorder = recorderRef.current;
    if (recorder && recorder.state !== "inactive") recorder.stop();
    stopStream();
    recorderRef.current = null;
    chunksRef.current = [];
    audioBlobRef.current = null;
    if (uploadInputRef.current) uploadInputRef.current.value = "";
    recorderErrorRef.current = false;
    revokeAudioUrl();
    setElapsed(0);
    setErrorType(null);
    setStatus("ready");
  };

  const handleWavUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;

    loadWavFile(file);
  };

  const loadWavFile = (file: File) => {
    const hasWavExtension = file.name.toLowerCase().endsWith(".wav");
    if (!hasWavExtension && !WAV_MIME_TYPES.has(file.type.toLowerCase())) {
      setErrorType("file");
      setStatus("error");
      return;
    }

    recorderRef.current = null;
    stopStream();
    revokeAudioUrl();
    audioBlobRef.current = file;
    audioUrlRef.current = URL.createObjectURL(file);
    setAudioUrl(audioUrlRef.current);
    setElapsed(0);
    setErrorType(null);
    setStatus("completed");
  };

  useEffect(() => {
    if (initialAudioFile) loadWavFile(initialAudioFile);
  }, [initialAudioFile]);

  const handleAnalysis = () => {
    if (!isLoggedIn) {
      setShowLoginRequired(true);
      return;
    }
    if (audioBlobRef.current) onAnalysis(attemptNo, audioBlobRef.current);
  };

  const playDynamicQuestionAudio = async () => {
    if (questionTts.state !== "ready" && questionTts.state !== "completed" && questionTts.state !== "error") return;
    stopQuestionTtsPlayback();
    const requestId = ++questionTtsRequestRef.current;
    setQuestionTts((current) => ({ ...current, state: "loading" }));
    try {
      const { data } = await supabase().auth.getSession();
      if (!data.session) throw new Error("로그인이 필요합니다.");
      const audioContext = new AudioContext();
      streamAudioContextRef.current = audioContext;
      await audioContext.resume();
      const playback = await playQuestionTtsStream({
        question: question.question,
        accessToken: data.session.access_token,
        audioContext,
        endpoint: getQuestionTtsStreamEndpoint(question),
      });
      if (questionTtsRequestRef.current !== requestId) {
        playback.cancel();
        return;
      }
      streamPlaybackRef.current = playback;
      setQuestionTts((current) => ({ ...current, state: "playing" }));
      void playback.done.then(
        () => {
          if (questionTtsRequestRef.current === requestId) setQuestionTts((current) => ({ ...current, state: "completed" }));
        },
        () => {
          if (questionTtsRequestRef.current === requestId) playBrowserFallback(requestId);
        },
      ).finally(() => {
        if (questionTtsRequestRef.current !== requestId) return;
        streamPlaybackRef.current = null;
        void audioContext.close();
        streamAudioContextRef.current = null;
      });
    } catch {
      if (questionTtsRequestRef.current === requestId) {
        void streamAudioContextRef.current?.close();
        streamAudioContextRef.current = null;
        playBrowserFallback(requestId);
      }
    }
  };

  const playQuestionTts = () => {
    const presetUrl = getPresetQuestionPlaybackUrl(question);
    if (presetUrl) {
      playPresetQuestionAudio(presetUrl);
      return;
    }
    void playDynamicQuestionAudio();
  };

  const retryQuestionTts = () => {
    playQuestionTts();
  };

  const errorTitle = errorType === "too-short" ? "조금만 더 답변해 주세요." : errorType === "file" ? "WAV 파일만 업로드할 수 있어요." : errorType === "microphone" ? "마이크를 사용할 수 없어요." : errorType === "interrupted" ? "녹음이 중단됐어요." : errorType === "blob" ? "녹음 파일을 만들 수 없어요." : "녹음을 시작할 수 없어요.";
  const errorDescription = errorType === "too-short" ? "답변은 5초 이상 녹음해야 분석할 수 있어요." : errorType === "file" ? "확장자가 .wav인 녹음 파일을 선택해 주세요." : errorType === "microphone" ? "마이크 권한과 연결 상태를 확인한 뒤 다시 시도해 주세요." : errorType === "interrupted" ? "마이크 연결 상태를 확인한 뒤 다시 시도해 주세요." : errorType === "blob" ? "잠시 후 다시 녹음해 주세요." : "마이크 권한과 연결 상태를 확인한 뒤 다시 시도해 주세요.";
  const statusLabel = status === "ready" ? "녹음 준비" : status === "recording" ? "녹음 중" : status === "paused" ? "일시정지" : status === "completed" ? "녹음 완료" : errorType === "too-short" ? "녹음 확인" : "녹음 오류";

  return (
    <div className="recording-page">
      <AppHeader />
      <main className="recording-main">
        <section className="recording-card" aria-labelledby="recording-title">
          {status !== "ready" && <p className="eyebrow">{statusLabel}</p>}
          <div className="recording-question">
            <span>선택한 질문</span>
            <div className="recording-question-body">
              <h1>{question.question}</h1>
              <QuestionTtsPanel state={questionTts.state} onPlay={playQuestionTts} onRetry={retryQuestionTts} />
            </div>
          </div>

          {status === "ready" && <div className="recording-state ready-state">
            <button
              className="recording-icon recording-icon-button"
              type="button"
              aria-label="마이크를 눌러 녹음 시작"
              onClick={() => void startRecording()}
            ><span className="on-air-mic" aria-hidden="true"><span className="on-air-grille" /><span className="on-air-label">ON AIR</span><span className="on-air-body" /><span className="on-air-stand" /><span className="on-air-base" /></span></button>
            <h2 id="recording-title">{isRerecord ? "피드백과 말하기 예시를 떠올리며 다시 말해볼까요?" : "준비되셨다면 편하게 시작해 주세요."}</h2>
            <p className="recording-limit">{isRerecord ? "완벽하게 바꾸려 하지 않아도 괜찮아요. 한 가지씩 적용해 보세요." : "답변은 5초 이상, 최대 60초까지 녹음할 수 있어요."}</p>
            {!isRerecord && <p className="recording-tip">완벽하게 말하려 하지 않아도 괜찮아요.<br />평소처럼 자연스럽게 답해 주세요.</p>}
            {isRerecord && <div className="rerecord-coach-note">{coachAudioState === "available" ? <button className="coach-example-button" type="button" onClick={() => console.log("[말해봄 mock] 정적 coach audio 재생")}>말하기 예시 다시 듣기</button> : coachAudioState === "unavailable" ? "이번에는 말하기 예시 없이 텍스트 안내를 참고해 다시 연습해 주세요." : "이번에는 텍스트 안내를 참고해 다시 연습해 주세요."}</div>}
            <button className="start-button recording-start-button" type="button" onClick={() => void startRecording()}>{isRerecord ? "재녹음 시작하기" : "녹음 시작하기"} <span aria-hidden="true">→</span></button>
            <input ref={uploadInputRef} className="recording-upload-input" type="file" accept="audio/wav,.wav" onChange={handleWavUpload} />
            <button className="secondary-button recording-upload-button" type="button" onClick={() => uploadInputRef.current?.click()}>WAV 파일 업로드</button>
            <p className="recording-upload-help">이미 녹음한 WAV 파일로도 분석할 수 있어요.</p>
          </div>}

          {(status === "recording" || status === "paused") && <div className="recording-state active-state" role="status" aria-live="polite">
            <div className={`external-recording-mic${status === "recording" ? " is-recording" : " is-paused"}`} aria-hidden="true"><span className="external-mic-head" /><span className="mic-wave mic-wave-left mic-wave-outer" /><span className="mic-wave mic-wave-left mic-wave-inner" /><span className="mic-wave mic-wave-right mic-wave-inner" /><span className="mic-wave mic-wave-right mic-wave-outer" /></div>
            <div className={`recording-icon is-active${status === "paused" ? " is-paused" : ""}`} aria-hidden="true"><span className="on-air-mic"><span className="on-air-grille" /><span className="on-air-label">ON AIR</span><span className="on-air-body" /><span className="on-air-stand" /><span className="on-air-base" /></span></div>
            <h2>{status === "recording" ? "답변을 녹음하고 있어요. 편하게 말씀해 주세요." : "녹음을 잠시 멈췄어요. 준비되면 이어서 말씀해 주세요."}</h2>
            <div className="timer">{formatTime(elapsedMs)} <span>/ 01:00</span></div>
            <div className="waveform" aria-hidden="true">{Array.from({ length: 24 }, (_, index) => <i key={index} style={{ height: `${18 + ((index * 17) % 30)}px` }} />)}</div>
            <div className="recording-actions">
              <button className="secondary-button" type="button" onClick={stopRecording}>그만하기</button>
              {status === "recording" ? <button className="start-button" type="button" onClick={pauseRecording}>일시정지</button> : <button className="start-button" type="button" onClick={resumeRecording}>이어서 녹음하기</button>}
            </div>
          </div>}

          {status === "completed" && <div className="recording-state completed-state">
            <div className="recording-icon" aria-hidden="true">✓</div>
            <h2>{audioBlobRef.current instanceof File ? "녹음 파일 업로드가 완료됐어요." : "답변 녹음이 완료됐어요."}</h2>
            <p className="recording-tip completed-description">{audioBlobRef.current instanceof File ? "업로드한 답변을 확인한 뒤 분석을 시작해 주세요." : "녹음한 답변을 확인한 뒤 분석을 시작해 주세요."}</p>
            {!(audioBlobRef.current instanceof File) && <p className="recording-limit">총 녹음 시간 {formatTime(elapsedMs)}</p>}
            {audioUrl && <audio className="recording-player" controls src={audioUrl} />}
            <div className="recording-actions"><button className="secondary-button" type="button" onClick={resetRecording}>다시 녹음</button><button className="start-button" type="button" onClick={handleAnalysis}>분석하기</button></div>
          </div>}

          {status === "error" && <div className="recording-state error-state" role="alert">
            <div className="recording-icon is-error" aria-hidden="true">!</div>
            <h2>{errorType === "too-short" ? "답변을 조금 더 길게 해주세요." : errorTitle}</h2>
            <p className="recording-tip">{MOCK_ERROR_STATE === "recording-failed" ? "잠시 후 다시 시도해 주세요." : errorType === "too-short" ? "분석을 위해 답변을 5초 이상 녹음해 주세요." : errorDescription}</p>
            <button className="start-button recording-start-button" type="button" onClick={resetRecording}>{MOCK_ERROR_STATE === "recording-failed" ? "다시 시도하기" : "다시 녹음하기"}</button>
          </div>}
        </section>
      </main>
      {showLoginRequired && <div className="recording-login-backdrop"><div className="recording-login-card"><h2>분석 결과를 확인하려면 로그인이 필요해요.</h2><p>로그인 후 연습 결과를 최대 24시간 동안 확인할 수 있어요.</p><div><button className="secondary-button" type="button" onClick={() => setShowLoginRequired(false)}>돌아가기</button><button className="start-button" type="button" onClick={onLogin}>로그인하기</button></div></div></div>}
    </div>
  );
}

function QuestionTtsPanel({ state, onPlay, onRetry }: { state: QuestionTtsState; onPlay: () => void; onRetry: () => void }) {
  if (state === "loading" || state === "idle") {
    return <div className="question-tts-panel" role="status" aria-live="polite"><span className="question-tts-message">질문 음성을 준비하고 있어요.</span><span className="question-tts-detail">잠시만 기다려 주세요.</span></div>;
  }

  if (state === "playing") {
    return <div className="question-tts-panel is-playing" role="status" aria-live="polite"><span className="question-tts-message">질문을 재생하고 있어요.</span></div>;
  }

  if (state === "error") {
    return <div className="question-tts-panel is-error" role="alert"><span className="question-tts-message">질문 음성을 준비하지 못했어요.</span><span className="question-tts-detail">잠시 후 다시 시도해 주세요.</span><button className="question-tts-button" type="button" onClick={onRetry}>다시 시도</button></div>;
  }

  if (state === "completed") {
    return <div className="question-tts-panel is-completed" role="status" aria-live="polite"><span className="question-tts-message">질문을 들었어요.</span><button className="question-tts-button" type="button" onClick={onPlay}>다시 듣기</button></div>;
  }

  return <div className="question-tts-panel" role="status"><button className="question-tts-button" type="button" onClick={onPlay}>질문 듣기</button></div>;
}

export default RecordingPage;
