#!/usr/bin/env python3
"""Mastering de-esser: transparent split-band sibilance control. numpy+scipy only.
Usage: deesser.py <in.wav> <out.wav> [--freq 7000 --q 1.8 --range 2.5 --threshold DB --ratio 3 --attack 0.002 --release 0.08 --mode split-shelf|split-bell|wideband --link]
Doctrine (researched 2026-10-10: SageAudio first-insert, Fois 2025):
- FIRST insert before additive EQ/saturation/comp/limiter. Range cap <3dB for transparency.
- split-shelf default (most versatile), split-bell surgical, wideband general.
- Minimum-phase only (sosfilt/lfilter). RMS-match MANDATORY. Soft-clip overs >0.95, ceiling 0.99.
"""
import os
import sys
import numpy as np

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
from analyze_audio import load

def detect_env(band, sr, attack=0.002, release=0.08):
    a_a = float(np.exp(-1.0 / max(sr * attack, 1)))
    r_r = float(np.exp(-1.0 / max(sr * release, 1)))
    env = np.empty_like(band)
    cur = 0.0
    for i, v in enumerate(np.abs(band)):
        c = a_a if v > cur else r_r
        cur = c * cur + (1 - c) * v
        env[i] = cur
    return env

def bandpass(y, sr, f0, q):
    from scipy import signal
    lo = max(f0 / (2 ** (1.0 / max(q, 0.3))), 20.0)
    hi = min(f0 * (2 ** (1.0 / max(q, 0.3))), sr / 2 * 0.98)
    sos = signal.butter(2, [lo, hi], btype="bandpass", fs=sr, output="sos")
    return signal.sosfilt(sos, y)

def highpass_part(y, sr, f0):
    from scipy import signal
    sos = signal.butter(2, max(f0 * 0.8, 20.0), btype="highpass", fs=sr, output="sos")
    return signal.sosfilt(sos, y)

def gr_from_env(env_db, thresh_db, ratio, range_db):
    over = env_db - thresh_db
    over = np.maximum(over, 0.0)
    gr = over * (1.0 - 1.0 / max(ratio, 1.01))
    return np.minimum(gr, range_db)

def main():
    a = sys.argv
    if len(a) < 3:
        sys.exit("usage: deesser.py <in.wav> <out.wav> [--freq 7000 --q 1.8 --range 2.5 --threshold DB --ratio 3 --attack 0.002 --release 0.08 --mode split-shelf --link]")
    src, dst = a[1], a[2]
    freq = float(a[a.index("--freq") + 1]) if "--freq" in a else 7000.0
    q = float(a[a.index("--q") + 1]) if "--q" in a else 1.8
    range_db = float(a[a.index("--range") + 1]) if "--range" in a else 2.5
    ratio = float(a[a.index("--ratio") + 1]) if "--ratio" in a else 3.0
    attack = float(a[a.index("--attack") + 1]) if "--attack" in a else 0.002
    release = float(a[a.index("--release") + 1]) if "--release" in a else 0.08
    mode = a[a.index("--mode") + 1] if "--mode" in a else "split-shelf"
    linked = "--link" in a
    y, sr = load(src)
    orig_rms = float(np.sqrt((y ** 2).mean()))
    nch = y.shape[1]
    # detection per channel (independent preserves stereo; --link uses max env)
    bands = np.empty_like(y)
    for c in range(nch):
        bands[:, c] = bandpass(y[:, c], sr, freq, q)
    if linked:
        m = np.abs(bands).max(axis=1, keepdims=True)
        bands = np.repeat(m, nch, axis=1)
    thresh_db = None
    if "--threshold" in a:
        thresh_db = float(a[a.index("--threshold") + 1])
    else:  # auto: band-RMS + 12dB (sibilant peaks sit well above average)
        brms = float(np.sqrt((bands ** 2).mean()))
        thresh_db = 20 * np.log10(max(brms, 1e-9)) + 12.0
    out = np.empty_like(y)
    max_gr = 0.0
    hit_pct = 0.0
    for c in range(nch):
        env = detect_env(bands[:, c], sr, attack, release)
        env_db = 20 * np.log10(np.maximum(env, 1e-9))
        gr = gr_from_env(env_db, thresh_db, ratio, range_db)
        g = 10 ** (-gr / 20)
        max_gr = max(max_gr, float(gr.max()))
        hit_pct += float((gr > 0.5).mean()) / nch
        if mode == "wideband":
            out[:, c] = y[:, c] * g
        elif mode == "split-bell":
            dry = y[:, c] - bands[:, c]
            out[:, c] = dry + bands[:, c] * g
        else:  # split-shelf: attenuate highs above shelf knee
            from scipy import signal as _s
            hip = highpass_part(y[:, c], sr, freq)
            dry = y[:, c] - hip
            out[:, c] = dry + hip * g
    out *= orig_rms / max(np.sqrt((out ** 2).mean()), 1e-12)  # RMS-match for fair A/B
    n_over = int((np.abs(out) >= 0.99).sum())
    th = 0.95
    m = np.abs(out) > th
    out[m] = np.sign(out[m]) * (th + (1 - th) * np.tanh((np.abs(out[m]) - th) / (1 - th)))
    peak = float(np.abs(out).max())
    out = (out * 0.99 / peak).astype(np.float32) if peak > 0.99 else out.astype(np.float32)  # ceiling-only
    from scipy.io import wavfile
    wavfile.write(dst, sr, out)
    print(f"mode={mode} freq={freq:.0f} q={q} thresh={thresh_db:.1f}dB ratio={ratio} range={range_db}dB link={linked}")
    print(f"maxGR={max_gr:.2f}dB hit>0.5dB={hit_pct*100:.2f}% overs>=0.99:{n_over} rms={float(np.sqrt((out**2).mean())):.4f} peak={float(np.abs(out).max()):.3f}")
    print(f"wrote {dst}")

if __name__ == "__main__":
    main()
