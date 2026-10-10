#!/usr/bin/env python3
"""Mastering repair: DC removal + mains hum notch (50/60 Hz + harmonics). numpy+scipy only.

DC offset steals headroom and skews limiting; mains hum (50 Hz EU / 60 Hz US) plus its
harmonics is a common mix defect that survives into mastering. Static narrow notches, minimal
phase, RMS-preserving. Reports the reduction.

Usage: dehum.py <in.wav> <out.wav> [--dc] [--hum 50] [--harmonics 6] [--q 15]
Doctrine: Q ~10-20 (bandwidth 50/Q Hz). Very high Q is too narrow to catch hum drift.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
from analyze_audio import load


def band_energy_db(y, sr, f0, bw=2.0):
    """Energy in f0 +/- bw, relative to total, in dB (0 if absent)."""
    m = y.mean(axis=1)
    X = np.abs(np.fft.rfft(m * np.hanning(len(m)))) ** 2
    fr = np.fft.rfftfreq(len(m), 1 / sr)
    band = (fr >= f0 - bw) & (fr <= f0 + bw)
    return 10 * np.log10(X[band].sum() / (X.sum() + 1e-30) + 1e-30)


def main():
    a = sys.argv
    if len(a) < 3:
        sys.exit("usage: dehum.py <in.wav> <out.wav> [--dc] [--hum 50] [--harmonics 6] [--q 30]")
    src, dst = a[1], a[2]
    do_dc = "--dc" in a
    hum = float(a[a.index("--hum") + 1]) if "--hum" in a else 0.0
    nharm = int(a[a.index("--harmonics") + 1]) if "--harmonics" in a else 6
    q = float(a[a.index("--q") + 1]) if "--q" in a else 15.0
    y, sr = load(src)
    from scipy import signal
    dc0 = [float(c) for c in y.mean(axis=0)]
    e0 = band_energy_db(y, sr, hum) if hum > 0 else None
    if do_dc:
        y = y - y.mean(axis=0)
    if hum > 0:
        for h in range(1, nharm + 1):
            f0 = hum * h
            if f0 >= sr / 2 * 0.95:
                break
            b, aa = signal.iirnotch(f0, q, fs=sr)
            for c in range(y.shape[1]):
                y[:, c] = signal.lfilter(b, aa, y[:, c])
    dc1 = [float(c) for c in y.mean(axis=0)]
    peak = float(np.abs(y).max())
    if peak > 0.99:
        y = y * 0.99 / peak
    from scipy.io import wavfile
    wavfile.write(dst, sr, y.astype(np.float32))
    msg = []
    if do_dc:
        msg.append(f"DC {['%.5f' % d for d in dc0]} -> {['%.6f' % d for d in dc1]}")
    if hum > 0:
        e1 = band_energy_db(y, sr, hum)
        msg.append(f"hum {hum:.0f}Hz {e0:.1f} -> {e1:.1f} dB rel ({e0 - e1:.1f} dB down, {nharm} harmonics Q{q:.0f})")
    print(" | ".join(msg) if msg else "nothing to do (pass --dc and/or --hum 50|60)")
    print(f"wrote {dst} peak={float(np.abs(y).max()):.3f}")


if __name__ == "__main__":
    main()
