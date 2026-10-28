import { base64FromPcm16 } from "./capture-audio.mjs";

/** Optional detector; source capture owns the microphone and calls pushFrame. */
export class WakewordController {
  constructor(client, {onDetection = () => {}, onState = () => {}, onError = () => {}} = {}) {
    this.client = client; this.onDetection = onDetection; this.onState = onState; this.onError = onError;
    this.epoch = 0; this.active = false; this.streamId = null; this.state = "off";
    this.removeListener = client.onState?.(() => this.stop());
  }
  setState(state) { this.state = state; this.onState(state); }
  async start() {
    if (this.active) return;
    const epoch = ++this.epoch;
    this.active = true; this.sequence = 0; this.lastDetection = null;
    this.queue = []; this.samples = new Int16Array(5120); this.offset = 0; this.sending = false;
    this.abort = new AbortController();
    this.setState("loading");
    try {
      const result = await this.client.wakewordStart({signal:this.abort.signal, timeoutMs:4500});
      if (epoch !== this.epoch) {
        this.client.wakewordStop(result.stream_id, {timeoutMs:1000}).catch(() => {});
        return;
      }
      if (result.sample_rate !== 16000 || result.batch_samples !== 5120 || result.next_sequence !== 0 ||
          typeof result.stream_id !== "string") throw new Error("Invalid detector response");
      this.streamId = result.stream_id;
      this.setState("waiting");
    } catch (error) { if (epoch === this.epoch) this.fail(error); }
  }
  pushFrame(frame) {
    if (!this.active || !this.streamId) return;
    for (const value of frame) {
      const v = Math.max(-1, Math.min(1, value));
      this.samples[this.offset++] = v < 0 ? v * 32768 : v * 32767;
      // Include the partial batch in the one-second queue bound.
      if (this.queue.length * 5120 + this.offset > 16000) {
        this.fail(new Error("Wake-word audio queue interrupted")); return;
      }
      if (this.offset === 5120) {
        this.queue.push(this.samples); this.samples = new Int16Array(5120); this.offset = 0;
        void this.sendNext();
      }
    }
  }
  async sendNext() {
    if (this.sending || !this.active || !this.queue.length) return;
    this.sending = true;
    const epoch = this.epoch, sequence = this.sequence++, streamId = this.streamId;
    const pcm = this.queue.shift();
    try {
      const result = await this.client.wakewordBatch(streamId, sequence, base64FromPcm16(pcm),
        {signal:this.abort.signal, timeoutMs:1000});
      if (epoch !== this.epoch) return;
      if (result.stream_id !== streamId || result.sequence !== sequence) throw new Error("Detector response mismatch");
      if (result.detection && !result.replayed && result.detection.id !== this.lastDetection) {
        if (typeof result.detection.id !== "string") throw new Error("Invalid detection");
        this.lastDetection = result.detection.id;
        this.setState("detected");
        this.onDetection(result.detection);
        clearTimeout(this.indicatorTimer);
        this.indicatorTimer = setTimeout(() => {
          if (epoch === this.epoch) this.setState("waiting");
        }, 2000);
      }
    } catch (error) { if (epoch === this.epoch) this.fail(error); }
    finally {
      if (epoch === this.epoch) { this.sending = false; void this.sendNext(); }
    }
  }
  fail(error) {
    this.stop();
    this.setState(error.code === "wakeword_unavailable" ? "unavailable" : "interrupted");
    this.onError(error);
  }
  stop() {
    this.active = false; this.epoch++; this.abort?.abort(); clearTimeout(this.indicatorTimer);
    this.queue = []; this.samples = null; this.offset = 0;
    const id = this.streamId; this.streamId = null;
    if (id) this.client.wakewordStop(id, {timeoutMs:1000}).catch(() => {});
    this.setState("off");
  }
  dispose() { this.stop(); this.removeListener?.(); }
}

/** Call unlock during the user's start click; a blocked chime never hides detection. */
export class WakewordChime {
  unlock() {
    try {
      this.context ??= new AudioContext();
      return this.context.resume().catch(() => {});
    } catch { return Promise.resolve(); }
  }
  play() {
    const context = this.context;
    if (!context || context.state !== "running") return;
    const oscillator = context.createOscillator(), gain = context.createGain();
    oscillator.frequency.value = 880;
    gain.gain.setValueAtTime(0, context.currentTime);
    gain.gain.linearRampToValueAtTime(0.06, context.currentTime + 0.015);
    gain.gain.linearRampToValueAtTime(0, context.currentTime + 0.16);
    oscillator.connect(gain); gain.connect(context.destination);
    oscillator.onended = () => { oscillator.disconnect(); gain.disconnect(); };
    oscillator.start(); oscillator.stop(context.currentTime + 0.18);
  }
  dispose() { this.context?.close().catch(() => {}); this.context = null; }
}
