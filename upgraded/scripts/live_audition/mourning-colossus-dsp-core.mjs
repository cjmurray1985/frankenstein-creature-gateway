export const MAIN_PITCH_RATIO = 2 ** (-6 / 12);
// Practical deep variant: two additional semitones below the matched path.
export const DEEP_MAIN_PITCH_RATIO = 2 ** (-8 / 12);
export const SUB_PITCH_RATIO = 0.5;

function interpolate(buffer, position) {
  const size = buffer.length;
  const wrapped = ((position % size) + size) % size;
  const lower = Math.floor(wrapped);
  const upper = (lower + 1) % size;
  const fraction = wrapped - lower;
  return buffer[lower] * (1 - fraction) + buffer[upper] * fraction;
}

function hann(phase) {
  return 0.5 - 0.5 * Math.cos(2 * Math.PI * phase);
}

/**
 * Bounded-latency dual-grain pitch shifter. It preserves wall-clock duration:
 * each read head moves more slowly than the live write head, then jumps only
 * while its Hann window is silent. A second head masks that jump.
 */
export class MourningColossusPitchCore {
  constructor(sampleRate, grainMilliseconds = 72, options = {}) {
    this.sampleRate = sampleRate;
    this.mainPitchRatio = options.mainPitchRatio ?? MAIN_PITCH_RATIO;
    this.subPitchRatio = options.subPitchRatio ?? SUB_PITCH_RATIO;
    this.grainSize = Math.max(1024, Math.round(sampleRate * grainMilliseconds / 1000));
    this.baseDelay = this.grainSize + 256;
    this.buffer = new Float32Array(this.grainSize * 4 + 1024);
    this.writeIndex = 0;
    this.written = 0;
    this.mainPhase = 0;
    this.subPhase = 0;
  }

  reset() {
    this.buffer.fill(0);
    this.writeIndex = 0;
    this.written = 0;
    this.mainPhase = 0;
    this.subPhase = 0;
  }

  shifted(ratio, phase) {
    const other = (phase + 0.5) % 1;
    const first = interpolate(this.buffer,
      this.writeIndex - this.baseDelay - phase * this.grainSize);
    const second = interpolate(this.buffer,
      this.writeIndex - this.baseDelay - other * this.grainSize);
    return first * hann(phase) + second * hann(other);
  }

  process(input, mainOutput, subOutput) {
    for (let index = 0; index < mainOutput.length; index += 1) {
      const sample = input?.[index] || 0;
      this.buffer[this.writeIndex] = sample;
      this.writeIndex = (this.writeIndex + 1) % this.buffer.length;
      this.written += 1;

      if (this.written < this.baseDelay + this.grainSize) {
        mainOutput[index] = 0;
        subOutput[index] = 0;
        continue;
      }

      mainOutput[index] = this.shifted(this.mainPitchRatio, this.mainPhase);
      subOutput[index] = this.shifted(this.subPitchRatio, this.subPhase);
      this.mainPhase = (this.mainPhase + (1 - this.mainPitchRatio) / this.grainSize) % 1;
      this.subPhase = (this.subPhase + (1 - this.subPitchRatio) / this.grainSize) % 1;
    }
  }
}
