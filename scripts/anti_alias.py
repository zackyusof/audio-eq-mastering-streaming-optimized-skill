#!/usr/bin/env python3
"""Anti-aliasing diagnostic for nonlinear stages.

Answers "is anti-aliasing / oversampling needed HERE?" empirically.

Two modes:
  sine (default) : push a bright tone through a stage, measure energy that is NOT a
                   harmonic of the input (= folded alias content), at 1x/2x/4x/8x.
  oob            : feed a band-limited 1-14 kHz chirp and measure OUT-OF-BAND energy
                   (15 kHz..Nyquist). A waveshaper raises it (harmonics race past
                   Nyquist); a time-varying gain cannot (sidebands hug each partial).

Rule (Gazillion/Tonalux/Wojcik, measured): only WAVESHAPERS alias. Time-varying gain
(dynamics: compressor/limiter/multiband/dynamic EQ) and linear stages do not --
skip oversampling there.

Usage:
  anti_alias.py [--stage clipper|hardclip|softclip|glue] [--mode sine|oob]
                [--f0 6200] [--drive 6] [--shave 2.0] [--gr 6.0]
                [--sr 44100] [--ratios 1,2,4,8] [--lines 4]
"""
import argparse
import sys

import numpy as np
from scipy import signal


def nonharmonic_db(x, sr, f0, guard=200.0, lines=0):
    """Energy not near f0 or its harmonics (below Nyquist), rel. total, in dB."""
    X = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    fr = np.fft.rfftfreq(len(x), 1.0 / sr)
    X = X / X.max()
    Xdb = 20 * np.log10(X + 1e-20)
    mask = fr > 100
    k = 1
    while f0 * k < sr / 2:
        mask &= np.abs(fr - f0 * k) > guard
        k += 1
    nhe = 10 * np.log10(np.sum(10 ** (Xdb[mask] / 10)) / np.sum(10 ** (Xdb / 10)) + 1e-30)
    top = ""
    if lines:
        idx = np.argsort(Xdb * mask)[::-1][:lines]
        top = "  lines: " + ", ".join(f"{fr[i]/1000:.1f}k@{Xdb[i]:.0f}dB" for i in sorted(idx, key=lambda i: fr[i]))
    return nhe, top


def out_of_band_db(x, sr, f_lo=15000.0):
    X = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    fr = np.fft.rfftfreq(len(x), 1.0 / sr)
    band = (fr >= f_lo) & (fr <= sr / 2)
    full = fr >= 100
    return 10 * np.log10(np.sum(X[band] ** 2) / np.sum(X[full] ** 2) + 1e-30)


def make_stage(name, shave, gr):
    if name == "clipper":
        return lambda x, sr: np.tanh(x)
    if name == "hardclip":
        return lambda x, sr: np.clip(x, -1.0, 1.0)
    if name == "softclip":
        from limiter import soft_clip
        return lambda x, sr: soft_clip(x, shave)[0]
    if name == "glue":
        from glue_comp import compress

        def f(x, sr):
            y2 = np.stack([x, x], axis=1)
            o, _, _ = compress(y2, sr, ratio=4.0, attack=0.030, release=0.250, target_gr=gr)
            return o[:, 0]
        return f
    sys.exit(f"unknown stage: {name}")


def run(stage, x, sr, os):
    if os == 1:
        return stage(x, sr)
    y = stage(signal.resample_poly(x, os, 1), sr * os)
    return signal.resample_poly(y, 1, os)[: len(x)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="clipper", choices=["clipper", "hardclip", "softclip", "glue"])
    ap.add_argument("--mode", default="sine", choices=["sine", "oob"])
    ap.add_argument("--f0", type=float, default=6200.0)
    ap.add_argument("--drive", type=float, default=6.0, help="dB above full scale (ceiling)")
    ap.add_argument("--shave", type=float, default=2.0, help="softclip requested shave dB")
    ap.add_argument("--gr", type=float, default=6.0, help="glue target gain reduction dB")
    ap.add_argument("--sr", type=int, default=44100)
    ap.add_argument("--ratios", default="1,2,4,8")
    ap.add_argument("--lines", type=int, default=0)
    a = ap.parse_args()

    stage = make_stage(a.stage, a.shave, a.gr)
    if a.mode == "sine":
        t = np.arange(int(a.sr)) / a.sr
        x = np.sin(2 * np.pi * a.f0 * t) * (10 ** (a.drive / 20))
        metric = lambda y, sr: nonharmonic_db(y, a.sr, a.f0, lines=a.lines)
        what = "non-harmonic (folded alias) content"
    else:
        t = np.arange(int(a.sr)) / a.sr
        x = signal.chirp(t, 1000.0, 1.0, 14000.0) * (10 ** (a.drive / 20))
        metric = lambda y, sr: (out_of_band_db(y, a.sr), "")
        what = "out-of-band 15kHz..Nyquist energy (alias cannot appear if input band-limited)"

    print(f"stage={a.stage} mode={a.mode} sr={a.sr} drive=+{a.drive:.0f}dB gr={a.gr} : {what}")
    base = None
    for os in [int(r) for r in a.ratios.split(",")]:
        y = run(stage, x, a.sr, os)
        val, top = metric(y, a.sr)
        if base is None:
            base = val
        gain = "" if os == 1 else f"  ({base - val:+.0f} dB vs 1x)"
        print(f"  {os:2d}x oversample : {val:8.1f} dB{gain}{top}")


if __name__ == "__main__":
    main()
