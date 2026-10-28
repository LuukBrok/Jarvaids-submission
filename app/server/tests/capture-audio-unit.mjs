// Unit tests for the DOM-free half of capture-audio.mjs (the Chunker).
// The getUserMedia/AudioWorklet half (startCapture) needs a real browser and
// is not exercised here; see BUILD-STATUS.md for what that leaves unverified.
import test from "node:test";
import assert from "node:assert/strict";
import { Chunker, base64FromPcm16, HARD_CUT_MS, SILENCE_MS } from "../capture-audio.mjs";

const SAMPLE_RATE = 16000;
const FRAME_SAMPLES = (SAMPLE_RATE * 20) / 1000;

function speechFrame() {
  const frame = new Float32Array(FRAME_SAMPLES);
  for (let i = 0; i < frame.length; i++) frame[i] = Math.sin(i) * 0.5;
  return frame;
}
function silenceFrame() {
  return new Float32Array(FRAME_SAMPLES);
}

test("endpoints after the sentence pause budget", () => {
  const chunks = [];
  const chunker = new Chunker((chunk) => chunks.push(chunk));
  for (let i = 0; i < 40; i++) chunker.pushFrame(speechFrame()); // 800ms speech
  for (let i = 0; i < SILENCE_MS / 20; i++) chunker.pushFrame(silenceFrame()); // sentence pause silence
  assert.equal(chunks.length, 1);
  assert.equal(chunks[0].endedReason, "silence");
  assert.ok(chunks[0].durationMs >= 600);
});

test("hard cuts at HARD_CUT_MS even without silence", () => {
  const chunks = [];
  const chunker = new Chunker((chunk) => chunks.push(chunk));
  for (let i = 0; i < HARD_CUT_MS / 20; i++) chunker.pushFrame(speechFrame());
  assert.equal(chunks.length, 1);
  assert.equal(chunks[0].endedReason, "hard_cut");
  assert.equal(chunks[0].durationMs, HARD_CUT_MS);
});

test("never emits a chunk shorter than the 600ms minimum", () => {
  const chunks = [];
  const chunker = new Chunker((chunk) => chunks.push(chunk));
  for (let i = 0; i < 5; i++) chunker.pushFrame(speechFrame()); // 100ms speech
  for (let i = 0; i < 5; i++) chunker.pushFrame(silenceFrame()); // 100ms silence: 200ms total, below the 600ms floor
  assert.equal(chunks.length, 0, "a too-short chunk must not be flushed before the minimum duration");
});

test("a pause with nothing said never emits a chunk, however long it runs", () => {
  const chunks = [];
  const chunker = new Chunker((chunk) => chunks.push(chunk));
  for (let i = 0; i < 250; i++) chunker.pushFrame(silenceFrame()); // 5000ms of pure silence
  assert.equal(chunks.length, 0, "a window with no detected speech must not be sent at all");
});

test("a single brief noise blip does not count as speech", () => {
  const chunks = [];
  const chunker = new Chunker((chunk) => chunks.push(chunk));
  for (let i = 0; i < 100; i++) chunker.pushFrame(silenceFrame()); // 2000ms quiet
  chunker.pushFrame(speechFrame()); // one 20ms blip: a creak, a breath
  for (let i = 0; i < 150; i++) chunker.pushFrame(silenceFrame()); // 3000ms more quiet
  assert.equal(chunks.length, 0, "a single loud frame must not be mistaken for real speech");
});

test("sustained speech still counts even if it starts with a brief blip", () => {
  const chunks = [];
  const chunker = new Chunker((chunk) => chunks.push(chunk));
  for (let i = 0; i < 40; i++) chunker.pushFrame(speechFrame()); // 800ms real speech
  for (let i = 0; i < SILENCE_MS / 20; i++) chunker.pushFrame(silenceFrame()); // trailing silence: flush
  assert.equal(chunks.length, 1, "genuine sustained speech must still be sent");
});

test("still emits once speech resumes after a long pause", () => {
  const chunks = [];
  const chunker = new Chunker((chunk) => chunks.push(chunk));
  for (let i = 0; i < 100; i++) chunker.pushFrame(silenceFrame()); // 2000ms silence, discarded
  for (let i = 0; i < 40; i++) chunker.pushFrame(speechFrame()); // 800ms speech
  for (let i = 0; i < SILENCE_MS / 20; i++) chunker.pushFrame(silenceFrame()); // sentence pause trailing silence: flush
  assert.equal(chunks.length, 1);
  assert.equal(chunks[0].endedReason, "silence");
});

test("base64FromPcm16 round-trips byte length", () => {
  const pcm = new Int16Array([1, -1, 32767, -32768]);
  const encoded = base64FromPcm16(pcm);
  const decoded = Buffer.from(encoded, "base64");
  assert.equal(decoded.length, pcm.byteLength);
});

 test("a 400ms pause inside a sentence stays in the same audio chunk", () => {
  const chunks = [];
  const chunker = new Chunker(chunk => chunks.push(chunk));
  for (let i = 0; i < 40; i++) chunker.pushFrame(speechFrame());
  for (let i = 0; i < 20; i++) chunker.pushFrame(silenceFrame());
  assert.equal(chunks.length, 0);
  for (let i = 0; i < 40; i++) chunker.pushFrame(speechFrame());
  for (let i = 0; i < SILENCE_MS / 20; i++) chunker.pushFrame(silenceFrame());
  assert.equal(chunks.length, 1);
  assert.equal(chunks[0].durationMs, 3000);
});
