#!/usr/bin/env python3
"""Transparent lookahead brickwall limiter + LUFS-target mastering.
maximum_filter lookahead (brickwall) + release-only gain smoothing at control rate.
Usage: limiter.py <in.wav> <out.wav> --lufs -14 --ceiling -1.2"""
import sys
import numpy as np
from scipy import ndimage
from lufs_meter import measure


def soft_clip(y, shave_db=1.0):
    """Round off transients above threshold (0.5-2 dB). Returns (clipped, shaved_db).
    Threshold is solved so measured peak shave == requested (tanh knee corrected)."""
    import math
    peak = float(np.abs(y).max())
    G = 10 ** (max(shave_db, 0.0) / 20)
    lo, hi = 1e-6, 1e3  # k = peak/thr; tanh(k)/k falls 1 -> 0, solution usually k<1
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if math.tanh(mid) / mid > 1.0 / G:
            lo = mid
        else:
            hi = mid
    thr = peak / (0.5 * (lo + hi))
    out = thr * np.tanh(y / max(thr, 1e-9))
    return out, round(20 * np.log10(peak / max(np.abs(out).max(), 1e-9)), 1)


def limit(y, sr, ceil_db=-1.0, lookahead_ms=5.0, release_ms=60.0, ctrl=64):
    thr = 10 ** (ceil_db / 20)
    D = max(1, int(sr * lookahead_ms / 1000))
    det = np.abs(y).max(axis=1)
    env = ndimage.maximum_filter1d(det, size=D + 1, mode="nearest", origin=-D // 2)
    target = np.minimum(1.0, thr / np.maximum(env, 1e-9))
    tc = target[::ctrl]  # control-rate asymmetric smoothing (fast)
    rel = float(np.exp(-ctrl / (sr * release_ms / 1000)))
    g = np.empty_like(tc)
    cur = 1.0
    for i, t in enumerate(tc):
        cur = t if t < cur else cur * rel + (1 - rel) * 1.0
        if cur > 1.0:
            cur = 1.0
        g[i] = cur
    gain = np.interp(np.arange(len(y)), np.arange(len(tc)) * ctrl, g).astype(np.float64)
    delayed = np.vstack([np.zeros((D, y.shape[1])), y])[:len(y)]
    out = delayed * gain[:, None]
    gr = -20 * np.log10(max(gain.min(), 1e-9))
    return out, round(float(gr), 1)


def main():
    src, dst = sys.argv[1], sys.argv[2]
    want = float(sys.argv[sys.argv.index("--lufs") + 1]) if "--lufs" in sys.argv else -14.0
    ceil = float(sys.argv[sys.argv.index("--ceiling") + 1]) if "--ceiling" in sys.argv else -1.2
    sys.path.insert(0, __import__("os").path.dirname(__file__))
    from analyze_audio import load
    from scipy.io import wavfile
    y, sr = load(src)
    m0 = measure(src)
    print(f"before: LUFS-I {m0['lufs']} TP {m0['tp']}dBTP crest {m0['crest']}dB")
    step = want - m0["lufs"]
    step = max(min(step, 12.0), -12.0)
    print(f"makeup {step:+.1f} dB -> ceiling {ceil} dBTP")
    out, gr = limit(y * 10 ** (step / 20), sr, ceil_db=ceil)
    wavfile.write(dst, sr, out.astype(np.float32))
    m1 = measure(dst)
    print(f"after:  LUFS-I {m1['lufs']} TP {m1['tp']}dBTP crest {m1['crest']}dB PLR {m1['plr']} (max GR {gr} dB)")


if __name__ == "__main__":
    main()
