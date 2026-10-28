import { base64FromPcm16 } from "../server/capture-audio.mjs";

export async function recordVoiceSample({ signal, durationMs = 6000, onReady = () => {} } = {}) {
  if (signal?.aborted) throw new DOMException("Recording cancelled", "AbortError");
  const stream = await navigator.mediaDevices.getUserMedia({ audio: {
    channelCount: 1, sampleRate: 16000, echoCancellation: false,
    noiseSuppression: false, autoGainControl: false } });
  let context, source, processor;
  const frames = [];
  try {
    if (signal?.aborted) throw new DOMException("Recording cancelled", "AbortError");
    context = new AudioContext({ sampleRate: 16000 });
    await context.resume();
    source = context.createMediaStreamSource(stream);
    processor = context.createScriptProcessor(512, 1, 1);
    processor.onaudioprocess = event => frames.push(event.inputBuffer.getChannelData(0).slice());
    source.connect(processor); processor.connect(context.destination);
    onReady();
    await new Promise((resolve, reject) => {
      const cancel = () => { clearTimeout(timer); reject(new DOMException("Recording cancelled", "AbortError")); };
      const timer = setTimeout(() => { signal?.removeEventListener("abort", cancel); resolve(); }, durationMs);
      signal?.addEventListener("abort", cancel, { once: true });
    });
  } finally {
    processor?.disconnect(); source?.disconnect(); context?.close();
    for (const track of stream.getTracks()) track.stop();
  }
  const pcm = new Int16Array(frames.reduce((count, frame) => count + frame.length, 0));
  let offset = 0;
  for (const frame of frames) for (const value of frame) {
    const clamped = Math.max(-1, Math.min(1, value));
    pcm[offset++] = clamped < 0 ? clamped * 32768 : clamped * 32767;
  }
  return base64FromPcm16(pcm);
}

/** The enrolled voices: one row each, the name in Body and what kind of
 * profile it is in Small, so a test profile is never mistaken for a real
 * voice match. */
export function renderSpeakers(snapshot) {
  const list = document.getElementById("speaker-list");
  list.textContent = "";
  const profiles = snapshot.records.filter(record => record.kind === "speaker_profile");
  if (!profiles.length) {
    const empty = document.createElement("p");
    empty.className = "t-small speaker-empty";
    empty.textContent = "No voices enrolled yet. Audio is attributed to this microphone's participant.";
    list.append(empty);
    return;
  }
  for (const profile of profiles) {
    const row = document.createElement("p");
    row.className = "speaker-row";
    const name = document.createElement("span");
    name.className = "t-body speaker-name";
    name.textContent = profile.data.name;
    const kind = document.createElement("span");
    kind.className = "t-small speaker-kind";
    kind.textContent = profile.data.provenance?.synthetic
      ? " · Test profile, no real voice matching" : " · Voice profile enrolled";
    row.append(name, kind);
    list.append(row);
  }
}
