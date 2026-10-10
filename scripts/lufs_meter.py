#!/usr/bin/env python3
"""BS.1770-style integrated LUFS meter. Exact K-weighting at 48kHz (resamples other rates).
Reports integrated LUFS, LRA (approx), true-peak (4x, approx), crest/PLR. numpy+scipy only."""
import sys
import numpy as np
from scipy import signal

# Exact BS.1770 48kHz K-weighting coefficients
B1 = [1.53512485958697, -2.69169618940638, 1.19839281085285]
A1 = [1.0, -1.69065929318241, 0.73248077421585]
B2 = [1.0, -2.0, 1.0]
A2 = [1.0, -1.99004745483398, 0.99007225036621]

def k_weight(y, sr):
    if sr != 48000:  # meter at 48k with exact filters
        g = 48000 / sr
        y = signal.resample_poly(y, 48000, sr, axis=0)
        sr = 48000
    out = np.empty_like(y)
    for c in range(y.shape[1]):
        s = signal.lfilter(B1, A1, y[:, c])
        out[:, c] = signal.lfilter(B2, A2, s)
    return out, sr

def block_loudness(y, sr, win_s, hop_s):
    n_win, n_hop = int(win_s * sr), int(hop_s * sr)
    out = []
    for s in range(0, len(y) - n_win + 1, n_hop):
        ms = (y[s:s + n_win] ** 2).mean(axis=0).sum()  # G=1.0 stereo
        out.append(-0.691 + 10 * np.log10(ms + 1e-12))
    return np.array(out)

def measure_array(y, sr):
    peak = float(np.abs(y).max())
    yw, srw = k_weight(y, sr)
    blocks = block_loudness(yw, srw, 0.400, 0.100)
    blocks = blocks[blocks > -70]  # absolute gate
    if len(blocks) == 0:
        return {"lufs": float("-inf"), "lra": 0.0, "tp": 20*np.log10(peak), "crest": 0.0, "plr": 0.0}
    rel = blocks.mean() - 10  # relative gate
    gated = blocks[blocks > rel]
    lufs = float(gated.mean())
    st = block_loudness(yw, srw, 3.0, 1.0)  # LRA approx
    st = st[st > -70]
    lra = float(np.percentile(st, 95) - np.percentile(st, 10)) if len(st) else 0.0
    up = signal.resample_poly(y, 4, 1, axis=0)  # true-peak approx (4x)
    tp = float(np.abs(up).max())
    crest = 20 * np.log10(peak / np.sqrt((y ** 2).mean()))
    return {"lufs": round(lufs, 1), "lra": round(lra, 1), "tp": round(20*np.log10(tp), 2),
            "crest": round(float(crest), 1), "plr": round(20*np.log10(peak) - lufs, 1)}


def measure(p):
    sys.path.insert(0, __import__("os").path.dirname(__file__))
    from analyze_audio import load
    y, sr = load(p)
    return measure_array(y, sr)

if __name__ == "__main__":
    for p in sys.argv[1:]:
        m = measure(p)
        print(f"{p.split('/')[-1][:42]:42s} LUFS-I {m['lufs']:>6}  LRA {m['lra']:>4}  TP {m['tp']:>6}dBTP  crest {m['crest']:>4}dB  PLR {m['plr']:>4}")
