/**
 * F1.1 live audio capture, client side: pipelines.md stages S1-S4.
 *
 * Scope cut (see decisions/decision-log.md): energy-threshold VAD, not the
 * Silero-class WASM VAD pipelines.md S3 specifies. A real VAD model needs a
 * WASM asset and tuning against room recordings neither of which this
 * session could do; an energy gate is the documented cheap fallback and is
 * named here so nobody mistakes it for the real thing.
 *
 * This module does S1 (getUserMedia, 16 kHz mono), S2 (high-pass, level),
 * S3 (energy VAD) and S4 (endpoint on 1000 ms trailing silence, hard cut at
 * 12 s), then hands one finished PCM16 chunk to `onChunk`. Everything after
 * that (S5 transport onward) is the caller's existing GenAIClient
 * intent/submit for the `source.audio` command; this module does not talk
 * to the network itself, so it stays testable without a server.
 */
import { newId } from "./client.mjs";

const SAMPLE_RATE = 16000;
const FRAME_MS = 20;
const FRAME_SAMPLES = (SAMPLE_RATE * FRAME_MS) / 1000;
// Give natural pauses inside a sentence time to resume before sending audio.
export const SILENCE_MS = 1000;
// pipelines.md S4 documents 12s. A real user's attempt to shorten this to 4s
// was reverted earlier in this project's history, but that attempt was
// entangled with a heavier model (medium), a since-fixed microphone
// auto-gain bug, and a since-removed context-priming feature all adding
// real load at the same time, so 4s itself was never cleanly tested on its
// own. Revisited now that the same user is running a lighter model (small)
// with real headroom to spare: a more conservative 6s, not the original
// 4s, to leave margin for the next surprise rather than repeat one.
export const HARD_CUT_MS = 6000;
const MIN_CHUNK_MS = 600;

/** High-pass at 80 Hz, one-pole. No model: pipelines.md S2. */
function highPass(frame, state, cutoffHz = 80) {
  const rc = 1 / (2 * Math.PI * cutoffHz);
  const dt = 1 / SAMPLE_RATE;
  const alpha = rc / (rc + dt);
  const out = new Float32Array(frame.length);
  let prevIn = state.prevIn, prevOut = state.prevOut;
  for (let i = 0; i < frame.length; i++) {
    const value = alpha * (prevOut + frame[i] - prevIn);
    prevIn = frame[i]; prevOut = value; out[i] = value;
  }
  state.prevIn = prevIn; state.prevOut = prevOut;
  return out;
}

function rms(frame) {
  let sum = 0;
  for (const v of frame) sum += v * v;
  return Math.sqrt(sum / frame.length);
}

function floatToPcm16(samples) {
  const out = new Int16Array(samples.length);
  for (let i = 0; i < samples.length; i++) {
    const clamped = Math.max(-1, Math.min(1, samples[i]));
    out[i] = clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff;
  }
  return out;
}

export function base64FromPcm16(pcm16) {
  const bytes = new Uint8Array(pcm16.buffer, pcm16.byteOffset, pcm16.byteLength);
  let binary = "";
  for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
  return typeof btoa === "function" ? btoa(binary) : Buffer.from(bytes).toString("base64");
}

/**
 * Pure, DOM-free chunker: feed it 20 ms Float32 frames, it calls onChunk with
 * {pcm16, durationMs, endedReason} when a chunk is ready. Kept separate from
 * the getUserMedia/AudioWorklet wiring below so it can be unit tested without
 * a browser (see tests/test_capture_audio.mjs).
 */
// A single loud frame (a creak, a breath, fan hum) can briefly cross the
// energy threshold without being real speech. A real user still saw chunks
// sent and rejected as "no speech" during a quiet room even after pure-
// silence windows stopped being sent, because one stray frame was enough to
// mark the whole window as having spoken content. Requiring this many
// consecutive speaking frames (60ms) before counting it as real speech
// filters a brief blip without meaningfully delaying real speech, which
// sustains far longer than that.
const SPEECH_DEBOUNCE_FRAMES = 3;

export class Chunker {
  #frames = []; #silenceMs = 0; #totalMs = 0; #hp = {prevIn: 0, prevOut: 0}; #hadSpeech = false;
  #consecutiveSpeaking = 0;
  #noiseFloor = 0.002; // guessed starting floor; adapted per S2's spec text
  constructor(onChunk, { noiseFloorMargin = 3 } = {}) {
    this.onChunk = onChunk;
    this.noiseFloorMargin = noiseFloorMargin;
  }
  pushFrame(frame) {
    const conditioned = highPass(frame, this.#hp);
    const level = rms(conditioned);
    const speaking = level > this.#noiseFloor * this.noiseFloorMargin;
    // Only adapt the floor from frames already judged quiet, so a sustained
    // voice cannot slowly drag the threshold up to meet itself.
    if (!speaking) { this.#noiseFloor = this.#noiseFloor * 0.99 + level * 0.01; this.#consecutiveSpeaking = 0; }
    else if (++this.#consecutiveSpeaking >= SPEECH_DEBOUNCE_FRAMES) this.#hadSpeech = true;
    this.#frames.push(conditioned);
    this.#totalMs += FRAME_MS;
    if (speaking) this.#silenceMs = 0; else this.#silenceMs += FRAME_MS;
    if (this.#totalMs >= HARD_CUT_MS) { this.#flush("hard_cut"); return; }
    if (this.#silenceMs >= SILENCE_MS && this.#totalMs >= MIN_CHUNK_MS) { this.#flush("silence"); return; }
  }
  #flush(endedReason) {
    // A window with no speech in it at all (a pause with nothing said) has
    // nothing worth sending: without this, a silent room produces a fresh
    // "silence" chunk roughly every MIN_CHUNK_MS forever, which a real
    // user's server-side backlog cap then had to turn away one by one,
    // flooding the transcript with 'Catching up' markers for a pause that
    // was, correctly, nothing being said.
    const hadSpeech = this.#hadSpeech;
    if (!this.#frames.length || !hadSpeech) {
      this.#frames = []; this.#silenceMs = 0; this.#totalMs = 0; this.#hadSpeech = false; this.#consecutiveSpeaking = 0;
      return;
    }
    const total = this.#frames.reduce((n, f) => n + f.length, 0);
    const merged = new Float32Array(total);
    let offset = 0;
    for (const f of this.#frames) { merged.set(f, offset); offset += f.length; }
    const pcm16 = floatToPcm16(merged);
    const durationMs = this.#totalMs;
    this.#frames = []; this.#silenceMs = 0; this.#totalMs = 0; this.#hadSpeech = false; this.#consecutiveSpeaking = 0;
    this.onChunk({ pcm16, durationMs, endedReason });
  }
  /** Flush whatever is buffered, e.g. on capture stop, so trailing speech is not lost. */
  flushRemaining() {
    if (this.#totalMs >= MIN_CHUNK_MS) this.#flush("silence");
    else { this.#frames = []; this.#silenceMs = 0; this.#totalMs = 0; this.#hadSpeech = false; this.#consecutiveSpeaking = 0; }
  }
}

/**
 * Browser wiring: getUserMedia + AudioWorklet, feeding a Chunker, submitting
 * finished chunks as `source.audio` commands through an existing
 * GenAIClient. Consent gate: this function must not be called before
 * `consent.acknowledge` and `session.activate` have succeeded; it does not
 * re-check that itself; the server enforces it (F6.1) and refuses
 * capture_inactive if a caller gets the order wrong.
 */
export async function startCapture(client, { onError, onFrame } = {}) {
  const captureId = newId();
  if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
    throw new Error("getUserMedia is unavailable in this environment.");
  }
  const stream = await navigator.mediaDevices.getUserMedia({
    // autoGainControl defaults to true in most browsers and normalises loud
    // and quiet sound to similar volume, which is directly at odds with
    // Chunker's energy-threshold VAD: it needs real speech to read
    // meaningfully louder than background noise, not levelled out. A real
    // user's build produced nothing but MIN_CHUNK_MS floor chunks (every
    // single one exactly 600ms) because of exactly this: the VAD never saw
    // speech as louder than "silence" once the browser had normalised both.
    audio: { channelCount: 1, sampleRate: SAMPLE_RATE, echoCancellation: false, noiseSuppression: false, autoGainControl: false },
  });
  const context = new AudioContext({ sampleRate: SAMPLE_RATE });
  const source = context.createMediaStreamSource(stream);
  // createScriptProcessor only accepts a power-of-two buffer size; FRAME_SAMPLES
  // (320, i.e. 20 ms at 16 kHz) is not one, so pull audio in 512-sample blocks
  // and re-slice it into FRAME_SAMPLES pieces below, so Chunker still sees the
  // fixed 20 ms frames its silence/hard-cut timing (FRAME_MS) assumes.
  const WORKLET_BUFFER_SAMPLES = 512;
  const processor = context.createScriptProcessor(WORKLET_BUFFER_SAMPLES, 1, 1);
  let carry = new Float32Array(0);
  const chunker = new Chunker(async ({ pcm16, durationMs, endedReason }) => {
    const capturedAtMs = Math.round(performance.now());
    try {
      const intent = client.intent("source.audio", {
        mime: "audio/pcm16",
        base64: base64FromPcm16(pcm16),
        ended_reason: endedReason,
        capture_id: captureId,
        captured_at_ms: capturedAtMs,
        captured_at_utc_ms: Date.now(),
      });
      // A real transcriber serialises one chunk at a time on the server
      // (genai_server/service.py's transcription_lock, since concurrent ASR
      // calls thrash a CPU rather than speeding anything up), so a chunk
      // submitted while others are queued ahead of it waits for all of
      // them, not just its own transcription. The default 10s client
      // timeout is tuned for ordinary commands, not this one.
      await client.submit(intent, { timeoutMs: 45000 });
    } catch (error) {
      // F6.4: a failed submit must be visible, never a silent drop of what
      // was said. The caller renders this as a queue/gap indicator.
      onError?.(error, { durationMs, endedReason });
    }
  });
  processor.onaudioprocess = (event) => {
    const incoming = event.inputBuffer.getChannelData(0);
    const merged = new Float32Array(carry.length + incoming.length);
    merged.set(carry); merged.set(incoming, carry.length);
    let offset = 0;
    while (merged.length - offset >= FRAME_SAMPLES) {
      const frame = merged.subarray(offset, offset + FRAME_SAMPLES);
      onFrame?.(frame);
      chunker.pushFrame(frame);
      offset += FRAME_SAMPLES;
    }
    carry = merged.slice(offset);
  };
  source.connect(processor); processor.connect(context.destination);
  return {
    stop() {
      chunker.flushRemaining();
      processor.disconnect(); source.disconnect(); context.close();
      for (const track of stream.getTracks()) track.stop();
    },
  };
}
