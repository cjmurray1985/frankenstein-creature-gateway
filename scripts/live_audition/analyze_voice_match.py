#!/usr/bin/env python3
"""Dependency-free comparison of bounded mono PCM voice captures."""
from __future__ import annotations

import json
import math
from pathlib import Path
import statistics
import subprocess
import sys
import wave


def samples(path: Path, target_rate: int = 8000) -> tuple[list[float], int]:
    with wave.open(str(path), "rb") as audio:
        rate = audio.getframerate()
        width = audio.getsampwidth()
        channels = audio.getnchannels()
        raw = audio.readframes(audio.getnframes())
    if width != 2 or channels != 1:
        raise ValueError(f"expected mono PCM16: {path}")
    values = [int.from_bytes(raw[i:i+2], "little", signed=True) / 32768 for i in range(0, len(raw), 2)]
    step = max(1, round(rate / target_rate))
    return values[::step], rate / step


def metrics(path: Path) -> dict:
    data, rate = samples(path)
    frame = max(1, round(rate * .04))
    hop = max(1, round(rate * .01))
    rms_values, pitches = [], []
    for start in range(0, max(0, len(data) - frame), hop):
        block = data[start:start + frame]
        rms = math.sqrt(sum(value * value for value in block) / len(block))
        rms_values.append(rms)
        if rms < .012:
            continue
        best_lag, best = 0, 0.0
        for lag in range(max(1, round(rate / 220)), min(len(block) - 1, round(rate / 45))):
            corr = sum(block[i] * block[i + lag] for i in range(len(block) - lag))
            energy = math.sqrt(sum(block[i] ** 2 for i in range(len(block) - lag)) * sum(block[i + lag] ** 2 for i in range(len(block) - lag)))
            score = corr / energy if energy else 0
            if score > best:
                best_lag, best = lag, score
        if best_lag and best > .45:
            pitches.append(rate / best_lag)
    voiced = [value for value in rms_values if value >= .012]
    active_seconds = len(voiced) * hop / rate
    duration = len(data) / rate
    return {
        "duration_seconds": round(duration, 3),
        "active_seconds": round(active_seconds, 3),
        "silence_ratio": round(1 - active_seconds / duration, 3) if duration else 1,
        "median_rms_dbfs": round(20 * math.log10(statistics.median(voiced)), 2) if voiced else None,
        "median_f0_hz": round(statistics.median(pitches), 1) if pitches else None,
        "p10_f0_hz": round(sorted(pitches)[len(pitches)//10], 1) if pitches else None,
    }


def main() -> None:
    folder = Path(sys.argv[1])
    reference = metrics(folder / "elevenlabs-mourning-colossus.wav")
    results = {"reference": reference, "candidates": []}
    for path in sorted(folder.glob("gpt-live-dsp-*.wav")):
        current = metrics(path)
        score = 0.0
        for key, scale in (("duration_seconds", 8), ("silence_ratio", .3), ("median_rms_dbfs", 12), ("median_f0_hz", 70)):
            if current[key] is not None and reference[key] is not None:
                score += ((current[key] - reference[key]) / scale) ** 2
        results["candidates"].append({"file": path.name, "distance": round(math.sqrt(score), 4), **current})
    results["candidates"].sort(key=lambda item: item["distance"])
    (folder / "analysis.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
