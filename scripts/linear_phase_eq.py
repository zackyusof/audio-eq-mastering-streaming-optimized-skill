#!/usr/bin/env python3
"""Linear-phase (zero-phase) mastering EQ — the standard mastering EQ mode. numpy+scipy only.

Applies the additive band spec as an EXACT zero-phase magnitude response via FFT (padded,
reflected edges), i.e. constant group delay and no phase shift between frequencies — Ozone's
"Linear Phase" choice, used for low-end correction where phase smear is audible. Minimum-phase
(`eq_demo.py`) stays the default for colouration.

Usage: linear_phase_eq.py <in.wav> <out.wav> [--hp 28] [--lshelf f0,gain] [--hshelf f0,gain]
                          [--band f0,gain,q ...] [--pad 50]
Bands are additive dB. Example: --hp 28 --band 270,-3.5,0.9 --hshelf 10500,2.5
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
    if len(p) < 2:
        sys.exit(f"band must be f0,gain[,q] — got '{s}'")
    return p


def magnitude_at(freqs, sr, hp, bands, lshelves, hshelves):
    """Linear magnitude of the additive chain evaluated at arbitrary freqs (>=0)."""
    from scipy import signal
    total_db = np.zeros_like(freqs)
    if hp > 0:
        b, a = signal.butter(2, hp, btype="highpass", fs=sr)
        _, h = signal.freqz(b, a, worN=freqs, fs=sr)
        total_db += 20 * np.log10(np.abs(h) + 1e-12)
    for f0, g in lshelves:
        b, a = rbj_hshelf(f0, -abs(g), sr, 0.9)
        _, h = signal.freqz(b, a, worN=freqs, fs=sr)
        total_db += 20 * np.log10(np.abs(h) + 1e-12)
    for f0, g in hshelves:
        b, a = rbj_hshelf(f0, g, sr, 0.9)
        _, h = signal.freqz(b, a, worN=freqs, fs=sr)
        total_db += 20 * np.log10(np.abs(h) + 1e-12)
    for f0, g, q in bands:
        b, a = rbj_peak(f0, g, q, sr)
        _, h = signal.freqz(b, a, worN=freqs, fs=sr)
        total_db += 20 * np.log10(np.abs(h) + 1e-12)
    return 10 ** (total_db / 20.0)


def process_channel(x, sr, hp, bands, lshelves, hshelves, pad_s):
    P = max(64, int(sr * pad_s / 1000.0))
    xp = np.pad(x, P, mode="reflect")
    n = len(xp)
    freqs = np.fft.rfftfreq(n, 1.0 / sr)
    h = magnitude_at(freqs, sr, hp, bands, lshelves, hshelves)
    y = np.fft.irfft(np.fft.rfft(xp) * h, n=n)
    return y[P:P + len(x)]


def main():
    a = sys.argv
    if len(a) < 3:
        sys.exit("usage: linear_phase_eq.py <in.wav> <out.wav> [--hp 28] [--band f0,g,q ...] "
                 "[--lshelf f0,g] [--hshelf f0,g] [--pad 50]")
    src, dst = a[1], a[2]
    hp = float(a[a.index("--hp") + 1]) if "--hp" in a else 0.0
    pad_s = float(a[a.index("--pad") + 1]) if "--pad" in a else 50.0
    bands = [tuple(parse_band(a[i + 1])) for i, x in enumerate(a) if x == "--band"]
    lshelves = [tuple(parse_band(a[i + 1])[:2]) for i, x in enumerate(a) if x == "--lshelf"]
    hshelves = [tuple(parse_band(a[i + 1])[:2]) for i, x in enumerate(a) if x == "--hshelf"]
    y, sr = load(src)
    out = np.empty_like(y)
    for c in range(y.shape[1]):
        out[:, c] = process_channel(y[:, c], sr, hp, bands, lshelves, hshelves, pad_s)
    peak = float(np.abs(out).max())
    if peak > 0.99:
        out = out * 0.99 / peak
    from scipy.io import wavfile
    wavfile.write(dst, sr, out.astype(np.float32))
    desc = [f"hp{hp:.0f}"] if hp else []
    desc += [f"{f0:.0f}Hz{g:+.1f}" for f0, g, q in bands]
    desc += [f"LS{f0:.0f}{g:+.1f}" for f0, g in lshelves] + [f"HS{f0:.0f}{g:+.1f}" for f0, g in hshelves]
    print(f"zero-phase (linear-phase) EQ via FFT  pad {pad_s:.0f}ms | {' '.join(desc) or 'flat'}")
    print(f"wrote {dst} peak={float(np.abs(out).max()):.3f}")


if __name__ == "__main__":
    main()
