import test from "node:test";
import assert from "node:assert/strict";
import { startCapture } from "../capture-audio.mjs";

test("chunks share a recording identity, and restarting creates a fresh command window", async t => {
  const navigatorDescriptor = Object.getOwnPropertyDescriptor(globalThis, "navigator");
  const originalContext = globalThis.AudioContext;
  const processors = [];
  Object.defineProperty(globalThis, "navigator", { configurable: true, value: { mediaDevices: {
    getUserMedia: async () => ({ getTracks: () => [{ stop() {} }] }) } } });
  globalThis.AudioContext = class {
    createMediaStreamSource() { return { connect() {}, disconnect() {} }; }
    createScriptProcessor() {
      const processor = { connect() {}, disconnect() {} };
      processors.push(processor);
      return processor;
    }
    close() { return Promise.resolve(); }
  };
  t.after(() => {
    if (navigatorDescriptor) Object.defineProperty(globalThis, "navigator", navigatorDescriptor);
    else delete globalThis.navigator;
    globalThis.AudioContext = originalContext;
  });
  const sends = [];
  const client = { intent: (operation, payload) => ({ operation, payload }),
    submit: async intent => { sends.push(intent); } };
  const frame = Float32Array.from({ length: 512 }, (_, i) => Math.sin(i * .2) * .3);
  const first = await startCapture(client);
  for (let i = 0; i < 400; i++) processors[0].onaudioprocess({ inputBuffer: { getChannelData: () => frame } });
  first.stop();
  assert(sends.length >= 2);
  const firstId = sends[0].payload.capture_id;
  assert(sends.every(send => send.payload.capture_id === firstId));
  const second = await startCapture(client);
  for (let i = 0; i < 200; i++) processors[1].onaudioprocess({ inputBuffer: { getChannelData: () => frame } });
  second.stop();
  assert.notEqual(sends.at(-1).payload.capture_id, firstId);
  for (const send of sends) {
    assert.match(send.payload.capture_id, /^[a-f0-9]{32}$/);
    assert(Number.isSafeInteger(send.payload.captured_at_ms));
    assert(send.payload.captured_at_ms >= 0);
    assert(Number.isSafeInteger(send.payload.captured_at_utc_ms));
    assert(Math.abs(send.payload.captured_at_utc_ms - Date.now()) < 60000);
  }
});
