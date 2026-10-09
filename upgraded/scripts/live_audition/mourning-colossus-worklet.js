import {
  DEEP_MAIN_PITCH_RATIO,
  MAIN_PITCH_RATIO,
  MourningColossusPitchCore,
  SUB_PITCH_RATIO,
} from './mourning-colossus-dsp-core.mjs';

class MourningColossusProcessor extends AudioWorkletProcessor {
  constructor(options) {
    super();
    const deep = options?.processorOptions?.variant === 'deep';
    this.core = new MourningColossusPitchCore(sampleRate, 72, {
      mainPitchRatio: deep ? DEEP_MAIN_PITCH_RATIO : MAIN_PITCH_RATIO,
      subPitchRatio: SUB_PITCH_RATIO,
    });
    this.port.onmessage = event => {
      if (event.data?.type === 'reset') this.core.reset();
    };
  }

  process(inputs, outputs) {
    const input = inputs[0]?.[0];
    const main = outputs[0]?.[0];
    const sub = outputs[1]?.[0];
    if (main && sub) this.core.process(input, main, sub);
    return true;
  }
}

registerProcessor('mourning-colossus-pitch', MourningColossusProcessor);
