/* Current teammate audio protocol, exposed without ES-module loading. */
(() => {
  const id = (size = 16) => Array.from(crypto.getRandomValues(new Uint8Array(size)), value => value.toString(16).padStart(2, '0')).join('');
  const json = async (url, options) => {
    const response = await fetch(url, { ...options, cache: 'no-store', credentials: 'omit' });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.error?.message || `Server returned ${response.status}`);
    return payload;
  };
  class Client {
    constructor({ baseUrl, sessionId, token }) { this.base = baseUrl; this.sessionId = sessionId; this.token = token; }
    get path() { return `${this.base}/api/sessions/${encodeURIComponent(this.sessionId)}`; }
    create({ ownerName, title, retentionSeconds }) {
      return json(`${this.base}/api/sessions`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ session_id: this.sessionId, owner_token: this.token, owner_name: ownerName, title, retention_seconds: retentionSeconds }) });
    }
    intent(operation, payload = {}, { controlSequence } = {}) { return { operation, payload, control_sequence: controlSequence, requestId: id() }; }
    submit(intent) {
      return json(`${this.path}/commands`, { method: 'POST', headers: { Authorization: `Bearer ${this.token}`, 'Content-Type': 'application/json', 'X-Request-ID': intent.requestId }, body: JSON.stringify({ operation: intent.operation, payload: intent.payload, control_sequence: intent.control_sequence }) });
    }
    snapshot() { return json(this.path, { headers: { Authorization: `Bearer ${this.token}` } }); }
    dispose() {}
  }
  const pcmBase64 = samples => {
    const bytes = new Uint8Array(samples.buffer, samples.byteOffset, samples.byteLength);
    let text = ''; for (let index = 0; index < bytes.length; index += 1) text += String.fromCharCode(bytes[index]);
    return btoa(text);
  };
  const pcm16 = samples => {
    const out = new Int16Array(samples.length);
    for (let index = 0; index < samples.length; index += 1) { const value = Math.max(-1, Math.min(1, samples[index])); out[index] = value < 0 ? value * 0x8000 : value * 0x7fff; }
    return out;
  };
  async function startCapture(client, { onError } = {}) {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, sampleRate: 16000, echoCancellation: true, noiseSuppression: false, autoGainControl: false } });
    const context = new AudioContext({ sampleRate: 16000 });
    const source = context.createMediaStreamSource(stream);
    const processor = context.createScriptProcessor(512, 1, 1);
    const captureId = id(); let carry = new Float32Array(0); let frames = []; let silence = 0; let total = 0; let noise = .002; let speechFrames = 0; let hasSpeech = false;
    const flush = reason => {
      if (!frames.length || !hasSpeech) { frames = []; silence = 0; total = 0; speechFrames = 0; hasSpeech = false; return; }
      const count = frames.reduce((sum, frame) => sum + frame.length, 0); const merged = new Float32Array(count); let at = 0;
      for (const frame of frames) { merged.set(frame, at); at += frame.length; }
      frames = []; silence = 0; total = 0; speechFrames = 0; hasSpeech = false;
      client.submit(client.intent('source.audio', { mime: 'audio/pcm16', base64: pcmBase64(pcm16(merged)), ended_reason: reason, capture_id: captureId, captured_at_ms: Math.round(performance.now()) })).catch(error => onError?.(error));
    };
    processor.onaudioprocess = event => {
      const incoming = event.inputBuffer.getChannelData(0); const merged = new Float32Array(carry.length + incoming.length); merged.set(carry); merged.set(incoming, carry.length); let at = 0;
      while (merged.length - at >= 320) {
        const frame = merged.slice(at, at + 320); at += 320; let energy = 0; for (const sample of frame) energy += sample * sample;
        const level = Math.sqrt(energy / frame.length); const speaking = level > noise * 3;
        if (speaking) { speechFrames += 1; if (speechFrames >= 3) hasSpeech = true; silence = 0; } else { speechFrames = 0; silence += 20; noise = noise * .99 + level * .01; }
        frames.push(frame); total += 20; if (total >= 6000) flush('hard_cut'); else if (silence >= 400 && total >= 600) flush('silence');
      }
      carry = merged.slice(at);
    };
    source.connect(processor); processor.connect(context.destination);
    return { stop() { if (total >= 600) flush('silence'); processor.disconnect(); source.disconnect(); context.close(); for (const track of stream.getTracks()) track.stop(); } };
  }
  window.JarvaidsTeammateAudio = { Client, startCapture };
})();
