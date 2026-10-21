import { beforeEach, describe, expect, it } from "vitest";

import { playQuestionTtsStream } from "./questionTtsStream";

class FakeAudioBuffer {
  readonly samples: Float32Array;

  constructor(
    readonly numberOfChannels: number,
    readonly length: number,
    readonly sampleRate: number,
  ) {
    this.samples = new Float32Array(length);
  }

  getChannelData(channel: number): Float32Array {
    if (channel !== 0) {
      throw new Error("Only mono audio is supported in this fake.");
    }
    return this.samples;
  }

  get duration(): number {
    return this.length / this.sampleRate;
  }
}

class FakeAudioContext {
  currentTime = 0;
  readonly destination = {} as AudioDestinationNode;
  readonly starts: Array<{ time: number; buffer: FakeAudioBuffer }> = [];
  closed = false;

  createBuffer(channels: number, length: number, sampleRate: number): FakeAudioBuffer {
    return new FakeAudioBuffer(channels, length, sampleRate);
  }

  createBufferSource(): AudioBufferSourceNode {
    const context = this;
    const source = {
      buffer: null as unknown,
      connect: () => context.destination,
      disconnect: () => undefined,
      start: (time = 0) => {
        if (!(source.buffer instanceof FakeAudioBuffer)) {
          throw new Error("A buffer must be assigned before start.");
        }
        context.starts.push({ time, buffer: source.buffer });
      },
      stop: () => undefined,
    };
    return source as unknown as AudioBufferSourceNode;
  }

  async close(): Promise<void> {
    this.closed = true;
  }
}

function fakeNdjsonFetch(lines: string[], chunks: number[] = [1, 3, 2]): typeof fetch {
  return (async (_input: RequestInfo | URL, _init?: RequestInit) => {
    const encoded = new TextEncoder().encode(`${lines.join("\n")}\n`);
    const pieces: Uint8Array[] = [];
    let offset = 0;
    for (const size of chunks) {
      if (offset >= encoded.length) {
        break;
      }
      pieces.push(encoded.slice(offset, offset + size));
      offset += size;
    }
    if (offset < encoded.length) {
      pieces.push(encoded.slice(offset));
    }
    return new Response(
      new ReadableStream<Uint8Array>({
        start(controller) {
          for (const piece of pieces) {
            controller.enqueue(piece);
          }
          controller.close();
        },
      }),
      { status: 200, headers: { "Content-Type": "application/x-ndjson" } },
    );
  }) as typeof fetch;
}

describe("playQuestionTtsStream", () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  it("sends the bearer token, parses split NDJSON, and schedules PCM only after complete", async () => {
    const audio = new FakeAudioContext();
    const fetchImpl = fakeNdjsonFetch([
      '{"type":"start","text":"질문입니다.","format":"pcm_s16le","sampleRate":24000,"channels":1}',
      '{"type":"audio","sequence":0,"pcmBase64":"AAAAAA=="}',
      '{"type":"complete","audioUrl":"/api/audio/questions/audio-1","durationMs":4,"expiresAt":"2026-08-21T00:00:00Z"}',
    ]);
    const calls: RequestInit[] = [];
    const recordingFetch = ((input: RequestInfo | URL, init?: RequestInit) => {
      calls.push(init ?? {});
      return fetchImpl(input, init);
    }) as typeof fetch;

    const handle = await playQuestionTtsStream({
      question: "질문입니다.",
      accessToken: "test-token",
      audioContext: audio as unknown as AudioContext,
      fetchImpl: recordingFetch,
    });

    await handle.done;

    expect(calls).toHaveLength(1);
    expect(calls[0].headers).toMatchObject({
      Authorization: "Bearer test-token",
      "Content-Type": "application/json",
      Accept: "application/x-ndjson",
    });
    expect(audio.starts).toHaveLength(1);
    expect(audio.starts[0].time).toBeCloseTo(0.03);
    expect(audio.starts[0].buffer.samples).toEqual(new Float32Array([0, 0]));
    expect(handle.result?.audioUrl).toBe("/api/audio/questions/audio-1");
    expect(sessionStorage.getItem("ttsAudio")).toBeNull();
  });

  it("rejects the stream on a missing PCM sequence and never stores audio", async () => {
    const audio = new FakeAudioContext();
    const handle = await playQuestionTtsStream({
      question: "질문입니다.",
      accessToken: "test-token",
      audioContext: audio as unknown as AudioContext,
      fetchImpl: fakeNdjsonFetch([
        '{"type":"start","text":"질문입니다.","format":"pcm_s16le","sampleRate":24000,"channels":1}',
        '{"type":"audio","sequence":1,"pcmBase64":"AAAAAA=="}',
      ]),
    });

    await expect(handle.done).rejects.toThrow("AUDIO_SEQUENCE_INVALID");
    expect(sessionStorage.getItem("ttsAudio")).toBeNull();
    expect(handle.result).toBeNull();
  });

  it("cancels the fetch and closes the injected audio context without persistence", async () => {
    const audio = new FakeAudioContext();
    let signal: AbortSignal | undefined;
    const fetchImpl = ((_: RequestInfo | URL, init?: RequestInit) => {
      signal = init?.signal ?? undefined;
      return Promise.resolve(
        new Response(
          new ReadableStream<Uint8Array>({
            start(controller) {
              controller.enqueue(
                new TextEncoder().encode(
                  '{"type":"start","text":"질문입니다.","format":"pcm_s16le","sampleRate":24000,"channels":1}\n',
                ),
              );
            },
          }),
          { status: 200 },
        ),
      );
    }) as typeof fetch;

    const handle = await playQuestionTtsStream({
      question: "질문입니다.",
      accessToken: "test-token",
      audioContext: audio as unknown as AudioContext,
      fetchImpl,
    });
    handle.cancel();

    await expect(handle.done).rejects.toThrow("TTS_STREAM_CANCELLED");
    expect(signal?.aborted).toBe(true);
    expect(audio.closed).toBe(true);
    expect(sessionStorage.getItem("ttsAudio")).toBeNull();
  });
});
