export type StreamComplete = {
  type: "complete";
  audioUrl: string;
  durationMs: number;
  expiresAt: string;
};

export type QuestionTtsPlaybackHandle = {
  cancel: () => void;
  done: Promise<void>;
  result: StreamComplete | null;
};

type StreamStart = {
  type: "start";
  text: string;
  format: "pcm_s16le";
  sampleRate: number;
  channels: number;
};

type StreamAudio = {
  type: "audio";
  sequence: number;
  pcmBase64: string;
};

type StreamError = {
  type: "error";
  code: string;
  message: string;
};

type StreamEvent = StreamStart | StreamAudio | StreamComplete | StreamError;

type Options = {
  question: string;
  accessToken: string;
  audioContext: AudioContext;
  endpoint?: string;
  fetchImpl?: typeof fetch;
};

class QuestionTtsStreamError extends Error {
  constructor(code: string) {
    super(code);
    this.name = "QuestionTtsStreamError";
  }
}

export async function playQuestionTtsStream(options: Options): Promise<QuestionTtsPlaybackHandle> {
  const controller = new AbortController();
  const fetchImpl = options.fetchImpl ?? fetch;
  const response = await fetchImpl(options.endpoint ?? "/api/questions/tts/stream", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${options.accessToken}`,
      "Content-Type": "application/json",
      Accept: "application/x-ndjson",
    },
    body: JSON.stringify({ question: options.question }),
    signal: controller.signal,
  });

  if (!response.ok || !response.body) {
    controller.abort();
    throw new QuestionTtsStreamError("TTS_STREAM_UNAVAILABLE");
  }

  let expectedSequence = 0;
  let nextStartTime = options.audioContext.currentTime + 0.03;
  let started = false;
  let completed = false;
  let cancelled = false;
  let settled = false;
  let startResolved = false;
  const scheduledSources: AudioBufferSourceNode[] = [];
  let resolveDone: () => void = () => undefined;
  let rejectDone: (reason: Error) => void = () => undefined;
  let resolveStart: () => void = () => undefined;
  let rejectStart: (reason: Error) => void = () => undefined;
  const done = new Promise<void>((resolve, reject) => {
    resolveDone = resolve;
    rejectDone = reject;
  });
  const startReady = new Promise<void>((resolve, reject) => {
    resolveStart = resolve;
    rejectStart = reject;
  });
  const handle: QuestionTtsPlaybackHandle = {
    cancel: () => {
      if (settled) {
        return;
      }
      cancelled = true;
      controller.abort();
      for (const source of scheduledSources) {
        source.stop();
      }
      void options.audioContext.close();
      fail(new QuestionTtsStreamError("TTS_STREAM_CANCELLED"));
    },
    done,
    result: null,
  };

  function fail(error: Error): void {
    if (settled) {
      return;
    }
    settled = true;
    controller.abort();
    rejectDone(error);
    if (!startResolved) {
      rejectStart(error);
    }
  }

  function processEvent(event: StreamEvent): void {
    if (cancelled) {
      return;
    }
    if (event.type === "start") {
      if (started || event.format !== "pcm_s16le" || event.sampleRate !== 24000 || event.channels !== 1) {
        throw new QuestionTtsStreamError("STREAM_START_INVALID");
      }
      started = true;
      startResolved = true;
      resolveStart();
      return;
    }
    if (!started) {
      throw new QuestionTtsStreamError("STREAM_START_REQUIRED");
    }
    if (event.type === "audio") {
      if (event.sequence !== expectedSequence) {
        throw new QuestionTtsStreamError("AUDIO_SEQUENCE_INVALID");
      }
      const pcm16 = decodePcm16(event.pcmBase64);
      schedulePcm(options.audioContext, pcm16, scheduledSources, (durationSeconds) => {
        nextStartTime = Math.max(options.audioContext.currentTime + 0.03, nextStartTime);
        const scheduledTime = nextStartTime;
        nextStartTime += durationSeconds;
        return scheduledTime;
      });
      expectedSequence += 1;
      return;
    }
    if (event.type === "complete") {
      if (completed || expectedSequence === 0) {
        throw new QuestionTtsStreamError("STREAM_COMPLETE_INVALID");
      }
      completed = true;
      handle.result = event;
      settled = true;
      resolveDone();
      return;
    }
    throw new QuestionTtsStreamError("TTS_STREAM_ERROR");
  }

  void consumeNdjson(response.body, processEvent)
    .then(() => {
      if (!settled && !cancelled) {
        fail(new QuestionTtsStreamError(completed ? "TTS_STREAM_INVALID" : "STREAM_COMPLETE_REQUIRED"));
      }
    })
    .catch((error: unknown) => {
      if (!settled) {
        fail(error instanceof Error ? error : new QuestionTtsStreamError("TTS_STREAM_INVALID"));
      }
    });

  await startReady;
  return handle;
}

async function consumeNdjson(
  body: ReadableStream<Uint8Array>,
  onEvent: (event: StreamEvent) => void,
): Promise<void> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffered = "";
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }
      buffered += decoder.decode(value, { stream: true });
      buffered = processCompleteLines(buffered, onEvent);
    }
    buffered += decoder.decode();
    if (buffered.trim()) {
      onEvent(parseEvent(buffered));
    }
  } finally {
    reader.releaseLock();
  }
}

function processCompleteLines(buffered: string, onEvent: (event: StreamEvent) => void): string {
  const lines = buffered.split("\n");
  const incompleteLine = lines.pop() ?? "";
  for (const line of lines) {
    if (line.trim()) {
      onEvent(parseEvent(line));
    }
  }
  return incompleteLine;
}

function parseEvent(line: string): StreamEvent {
  let parsed: unknown;
  try {
    parsed = JSON.parse(line);
  } catch {
    throw new QuestionTtsStreamError("NDJSON_INVALID");
  }
  if (!parsed || typeof parsed !== "object" || !("type" in parsed)) {
    throw new QuestionTtsStreamError("STREAM_EVENT_INVALID");
  }
  return parsed as StreamEvent;
}

function decodePcm16(pcmBase64: string): Int16Array {
  if (!/^[A-Za-z0-9+/]*={0,2}$/.test(pcmBase64) || pcmBase64.length % 4 !== 0) {
    throw new QuestionTtsStreamError("PCM_BASE64_INVALID");
  }
  let decoded: string;
  try {
    decoded = atob(pcmBase64);
  } catch {
    throw new QuestionTtsStreamError("PCM_BASE64_INVALID");
  }
  if (!decoded.length || decoded.length % 2 !== 0) {
    throw new QuestionTtsStreamError("PCM16_INVALID");
  }
  const pcm16 = new Int16Array(decoded.length / 2);
  for (let index = 0; index < pcm16.length; index += 1) {
    const offset = index * 2;
    pcm16[index] = (decoded.charCodeAt(offset) | (decoded.charCodeAt(offset + 1) << 8));
  }
  return pcm16;
}

function schedulePcm(
  audioContext: AudioContext,
  pcm16: Int16Array,
  scheduledSources: AudioBufferSourceNode[],
  nextTime: (durationSeconds: number) => number,
): void {
  const audioBuffer = audioContext.createBuffer(1, pcm16.length, 24000);
  const samples = audioBuffer.getChannelData(0);
  for (let index = 0; index < pcm16.length; index += 1) {
    samples[index] = pcm16[index] / 32768;
  }
  const source = audioContext.createBufferSource();
  source.buffer = audioBuffer;
  source.connect(audioContext.destination);
  scheduledSources.push(source);
  source.start(nextTime(audioBuffer.duration));
}
