#!/usr/bin/env python3
"""Bus-style glue compressor for mastering. numpy+scipy only.
Usage: glue_comp.py <in.wav> <out.wav> [--ratio 2.5 --attack 0.03 --release 0.25 --gr 1.5 --makeup auto]
Doctrine (Sean Kim 28y): slow attack 30ms+, 2:1-4:1, 1-2dB GR sweet spot, medium/auto release.
Feedforward RMS detector at control rate, soft-knee, auto-threshold to hit target GR, RMS-match output."""
import os
import sys
import numpy as np

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
from analyze_audio import load

def compress(y, sr, ratio=2.5, attack=0.03, release=0.25, target_gr=1.5):
    mono = y.mean(axis=1)
    # RMS detector window ~ attack time
    w = max(1, int(sr * attack))
    rms = np.sqrt(np.convolve(mono ** 2, np.ones(w) / w, mode="same") + 1e-12)
    rms_db = 20 * np.log10(np.maximum(rms, 1e-9))
    # auto-threshold: find thresh giving ~target_gr max reduction (soft-knee 6dB)
    best = None
    for th in np.arange(-50, 0, 0.5):
        over = np.maximum(0.0, rms_db - th)
        knee = np.clip(over / 6.0, 0, 1)
        gr = over * (1.0 - 1.0 / ratio) * (0.5 + 0.5 * knee)
        if best is None or abs(gr.max() - target_gr) < abs(best[0] - target_gr):
            best = (gr.max(), th, gr)
    _, thresh, gr_raw = best
    # attack/release smoothing on GR curve (control-rate envelope)
    a_a = float(np.exp(-1.0 / max(sr * attack, 1)))
    r_r = float(np.exp(-1.0 / max(sr * release, 1)))
    gr = np.empty_like(gr_raw)
    cur = 0.0
    for i, v in enumerate(gr_raw):
        c = a_a if v > cur else r_r
        cur = c * cur + (1 - c) * v
        gr[i] = cur
    g = 10 ** (-gr / 20)
    out = y * g[:, None]
    return out, float(gr.max()), float(thresh)

def main():
    a = sys.argv
    if len(a) < 3:
        sys.exit("usage: glue_comp.py <in.wav> <out.wav> [--ratio 2.5 --attack 0.03 --release 0.25 --gr 1.5]")
    src, dst = a[1], a[2]
    ratio = float(a[a.index("--ratio") + 1]) if "--ratio" in a else 2.5
    attack = float(a[a.index("--attack") + 1]) if "--attack" in a else 0.03
    release = float(a[a.index("--release") + 1]) if "--release" in a else 0.25
    target = float(a[a.index("--gr") + 1]) if "--gr" in a else 1.5
    y, sr = load(src)
    orig_rms = float(np.sqrt((y ** 2).mean()))
    out, maxgr, thresh = compress(y, sr, ratio, attack, release, target)
    out *= orig_rms / max(np.sqrt((out ** 2).mean()), 1e-12)  # RMS-match for fair A/B
    th = 0.95
    m = np.abs(out) > th
    out[m] = np.sign(out[m]) * (th + (1 - th) * np.tanh((np.abs(out[m]) - th) / (1 - th)))
    peak = float(np.abs(out).max())
    out = (out * 0.99 / peak).astype(np.float32) if peak > 0.99 else out.astype(np.float32)  # ceiling-only
    from scipy.io import wavfile
    wavfile.write(dst, sr, out)
    print(f"ratio={ratio} attack={attack*1000:.0f}ms release={release*1000:.0f}ms thresh={thresh:.1f}dB maxGR={maxgr:.2f}dB rms={float(np.sqrt((out**2).mean())):.4f} peak={float(np.abs(out).max()):.3f}")
    print(f"wrote {dst}")
    if maxgr > 3.0:
        print("WARN: >3dB GR — over-compressing for mastering, ease target.")

if __name__ == "__main__":
    main()
