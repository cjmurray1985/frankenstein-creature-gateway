import test from 'node:test';
import assert from 'node:assert/strict';
import {
  DEEP_MAIN_PITCH_RATIO,
  MourningColossusPitchCore,
  MAIN_PITCH_RATIO,
  SUB_PITCH_RATIO,
} from './mourning-colossus-dsp-core.mjs';

function spectralMagnitude(samples, sampleRate, frequency, start) {
  let real = 0;
  let imaginary = 0;
  for (let index = start; index < samples.length; index += 1) {
    const phase = 2 * Math.PI * frequency * index / sampleRate;
    real += samples[index] * Math.cos(phase);
    imaginary -= samples[index] * Math.sin(phase);
  }
  return Math.hypot(real, imaginary);
}

function strongestFrequency(samples, sampleRate, start, low = 70, high = 230) {
  let result = {frequency: 0, magnitude: 0};
  for (let frequency = low; frequency <= high; frequency += 1) {
    const magnitude = spectralMagnitude(samples, sampleRate, frequency, start);
    if (magnitude > result.magnitude) result = {frequency, magnitude};
  }
  return result.frequency;
}

test('streaming processor lowers pitch without extending the output timeline', () => {
  const sampleRate = 48000;
  const length = sampleRate * 2;
  const input = new Float32Array(length);
  const main = new Float32Array(length);
  const sub = new Float32Array(length);
  for (let index = 0; index < length; index += 1) {
    input[index] = 0.5 * Math.sin(2 * Math.PI * 220 * index / sampleRate);
  }

  const processor = new MourningColossusPitchCore(sampleRate);
  for (let offset = 0; offset < length; offset += 128) {
    processor.process(
      input.subarray(offset, offset + 128),
      main.subarray(offset, offset + 128),
      sub.subarray(offset, offset + 128),
    );
  }

  assert.equal(main.length, input.length);
  assert.equal(sub.length, input.length);
  assert.ok(Math.abs(strongestFrequency(main, sampleRate, sampleRate) - 220 * MAIN_PITCH_RATIO) < 2);
  assert.ok(Math.abs(strongestFrequency(sub, sampleRate, sampleRate) - 220 * SUB_PITCH_RATIO) < 2);
  assert.ok((processor.baseDelay + processor.grainSize) / sampleRate < 0.16);
});

test('deep variant lowers the main voice two additional semitones', () => {
  const sampleRate = 48000;
  const length = sampleRate * 2;
  const input = new Float32Array(length);
  const main = new Float32Array(length);
  const sub = new Float32Array(length);
  for (let index = 0; index < length; index += 1) {
    input[index] = 0.5 * Math.sin(2 * Math.PI * 220 * index / sampleRate);
  }
  const processor = new MourningColossusPitchCore(sampleRate, 72, {
    mainPitchRatio: DEEP_MAIN_PITCH_RATIO,
  });
  for (let offset = 0; offset < length; offset += 128) {
    processor.process(
      input.subarray(offset, offset + 128),
      main.subarray(offset, offset + 128),
      sub.subarray(offset, offset + 128),
    );
  }
  assert.ok(Math.abs(strongestFrequency(main, sampleRate, sampleRate) - 220 * DEEP_MAIN_PITCH_RATIO) < 2);
});

test('reset clears buffered speech before a replacement stream', () => {
  const processor = new MourningColossusPitchCore(48000);
  const input = new Float32Array(8192).fill(0.5);
  const main = new Float32Array(input.length);
  const sub = new Float32Array(input.length);
  processor.process(input, main, sub);
  assert.ok(main.some(sample => sample !== 0));
  processor.reset();
  const silenceMain = new Float32Array(1024);
  const silenceSub = new Float32Array(1024);
  processor.process(new Float32Array(1024), silenceMain, silenceSub);
  assert.ok(silenceMain.every(sample => sample === 0));
  assert.ok(silenceSub.every(sample => sample === 0));
});
