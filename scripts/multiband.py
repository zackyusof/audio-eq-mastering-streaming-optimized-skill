#!/usr/bin/env python3
"""4-band mastering multiband glue. numpy+scipy only.
Usage: multiband.py <in.wav> <out.wav>
Bands/ratios (MusicGuyMastering glue setup): 1-120Hz 1.6:1 / 120-1200 1.5:1 / 1200-9000 1.2:1 / 9000+ 1.1:1.
Soft-knee, low thresholds (whole-range smoothing), attack >=5-10ms to keep punch. RMS-match, ceiling 0.99."""
import os
import sys
import numpy as np

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
from analyze_audio import load

BANDS = [(1, 120, 1.6, 0.010), (120, 1200, 1.5, 0.020), (1200, 9000, 1.2, 0.015), (9000, 24000, 1.1, 0.005)]

def split_bands(y, sr):
    from scipy import signal
    nyq = sr / 2
    parts = []
    for lo, hi, _, _ in BANDS:
        hi = min(hi, nyq * 0.98)
        if lo <= 1:
            sos = signal.butter(4, hi, btype="lowpass", fs=sr, output="sos")
        elif hi >= nyq * 0.97:
            sos = signal.butter(4, lo, btype="highpass", fs=sr, output="sos")
        else:
            sos = signal.butter(4, [lo, hi], btype="bandpass", fs=sr, output="sos")
        parts.append(signal.sosfilt(sos, y))
    return parts

def comp_band(b, sr, ratio, attack, target=1.0):
    rms = np.sqrt(np.convolve(b ** 2, np.ones(max(1, int(sr * attack))) / max(1, int(sr * attack)), mode="same") + 1e-12)
    db = 20 * np.log10(np.maximum(rms, 1e-9))
    best = None
    for th in np.arange(-50, 0, 0.5):
        over = np.maximum(0.0, db - th)
        gr = over * (1.0 - 1.0 / ratio) * np.clip(over / 12.0 * 0.5 + 0.5, 0, 1)
        if best is None or abs(gr.max() - target) < abs(best[1].max() - target):
            best = (th, gr)
    th, gr_raw = best
    aa = float(np.exp(-1.0 / max(sr * attack, 1)))
    rr = float(np.exp(-1.0 / max(sr * 0.15, 1)))
    gr, cur = np.empty_like(gr_raw), 0.0
    for i, v in enumerate(gr_raw):
        c = aa if v > cur else rr
        cur = c * cur + (1 - c) * v
        gr[i] = cur
    return b * 10 ** (-gr / 20), float(gr.max()), float(th)

def main():
    a = sys.argv
    if len(a) < 3:
        sys.exit("usage: multiband.py <in.wav> <out.wav>")
    src, dst = a[1], a[2]
    y, sr = load(src)
    mono = y.mean(axis=1)
    orig_rms = float(np.sqrt((y ** 2).mean()))
    parts = split_bands(mono, sr)
    tot, rep = [], []
    for (lo, hi, ratio, atk), b in zip(BANDS, parts):
        o, g, th = comp_band(b, sr, ratio, atk)
        tot.append(o)
        rep.append(f"{lo}-{hi}:{ratio}:1 GR {g:.2f}dB th {th:.0f}")
    wet = np.sum(tot, axis=0)
    # per-channel gain ride from mono multiband delta (keeps stereo image intact).
    # Clamp: dividing by a near-zero band sum in quiet gaps spikes the gain and
    # destroys the track once RMS-matched (bug 2026-10-10). Floor + +/-6dB ride.
    denom = np.sum(parts, axis=0)
    g = np.ones_like(wet)
    nz = np.abs(denom) > 1e-4
    g[nz] = wet[nz] / denom[nz]
    g = np.clip(g, 10 ** (-6 / 20), 10 ** (6 / 20))
    out = y * g[:, None]
    out *= orig_rms / max(np.sqrt((out ** 2).mean()), 1e-12)
    th = 0.95
    m = np.abs(out) > th
    out[m] = np.sign(out[m]) * (th + (1 - th) * np.tanh((np.abs(out[m]) - th) / (1 - th)))
    peak = float(np.abs(out).max())
    out = (out * 0.99 / peak).astype(np.float32) if peak > 0.99 else out.astype(np.float32)  # ceiling-only
    from scipy.io import wavfile
    wavfile.write(dst, sr, out)
    print(" | ".join(rep))
    print(f"rms={float(np.sqrt((out**2).mean())):.4f} peak={float(np.abs(out).max()):.3f} wrote {dst}")

if __name__ == "__main__":
    main()
