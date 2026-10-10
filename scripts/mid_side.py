#!/usr/bin/env python3
"""Mid/Side mastering tools: independent M/S EQ, global width, mono-below. numpy+scipy only.

Ozone's EQ/Dynamics/Imager all offer M/S; this is the routing. Encode L/R -> M/S, EQ the mid
(centre: vocal/kick) and the side (stereo image) independently, optionally widen, decode.
Minimum-phase biquads (M/S EQ is normally minimum-phase). Reports corr + mono loss.

Usage: mid_side.py <in.wav> <out.wav> [--mid f0,g,q ...] [--side f0,g,q ...]
                   [--width W] [--mono F]
Example: --side 12000,1.5,0.7 --mid 250,-1.5,1.0 --width 1.12 --mono 120
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
from analyze_audio import load
from eq_demo import rbj_peak, rbj_hshelf


def parse_band(s):
    p = [float(x) for x in s.split(",")]
    if len(p) != 3:
        sys.exit(f"band must be f0,gain,q — got '{s}'")
    return p


def apply_eq(x, sr, bands):
    from scipy import signal
    for f0, g, q in bands:
        b, a = rbj_peak(f0, g, q, sr)
        x = signal.lfilter(b, a, x)
    return x


def process(y, sr, mid_bands, side_bands, width, mono_f):
    from scipy import signal
    assert y.shape[1] == 2, "mid_side needs stereo input"
    L, R = y[:, 0], y[:, 1]
    M, S = (L + R) / 2, (L - R) / 2
    M = apply_eq(M, sr, mid_bands)
    S = apply_eq(S, sr, side_bands)
    if mono_f > 0:
        # mono the side below mono_f via an LR4 highpass. NOT side-lowpass(side):
        # minimum-phase subtraction adds ~+3dB at the transition instead of removing lows.
        sos = signal.butter(2, mono_f, btype="highpass", fs=sr, output="sos")
        S = signal.sosfilt(sos, signal.sosfilt(sos, S))
    S = S * width
    return np.stack([M + S, M - S], axis=1)


def corr(a, b):
    return float(np.corrcoef(a[::97], b[::97])[0, 1])


def main():
    a = sys.argv
    if len(a) < 3:
        sys.exit("usage: mid_side.py <in.wav> <out.wav> [--mid f0,g,q ...] [--side f0,g,q ...] [--width W] [--mono F]")
    src, dst = a[1], a[2]
    mid_bands = [parse_band(a[i + 1]) for i, x in enumerate(a) if x == "--mid"]
    side_bands = [parse_band(a[i + 1]) for i, x in enumerate(a) if x == "--side"]
    width = float(a[a.index("--width") + 1]) if "--width" in a else 1.0
    mono_f = float(a[a.index("--mono") + 1]) if "--mono" in a else 0.0
    y, sr = load(src)
    if y.shape[1] != 2:
        sys.exit("mid_side: mono input — pass-through, nothing to do.")
    orig_rms = float(np.sqrt((y ** 2).mean()))
    c0 = corr(y[:, 0], y[:, 1])
    out = process(y, sr, mid_bands, side_bands, width, mono_f)
    c1 = corr(out[:, 0], out[:, 1])
    m0 = np.sqrt((y.mean(axis=1) ** 2).mean())
    m1 = np.sqrt((out.mean(axis=1) ** 2).mean())
    mono_loss = 20 * np.log10((m1 + 1e-12) / (m0 + 1e-12))
    out *= orig_rms / max(np.sqrt((out ** 2).mean()), 1e-12)
    th = 0.95
    m = np.abs(out) > th
    out[m] = np.sign(out[m]) * (th + (1 - th) * np.tanh((np.abs(out[m]) - th) / (1 - th)))
    peak = float(np.abs(out).max())
    out = (out * 0.99 / peak).astype(np.float32) if peak > 0.99 else out.astype(np.float32)
    from scipy.io import wavfile
    wavfile.write(dst, sr, out)
    print(f"M/S eq (mid {len(mid_bands)}, side {len(side_bands)}) width={width} mono<{mono_f:.0f} "
          f"corr {c0:.3f}->{c1:.3f} monoloss={mono_loss:+.2f}dB peak={float(np.abs(out).max()):.3f}")
    print(f"wrote {dst}")
    if c1 < 0.3:
        print("WARN: corr <0.3 — width aggressive, check mono.")


if __name__ == "__main__":
    main()
