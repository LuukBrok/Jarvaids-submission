/** Reframe arbitrary render quanta into exact 20 ms frames at 16 kHz. */
export class AudioFrames {
  constructor(onFrame) { this.onFrame = onFrame; this.buffer = new Float32Array(320); this.offset = 0; }
  push(input) {
    for (const sample of input) {
      this.buffer[this.offset++] = sample;
      if (this.offset === 320) {
        this.onFrame(this.buffer);
        this.buffer = new Float32Array(320); this.offset = 0;
      }
    }
  }
}
