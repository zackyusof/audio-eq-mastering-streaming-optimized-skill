#!/usr/bin/env python3
"""Translation stage: make low end survive small speakers + quiet playback. numpy+scipy only.
Usage: translate.py <in.wav> <out.wav>
Doctrine (ProAudioPlug low-end translation + Fletcher-Munson quiet-ear proof):
- Three zones: sub 20-60 (FELT, vanishes on small/quiet systems, wastes headroom) / body 60-200
  (HEARD everywhere, the translation carrier) / upper harmonics 200-500 (definition on laptop/phone).
- Saturation as translation tool: parallel low-band tube saturation adds 2nd/3rd harmonics (60Hz ->
  120/180Hz) so the ear reconstructs the fundamental (psychoacoustic bass) where subs can't play.
- Adaptive + conservative: sub share >12% -> broad -XdB trim @45Hz (cap 2dB, keeps thump, HPF stays 28);
  always a LITE parallel ghost (mix 0.25, drive 0.4) for harmonic carry. Balanced tracks pass through
  nearly untouched. Per-channel (image intact), min-phase, RMS-match, soft-clip >0.95, ceiling 0.99."""
import os
import sys
import numpy as np

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
from analyze_audio import load, avg_power, BANDS

def band_share(p_or_y, sr=None, key="sub 20-60"):
    if isinstance(p_or_y, str):
        y, sr = load(p_or_y)
    else:
        y = p_or_y
    mono = y.mean(axis=1)
    P, fr = avg_power(mono, sr)
    tot = P.sum()
    out = {}
    for k, (a, b) in BANDS.items():
        m = (fr >= a) & (fr < b)
        out[k] = P[m].sum() / tot * 100
    return out, y, sr

def translate_array(y, sr):
    from scipy import signal
    from eq_demo import rbj_peak
    from vintage_color import saturate
    sh0, _, _ = band_share(y, sr)
    sub = sh0["sub 20-60"]
    trim = min(max((sub - 12.0) * 0.15, 0.0), 2.0)
    if trim > 0.05:
        for c in range(y.shape[1]):
            b, a = rbj_peak(45, -trim, 0.7, sr)
            y[:, c] = signal.lfilter(b, a, y[:, c])
    sos_bp = signal.butter(2, [60, 250], btype="bandpass", fs=sr, output="sos")
    ghost_mix, drive = 0.25, 0.4
    for c in range(y.shape[1]):
        lo = signal.sosfilt(sos_bp, y[:, c])
        pk = float(np.abs(lo).max())
        sat = saturate(lo / max(pk, 1e-9) * 0.9, drive, "tube")
        sat *= float(np.sqrt((lo ** 2).mean())) / max(float(np.sqrt((sat ** 2).mean())), 1e-12)
        y[:, c] = y[:, c] + (sat - lo) * ghost_mix  # parallel ghost: dry + harmonic difference only
    sh1, _, _ = band_share(y, sr)
    return y, sub, sh1["sub 20-60"], sh1["body 400-800"] - sh0["body 400-800"], trim

def main():
    a = sys.argv
    if len(a) < 3:
        sys.exit("usage: translate.py <in.wav> <out.wav>")
    src, dst = a[1], a[2]
    y, sr = load(src)
    orig_rms = float(np.sqrt((y ** 2).mean()))
    y, sub0, sub1, body_lift, trim = translate_array(y, sr)
    y *= orig_rms / max(np.sqrt((y ** 2).mean()), 1e-12)
    th = 0.95
    m = np.abs(y) > th
    y[m] = np.sign(y[m]) * (th + (1 - th) * np.tanh((np.abs(y[m]) - th) / (1 - th)))
    peak = float(np.abs(y).max())
    y = (y * 0.99 / peak).astype(np.float32) if peak > 0.99 else y.astype(np.float32)  # ceiling-only
    from scipy.io import wavfile
    wavfile.write(dst, sr, y)
    print(f"sub {sub0:.1f}%->{sub1:.1f}% (trim -{trim:.2f}dB) body-lift {body_lift:+.2f}pp rms={float(np.sqrt((y**2).mean())):.4f} peak={float(np.abs(y).max()):.3f} wrote {dst}")

if __name__ == "__main__":
    main()
