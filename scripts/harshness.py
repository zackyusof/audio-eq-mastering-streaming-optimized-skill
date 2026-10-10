#!/usr/bin/env python3
"""Dynamic harshness tamer: finds ringing 2-8kHz resonances, ducks only the peaks. numpy+scipy only.
Usage: harshness.py <in.wav> <out.wav> [--zone 2000,8000 --peaks 3 --range 2.0 --prom 8]
Doctrine (Soothe/SmoothOp/RESO workflow + top-engineer practice):
- Harshness (2-5kHz pain zone, ear most sensitive) != sibilance (5-10k, deesser.py owns that).
- NEVER static-cut resonances: dynamic-only-on-peaks, or good passages get punished (dull/lifeless).
- Sweep-narrow-boost logic automated: prominence of peak over local +-1oct median; top-N peaks only.
- Conservative: range cap 2dB/peak, total <=4dB; bypass test = original obviously more annoying,
  processed never obviously "working". Min-phase, RMS-match, soft-clip >0.95, ceiling 0.99."""
import os
import sys
import numpy as np

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
from analyze_audio import load, avg_power
from deesser import bandpass, detect_env, gr_from_env

def find_resonances(p, zlo=2000.0, zhi=8000.0, n=3, prom_min=8.0):
    import math
    y, sr = load(p)
    mono = y.mean(axis=1)
    P, fr = avg_power(mono, sr)
    db = 10 * np.log10(P + 1e-18)
    out = []
    for i in range(1, len(fr) - 1):
        f = fr[i]
        if not (zlo <= f <= zhi and db[i] > db[i - 1] and db[i] >= db[i + 1] and f > 100):
            continue
        lo_m = np.median(db[(fr >= f / 2) & (fr < f)])
        hi_m = np.median(db[(fr > f) & (fr <= f * 2)])
        prom = db[i] - max(lo_m, hi_m)
        if prom >= prom_min:
            out.append((prom, f))
    out.sort(reverse=True)
    picked = []
    for prom, f in out:
        if all(abs(math.log(f / q, 2)) > 0.25 for _, q in picked):
            picked.append((round(float(prom), 1), round(float(f))))
        if len(picked) >= n:
            break
    score = round(float(sum(pr for pr, _ in picked)), 1)
    return picked, score, sr

def main():
    a = sys.argv
    if len(a) < 3:
        sys.exit("usage: harshness.py <in.wav> <out.wav> [--zone 2000,8000 --peaks 3 --range 2.0]")
    src, dst = a[1], a[2]
    zlo, zhi = (float(x) for x in (a[a.index("--zone") + 1] if "--zone" in a else "2000,8000").split(","))
    n = int(a[a.index("--peaks") + 1]) if "--peaks" in a else 3
    rng = float(a[a.index("--range") + 1]) if "--range" in a else 2.0
    prom = float(a[a.index("--prom") + 1]) if "--prom" in a else 8.0
    peaks, score0, _ = find_resonances(src, zlo, zhi, n, prom)
    y, sr = load(src)
    orig_rms = float(np.sqrt((y ** 2).mean()))
    if not peaks:
        print(f"no resonances >={prom}dB prominence in {zlo:.0f}-{zhi:.0f}Hz (score {score0}) — pass-through")
        from scipy.io import wavfile
        wavfile.write(dst, sr, y.astype(np.float32))
        print(f"wrote {dst} (untouched)")
        return
    print(f"harshness score {score0} ({len(peaks)} peaks): " + ", ".join(f"{f:.0f}Hz +{pr}dB" for pr, f in peaks))
    total_gr = np.zeros(len(y))
    for prom, f0 in peaks:
        det = np.zeros(len(y))
        for c in range(y.shape[1]):
            det += bandpass(y[:, c], sr, f0, 2.5) / y.shape[1]
        env = detect_env(det, sr, attack=0.005, release=0.12)
        env_db = 20 * np.log10(np.maximum(env, 1e-9))
        thresh = float(env_db.max()) - 8.0  # catch only hottest excursions, not the average
        gr = gr_from_env(env_db, thresh, 3.0, rng)
        total_gr = np.maximum(total_gr, gr)
        g = 10 ** (-np.minimum(gr, 4.0) / 20)  # total cap 4dB
        for c in range(y.shape[1]):
            band = bandpass(y[:, c], sr, f0, 2.5)
            y[:, c] = (y[:, c] - band) + band * g
    print(f"maxGR={float(total_gr.max()):.2f}dB hit>0.5dB={float((total_gr > 0.5).mean())*100:.2f}%")
    y *= orig_rms / max(np.sqrt((y ** 2).mean()), 1e-12)
    th = 0.95
    m = np.abs(y) > th
    y[m] = np.sign(y[m]) * (th + (1 - th) * np.tanh((np.abs(y[m]) - th) / (1 - th)))
    peak = float(np.abs(y).max())
    y = (y * 0.99 / peak).astype(np.float32) if peak > 0.99 else y.astype(np.float32)  # ceiling-only
    from scipy.io import wavfile
    wavfile.write(dst, sr, y)
    _, score1, _ = find_resonances(dst, zlo, zhi, n, prom)
    print(f"score {score0} -> {score1} rms={float(np.sqrt((y**2).mean())):.4f} peak={float(np.abs(y).max()):.3f} wrote {dst}")

if __name__ == "__main__":
    main()
