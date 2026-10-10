#!/usr/bin/env python3
"""Stereo tool for mastering: mono lows + gentle width + mono-compat check. numpy+scipy only.
Usage: stereo_tool.py <in.wav> <out.wav> [--mono 200 --width 1.1] [--sidehpf 90]
Doctrine: keep <200Hz mono (phase/mono-collapse safety), widen mids/highs gently, always check mono.
Minimum-phase LR4 crossover (sosfilt). RMS-match output. Reports L/R corr + mono loss."""
import os
import sys
import numpy as np

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
from analyze_audio import load

def lr4_lp(x, sr, fc):
    from scipy import signal
    sos = signal.butter(4, fc, btype="lowpass", fs=sr, output="sos")
    return signal.sosfilt(sos, x)

def lr4_hp(x, sr, fc):
    """Linkwitz-Riley 4th-order highpass (two cascaded 2nd-order Butterworth). -6dB at fc."""
    from scipy import signal
    sos = signal.butter(2, fc, btype="highpass", fs=sr, output="sos")
    return signal.sosfilt(sos, signal.sosfilt(sos, x))

def process(y, sr, mono_freq=200.0, width=1.1, sidehpf=0.0):
    from scipy import signal
    assert y.shape[1] == 2, "stereo tool needs stereo input"
    L, R = y[:, 0], y[:, 1]
    mid, side = (L + R) / 2, (L - R) / 2
    if sidehpf > 0:
        # gentler alternative to full mono: high-pass the SIDE below N (keeps 90-200Hz width)
        sos_hp = signal.butter(4, sidehpf, btype="highpass", fs=sr, output="sos")
        side2 = signal.sosfilt(sos_hp, side) * width
    elif mono_freq > 0:
        # mono the side below mono_freq: highpass the side directly. Do NOT do
        # side - lowpass(side) — a minimum-phase lowpass has phase lag, so that
        # subtracts out of phase and BOOSTS the transition ~+3dB instead of removing it.
        side_hi = lr4_hp(side, sr, mono_freq)
        side2 = side_hi * width  # lows stay mono, highs get width
    else:
        side2 = side * width
    L2, R2 = mid + side2, mid - side2
    return np.stack([L2, R2], axis=1)

def corr(a, b):
    return float(np.corrcoef(a[::97], b[::97])[0, 1])

def main():
    a = sys.argv
    if len(a) < 3:
        sys.exit("usage: stereo_tool.py <in.wav> <out.wav> [--mono 200 --width 1.1]")
    src, dst = a[1], a[2]
    mono_f = float(a[a.index("--mono") + 1]) if "--mono" in a else 200.0
    sidehpf = float(a[a.index("--sidehpf") + 1]) if "--sidehpf" in a else 0.0
    width = float(a[a.index("--width") + 1]) if "--width" in a else 1.1
    if width > 1.4:
        print("WARN: width >1.4 risks mono collapse — restraint is key.")
    y, sr = load(src)
    if y.shape[1] != 2:
        sys.exit("stereo_tool: mono input — nothing to do, skipping (pass through).")
    orig_rms = float(np.sqrt((y ** 2).mean()))
    c0 = corr(y[:, 0], y[:, 1])
    out = process(y, sr, mono_f, width, sidehpf)
    c1 = corr(out[:, 0], out[:, 1])
    mono_loss = 20 * np.log10(np.sqrt(((out.mean(axis=1)) ** 2).mean()) / max(np.sqrt((y.mean(axis=1) ** 2).mean()), 1e-12))
    out *= orig_rms / max(np.sqrt((out ** 2).mean()), 1e-12)
    th = 0.95
    m = np.abs(out) > th
    out[m] = np.sign(out[m]) * (th + (1 - th) * np.tanh((np.abs(out[m]) - th) / (1 - th)))
    peak = float(np.abs(out).max())
    out = (out * 0.99 / peak).astype(np.float32) if peak > 0.99 else out.astype(np.float32)  # ceiling-only
    from scipy.io import wavfile
    wavfile.write(dst, sr, out)
    mode = f"sidehpf<{sidehpf:.0f}Hz" if sidehpf > 0 else f"mono<{mono_f:.0f}Hz"
    print(f"{mode} width={width} corr {c0:.3f}->{c1:.3f} monoloss={mono_loss:+.2f}dB rms={float(np.sqrt((out**2).mean())):.4f} peak={float(np.abs(out).max()):.3f}")
    print(f"wrote {dst}")
    if c1 < 0.3:
        print("WARN: corr <0.3 — width too aggressive, check mono.")

if __name__ == "__main__":
    main()
