#!/usr/bin/env node
import {execFileSync} from 'node:child_process';
import {readFileSync, writeFileSync} from 'node:fs';
import {basename, dirname, join} from 'node:path';
import {MourningColossusPitchCore} from './mourning-colossus-dsp-core.mjs';

function readPcm16Wav(path) {
  const wav = readFileSync(path);
  if (wav.toString('ascii', 0, 4) !== 'RIFF' || wav.toString('ascii', 8, 12) !== 'WAVE') throw Error('WAV required');
  let offset = 12, rate = 0, channels = 0, bits = 0, data;
  while (offset + 8 <= wav.length) {
    const id = wav.toString('ascii', offset, offset + 4), size = wav.readUInt32LE(offset + 4);
    if (id === 'fmt ') {channels = wav.readUInt16LE(offset + 10); rate = wav.readUInt32LE(offset + 12); bits = wav.readUInt16LE(offset + 22);}
    if (id === 'data') {data = wav.subarray(offset + 8, offset + 8 + size); break;}
    offset += 8 + size + (size % 2);
  }
  if (!data || channels !== 1 || bits !== 16) throw Error('mono PCM16 WAV required');
  const samples = new Float32Array(data.length / 2);
  for (let i = 0; i < samples.length; i += 1) samples[i] = data.readInt16LE(i * 2) / 32768;
  return {samples, rate};
}

function wavBytes(samples, rate) {
  const out = Buffer.alloc(44 + samples.length * 2);
  out.write('RIFF', 0); out.writeUInt32LE(out.length - 8, 4); out.write('WAVEfmt ', 8);
  out.writeUInt32LE(16, 16); out.writeUInt16LE(1, 20); out.writeUInt16LE(1, 22);
  out.writeUInt32LE(rate, 24); out.writeUInt32LE(rate * 2, 28); out.writeUInt16LE(2, 32); out.writeUInt16LE(16, 34);
  out.write('data', 36); out.writeUInt32LE(samples.length * 2, 40);
  for (let i = 0; i < samples.length; i += 1) out.writeInt16LE(Math.max(-32768, Math.min(32767, Math.round(samples[i] * 32767))), 44 + i * 2);
  return out;
}

const [input, output, semitoneText = '-6', subText = '0.10', presenceText = '0', makeupText = '2.2', airText = '0', airCutoffText = '3200'] = process.argv.slice(2);
if (!input || !output) throw Error('usage: render_voice_match_dsp.mjs INPUT.wav OUTPUT.wav [semitones] [sub_gain] [presence_db] [makeup_gain] [air_gain] [air_cutoff_hz]');
const semitones = Number(semitoneText), subGain = Number(subText), presence = Number(presenceText), makeup = Number(makeupText), airGain = Number(airText), airCutoff = Number(airCutoffText);
const {samples, rate} = readPcm16Wav(input);
const main = new Float32Array(samples.length), sub = new Float32Array(samples.length);
const core = new MourningColossusPitchCore(rate, 72, {mainPitchRatio: 2 ** (semitones / 12), subPitchRatio: 0.5});
for (let offset = 0; offset < samples.length; offset += 128) core.process(samples.subarray(offset, offset + 128), main.subarray(offset, offset + 128), sub.subarray(offset, offset + 128));
const folder = dirname(output), stem = basename(output, '.wav');
const mainPath = join(folder, `.${stem}-main.wav`), subPath = join(folder, `.${stem}-sub.wav`);
writeFileSync(mainPath, wavBytes(main, rate)); writeFileSync(subPath, wavBytes(sub, rate));
// The pitch core has about 150 ms of bounded look-behind. Delay the original
// high-frequency slice to the transformed voice so it restores consonants and
// breath without resurrecting the earlier, audible second speaker.
const filter = `[0:a]highpass=f=32,lowpass=f=10200,highshelf=f=2500:g=${presence},volume=0.94[m];[1:a]lowpass=f=2100,highpass=f=28,volume=${subGain}[s];[2:a]highpass=f=${airCutoff},adelay=155,volume=${airGain}[air];[m][s][air]amix=inputs=3:normalize=0,acompressor=threshold=0.12:ratio=2.0:attack=20:release=240,volume=${makeup},alimiter=limit=0.794:attack=5:release=100:level=false[out]`;
execFileSync('/opt/homebrew/bin/ffmpeg', ['-y','-hide_banner','-loglevel','error','-i',mainPath,'-i',subPath,'-i',input,'-filter_complex',filter,'-map','[out]','-ar','44100','-ac','1',output]);
