#!/usr/bin/env python3
"""Perceived spectrum: raw FFT shares vs ear-weighted shares. numpy+scipy only.
Usage: perceived.py <file.wav>
Why (Fletcher-Munson 1933 -> Robinson-Dadson 1956 -> ISO 226:2003, current ed. 2023):
the ear is not a flat mic. ~3-4kHz ear-canal resonance = peak sensitivity (our harshness zone);
lows/highs need far more SPL at quiet levels; contours flatten as level rises (85dB SPL studio ref).
Honesty rules (iZotope caveat, Avery): contours are averaged lab data, NOT a personal inverse-EQ target.
This tool is ANALYSIS ONLY: A-weighting (IEC 61672 exact ~= 40-phon/quiet ear) and C-weighting
(exact ~= 100-phon/loud ear). The A-vs-C delta per band is the translation forecast: big delta =
balance shifts with the listener's volume knob. No interpolated phon fiction, no processing target."""
import os
import sys
import numpy as np

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
from analyze_audio import load, avg_power, BANDS

def a_weight(f):
    f = np.maximum(np.asarray(f, dtype=float), 1.0)
    f2 = f ** 2
    ra = (12194.0 ** 2 * f ** 4) / ((f2 + 20.6 ** 2) * np.sqrt((f2 + 107.7 ** 2) * (f2 + 737.9 ** 2)) * (f2 + 12194.0 ** 2))
    ra1k = (12194.0 ** 2 * 1e12) / ((1e6 + 20.6 ** 2) * np.sqrt((1e6 + 107.7 ** 2) * (1e6 + 737.9 ** 2)) * (1e6 + 12194.0 ** 2))
    return 20 * np.log10(ra / ra1k)

def c_weight(f):
    f = np.maximum(np.asarray(f, dtype=float), 1.0)
    f2 = f ** 2
    rc = (12194.0 ** 2 * f2) / ((f2 + 20.6 ** 2) * (f2 + 12194.0 ** 2))
    rc1k = (12194.0 ** 2 * 1e6) / ((1e6 + 20.6 ** 2) * (1e6 + 12194.0 ** 2))
    return 20 * np.log10(rc / rc1k)

def shares(P, fr, wdb=None):
    Pw = P * (10 ** (wdb / 10) if wdb is not None else 1.0)
    tot = Pw.sum()
    out = {}
    for k, (a, b) in BANDS.items():
        m = (fr >= a) & (fr < b)
        out[k] = Pw[m].sum() / tot * 100
    cent = float((fr * Pw).sum() / tot)
    return out, cent

def main():
    p = sys.argv[1] if len(sys.argv) > 1 else sys.exit("usage: perceived.py <file.wav>")
    y, sr = load(p)
    mono = y.mean(axis=1)
    P, fr = avg_power(mono, sr)
    raw, rc = shares(P, fr)
    aw, ac = shares(P, fr, a_weight(fr))
    cw, cc = shares(P, fr, c_weight(fr))
    print(f"{'band':14s} {'raw%':>6s} {'A(quiet)%':>10s} {'C(loud)%':>9s} {'shift':>6s}")
    for k in BANDS:
        print(f"{k:14s} {raw[k]:6.2f} {aw[k]:10.2f} {cw[k]:9.2f} {cw[k]-aw[k]:+6.2f}")
    print(f"centroid raw {rc:.0f}Hz / A {ac:.0f}Hz / C {cc:.0f}Hz")
    worst = sorted(BANDS, key=lambda k: abs(cw[k] - aw[k]), reverse=True)[:3]
    print("level-dependent bands (check at several volumes): " + ", ".join(f"{k} ({cw[k]-aw[k]:+.1f})" for k in worst))

if __name__ == "__main__":
    main()
