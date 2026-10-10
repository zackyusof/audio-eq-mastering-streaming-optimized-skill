#!/usr/bin/env python3
"""Reference tonal matcher: level-matched EQ deltas only, NEVER loudness. numpy+scipy only.
Usage: ref_match.py <mix.wav> <ref.wav> <out.wav> [--amount 0.6 --maxdb 2.5]
Doctrine (Unison/FabFilter wisdom): level-match first (louder always wins), smooth ~50%, apply ~60%,
moves <= +-2.5dB. Caveats enforced: NEVER match a mastered ref's lows blindly (cap sub cut -1dB);
NEVER chase top octave of an MP3-ish ref (skip air if ref rolloff<16k while mix>18k); tonal only.
If ref mud ~= mix mud (<1dB), skip mud cut. RMS-match to MIX."""
import os
import sys
import numpy as np

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
from analyze_audio import load, avg_power, BANDS

KEYS = ["sub 20-60", "thump 60-150", "mud 150-400", "body 400-800", "grind 0.8-1.5k",
        "bite 1.5-4k", "presence 4-8k", "fizz 8-12k", "air 12k+"]
CENTERS = [40, 100, 270, 600, 1150, 2700, 6000, 10000, 15000]

def shares(p):
    y, sr = load(p)
    mono = y.mean(axis=1)
    P, fr = avg_power(mono, sr)
    tot = P.sum()
    out = {}
    for k, (a, b) in BANDS.items():
        m = (fr >= a) & (fr < b)
        out[k] = P[m].sum() / tot * 100
    c = float((fr * P).sum() / tot)
    roll = float(fr[np.searchsorted(np.cumsum(P) / tot, 0.85)])
    return out, c, roll, sr

def main():
    a = sys.argv
    if len(a) < 4:
        sys.exit("usage: ref_match.py <mix.wav> <ref.wav> <out.wav> [--amount 0.6 --maxdb 2.5]")
    mix_p, ref_p, dst = a[1], a[2], a[3]
    amt = float(a[a.index("--amount") + 1]) if "--amount" in a else 0.6
    cap = float(a[a.index("--maxdb") + 1]) if "--maxdb" in a else 2.5
    ms, _, _, sr = shares(mix_p)
    rs, _, rroll, _ = shares(ref_p)
    _, _, mroll, _ = shares(mix_p)
    y, sr = load(mix_p)
    orig_rms = float(np.sqrt((y ** 2).mean()))
    from eq_demo import rbj_peak, rbj_hshelf
    from scipy import signal
    print(f"{'band':14s} {'mix%':>6s} {'ref%':>6s} {'applied':>8s}")
    for k, f0 in zip(KEYS, CENTERS):
        want = 10 * np.log10(max(rs[k], 1e-9) / max(ms[k], 1e-9))
        app = want * amt
        tag = ""
        if k == "sub 20-60" and app < -1.0:
            app, tag = -1.0, " [cap: mastered-ref lows]"
        if k == "air 12k+" and rroll < 16000 and mroll > 18000:
            app, tag = 0.0, " [skip: MP3-ish ref top octave]"
        if k == "mud 150-400" and abs(want) < 1.0:
            app, tag = 0.0, " [skip: mud~=ref]"
        app = max(-cap, min(cap, app))
        print(f"{k:14s} {ms[k]:6.2f} {rs[k]:6.2f} {app:+7.2f}dB{tag}")
        if abs(app) < 0.05:
            continue
        for c in range(y.shape[1]):
            if k == "air 12k+":
                b, bb = rbj_hshelf(12000, app, sr, 0.7)
            else:
                b, bb = rbj_peak(f0, app, 1.0, sr)
            y[:, c] = signal.lfilter(b, bb, y[:, c])
    y *= orig_rms / max(np.sqrt((y ** 2).mean()), 1e-12)  # tonal only — never loudness
    th = 0.95
    m = np.abs(y) > th
    y[m] = np.sign(y[m]) * (th + (1 - th) * np.tanh((np.abs(y[m]) - th) / (1 - th)))
    peak = float(np.abs(y).max())
    y = (y * 0.99 / peak).astype(np.float32) if peak > 0.99 else y.astype(np.float32)  # ceiling-only
    from scipy.io import wavfile
    wavfile.write(dst, sr, y)
    print(f"amount={amt} cap={cap}dB rms={float(np.sqrt((y**2).mean())):.4f} peak={float(np.abs(y).max()):.3f} wrote {dst}")

if __name__ == "__main__":
    main()
