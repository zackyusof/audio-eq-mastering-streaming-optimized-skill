#!/usr/bin/env python3
"""Measure time-frequency overlap of aligned stems and render chosen space moves.

The overlap score is a screening measure, not a psychoacoustic masking verdict.
It requires actual stems; a finished stereo mix cannot identify instruments.
"""

import argparse
import json
from pathlib import Path

import numpy as np
from scipy import signal
from scipy.io import wavfile

from analyze_audio import load


BANDS = ((60, 150), (150, 400), (400, 800), (800, 1500),
         (1500, 4000), (4000, 8000), (8000, 12000))


def band_frames(y, sr):
    """Band power every 1024 samples, processed in bounded chunks."""
    mono = y.mean(axis=1)
    nfft, hop = 2048, 1024
    freqs = np.fft.rfftfreq(nfft, 1 / sr)
    pieces = []
    for start in range(0, len(mono), sr * 8):
        chunk = mono[start : start + sr * 8]
        if len(chunk) < nfft:
            chunk = np.pad(chunk, (0, nfft - len(chunk)))
        _, _, z = signal.stft(chunk, fs=sr, nperseg=nfft, noverlap=nfft - hop,
                              boundary=None, padded=False)
        power = np.abs(z) ** 2
        pieces.append(np.stack([power[(freqs >= lo) & (freqs < hi)].sum(axis=0)
                                for lo, hi in BANDS]))
    return np.concatenate(pieces, axis=1)


def analyze_stems(paths):
    if len(paths) < 2:
        raise ValueError("provide at least two aligned stems")
    data = []
    for path in paths:
        y, sr = load(str(path))
        data.append((path, y, sr))
    rates = {sr for _, _, sr in data}
    lengths = {len(y) for _, y, _ in data}
    if len(rates) != 1 or len(lengths) != 1:
        raise ValueError("stems must have the same sample rate and length; align them first")
    features = [(path.name, band_frames(y, sr)) for path, y, sr in data]
    report = {"sample_rate": data[0][2], "duration_s": round(len(data[0][1]) / data[0][2], 2),
              "metric": "energy-weighted time-frequency overlap; potential masking only", "pairs": []}
    for i in range(len(features)):
        for j in range(i + 1, len(features)):
            name_a, a = features[i]
            name_b, b = features[j]
            bands = []
            total_energy = float((a + b).sum()) + 1e-20
            for idx, (lo, hi) in enumerate(BANDS):
                x, y = a[idx], b[idx]
                threshold_x = max(float(x.max()) * 1e-3, 1e-14)
                threshold_y = max(float(y.max()) * 1e-3, 1e-14)
                active = (x > threshold_x) & (y > threshold_y)
                overlap = float(2 * np.minimum(x[active], y[active]).sum() /
                                max((x[active] + y[active]).sum(), 1e-20))
                coactive = float(active.mean())
                energy_share = float((x + y).sum() / total_energy)
                score = overlap * coactive * energy_share
                balance = float(10 * np.log10((x.sum() + 1e-20) / (y.sum() + 1e-20)))
                bands.append({"hz": [lo, hi], "overlap": round(overlap, 3),
                              "coactivity": round(coactive, 3), "energy_share": round(energy_share, 3),
                              "score": round(score, 4), "a_minus_b_db": round(balance, 1)})
            report["pairs"].append({"stems": [name_a, name_b],
                                    "bands": sorted(bands, key=lambda v: v["score"], reverse=True)})
    return report


def peaking_cut(y, sr, hz, db, q):
    if not 20 < hz < sr / 2 or not 0 < db <= 3 or not 0.5 <= q <= 2:
        raise ValueError("cut requires 20 < hz < Nyquist, 0 < dB <= 3, Q 0.5..2")
    a = 10 ** (-db / 40)
    w = 2 * np.pi * hz / sr
    alpha = np.sin(w) / (2 * q)
    b = np.array([1 + alpha * a, -2 * np.cos(w), 1 - alpha * a])
    den = np.array([1 + alpha / a, -2 * np.cos(w), 1 - alpha / a])
    return signal.lfilter(b / den[0], den / den[0], y, axis=0)


def render_stem(source, output, cut_hz, cut_db, q, pan):
    if source.resolve() == output.resolve():
        raise ValueError("output must differ from source")
    if not output.parent.exists():
        raise ValueError("output directory does not exist")
    if not -1 <= pan <= 1:
        raise ValueError("pan must be -1..1")
    if cut_db <= 0 and pan == 0:
        raise ValueError("choose an explicit EQ cut or pan position")
    y, sr = load(str(source))
    if cut_db > 0:
        y = peaking_cut(y, sr, cut_hz, cut_db, q)
    if pan != 0:
        if y.shape[1] != 1:
            raise ValueError("pan is for mono stems only; balance stereo stems in the DAW")
        angle = (pan + 1) * np.pi / 4
        y = np.column_stack((y[:, 0] * np.cos(angle), y[:, 0] * np.sin(angle)))
    peak = float(np.max(np.abs(y)))
    if peak > 1:
        raise ValueError(f"render peak {peak:.3f} exceeds 1.0; lower the stem level first")
    wavfile.write(output, sr, y.astype(np.float32))
    return peak


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    a = sub.add_parser("analyze", help="rank pairwise band overlap across aligned stems")
    a.add_argument("stems", type=Path, nargs="+")
    a.add_argument("--json", action="store_true")
    r = sub.add_parser("render", help="render an explicitly chosen EQ cut and/or mono-stem pan")
    r.add_argument("source", type=Path)
    r.add_argument("output", type=Path)
    r.add_argument("--cut-hz", type=float, default=0.0)
    r.add_argument("--cut-db", type=float, default=0.0)
    r.add_argument("--q", type=float, default=0.9)
    r.add_argument("--pan", type=float, default=0.0, help="mono stem only: -1 left, +1 right")
    args = p.parse_args()
    if args.command == "analyze":
        report = analyze_stems(args.stems)
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            print("Potential masking: higher score means more shared energy and time, not proven audibility.")
            for pair in report["pairs"]:
                print(" / ".join(pair["stems"]))
                for band in pair["bands"][:3]:
                    lo, hi = band["hz"]
                    print(f"  {lo}-{hi} Hz score={band['score']:.3f} overlap={band['overlap']:.2f} "
                          f"coactivity={band['coactivity']:.2f} A-B={band['a_minus_b_db']:+.1f} dB")
    else:
        peak = render_stem(args.source, args.output, args.cut_hz, args.cut_db, args.q, args.pan)
        print(f"wrote {args.output}; peak={peak:.3f}; check in the full mix and mono")


if __name__ == "__main__":
    main()
