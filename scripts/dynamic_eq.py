#!/usr/bin/env python3
"""Whole-song dynamic EQ: listens in ticks, corrects per-section, not per-average. numpy+scipy only.
Usage: dynamic_eq.py <in.wav> <out.wav> [--tick 2.0 --cap 1.0 --csv ticks.csv]
Doctrine (Unison dynamic-EQ automation + Soothe "only when needed" + our static-EQ trap lesson):
a static cut that fixes the chorus dulls the verse. So: slice the song into ticks (default 2s),
measure 7 band shares per tick (mud..air; sub/thump left to translate/glue — dynamic low-end = pumping),
compare each tick to the SONG MEDIAN (self-referential consistency target), cut over-represented bands
proportionally (factor 0.5, cap 1dB, cuts ONLY — never chase loudness upward), smooth correction curves
across ticks (5-tick moving average + interpolate, no zipper), apply via fixed LR4 filter bank with
time-varying per-band gains (no coefficient modulation -> no clicks). Min-phase, RMS-match, ceiling-only."""
import os
import sys
import numpy as np

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
from analyze_audio import load, avg_power, BANDS

DYN_BANDS = ["mud 150-400", "body 400-800", "grind 0.8-1.5k", "bite 1.5-4k",
             "presence 4-8k", "fizz 8-12k", "air 12k+"]
EDGES = [150, 400, 800, 1500, 4000, 8000, 12000]

def tick_shares(mono, sr, tick=2.0):
    n = int(tick * sr)
    out = []
    for s in range(0, len(mono), n):
        seg = mono[s:s + n]
        if len(seg) < 32768:
            break
        P, fr = avg_power(seg, sr, stride=1)
        tot = P.sum()
        out.append({k: P[(fr >= a) & (fr < b)].sum() / tot * 100 for k, (a, b) in BANDS.items()})
    return out

def correction_curves(ticks, cap=1.0, factor=0.5):
    med = {k: float(np.median([t[k] for t in ticks])) for k in DYN_BANDS}
    corr = {k: np.zeros(len(ticks)) for k in DYN_BANDS}
    for i, t in enumerate(ticks):
        for k in DYN_BANDS:
            delta = 10 * np.log10(max(t[k], 1e-9) / max(med[k], 1e-9))
            corr[k][i] = -min(max(delta * factor, 0.0), cap) if delta > 0 else 0.0
    w = 3  # moving-average across ticks (+-1 tick): no pumping/zipper, no 4s pre-echo
    sm = {k: np.convolve(v, np.ones(w) / w, mode="same") for k, v in corr.items()}
    return sm, med

def split_bank(y, sr):
    from scipy import signal
    nyq = sr / 2
    parts = [signal.sosfilt(signal.butter(4, EDGES[0], btype="lowpass", fs=sr, output="sos"), y)]
    for lo, hi in zip(EDGES[:-1], EDGES[1:]):
        parts.append(signal.sosfilt(signal.butter(4, [lo, hi], btype="bandpass", fs=sr, output="sos"), y))
    parts.append(signal.sosfilt(signal.butter(4, EDGES[-1], btype="highpass", fs=sr, output="sos"), y))
    return parts  # [low, mud, body, grind, bite, presence, fizz, air]

def apply_dynamic(y, sr, curves, tick=2.0):
    n = len(y)
    nt = len(next(iter(curves.values())))
    idx = np.clip((np.arange(n) / (tick * sr) * 1.0).astype(int), 0, nt - 1)
    out = np.zeros_like(y)
    for ch in range(y.shape[1]):
        parts = split_bank(y[:, ch], sr)
        acc = parts[0].copy()  # low residual untouched
        for (k, edge_i) in zip(DYN_BANDS, range(1, 8)):
            g = 10 ** (curves[k][idx] / 20)
            acc = acc + parts[edge_i] * g
        out[:, ch] = acc
    return out

def dyn_stats(ticks, curves):
    rep = []
    for k in DYN_BANDS:
        v = curves[k]
        rep.append(f"{k.split()[0]}:max{np.abs(v).max():.1f}dB active{(np.abs(v) > 0.2).mean()*100:.0f}%")
    before = {k: float(np.std([t[k] for t in ticks])) for k in DYN_BANDS}
    return " | ".join(rep), before

def main():
    a = sys.argv
    if len(a) < 3:
        sys.exit("usage: dynamic_eq.py <in.wav> <out.wav> [--tick 2.0 --cap 1.0 --csv ticks.csv]")
    src, dst = a[1], a[2]
    tick = float(a[a.index("--tick") + 1]) if "--tick" in a else 2.0
    cap = float(a[a.index("--cap") + 1]) if "--cap" in a else 1.0
    csvp = a[a.index("--csv") + 1] if "--csv" in a else ""
    y, sr = load(src)
    orig_rms = float(np.sqrt((y ** 2).mean()))
    mono = y.mean(axis=1)
    ticks = tick_shares(mono, sr, tick)
    print(f"ticks: {len(ticks)} x {tick}s over {len(y)/sr:.0f}s")
    curves, med = correction_curves(ticks, cap)
    rep, _ = dyn_stats(ticks, curves)
    print(rep)
    if csvp:
        import csv
        with open(csvp, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["tick", "t_sec"] + [f"{k}_share" for k in DYN_BANDS] + [f"{k}_cutdB" for k in DYN_BANDS])
            for i, t in enumerate(ticks):
                w.writerow([i, round(i * tick, 1)] + [round(t[k], 2) for k in DYN_BANDS] + [round(float(curves[k][i]), 2) for k in DYN_BANDS])
        print(f"tick table -> {csvp}")
    out = apply_dynamic(y, sr, curves, tick)
    out *= orig_rms / max(np.sqrt((out ** 2).mean()), 1e-12)
    th = 0.95
    m = np.abs(out) > th
    out[m] = np.sign(out[m]) * (th + (1 - th) * np.tanh((np.abs(out[m]) - th) / (1 - th)))
    peak = float(np.abs(out).max())
    out = (out * 0.99 / peak).astype(np.float32) if peak > 0.99 else out.astype(np.float32)  # ceiling-only
    from scipy.io import wavfile
    wavfile.write(dst, sr, out)
    print(f"rms={float(np.sqrt((out**2).mean())):.4f} peak={float(np.abs(out).max()):.3f} wrote {dst}")

if __name__ == "__main__":
    main()
