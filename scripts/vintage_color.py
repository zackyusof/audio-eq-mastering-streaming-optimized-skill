#!/usr/bin/env python3
"""Vintage color box: transformer + tube + tape flavors with Pultec-style tone. numpy+scipy only.
Usage: vintage_color.py <in.wav> <out.wav> [--flavor pultec|tape15|tube|transformer] [--drive 0.5] [--mix 1.0]
Why vintage in mastering (MusicRadar 2023): run signal THROUGH hardware for sauce even at no-op —
Pultec low trick (boost+cut same freq = tighter curve), 1176 all-buttons color, Studer tape (wow/flutter/sat),
console preamps (API/SSL/Neve) vs digital sterility. Ours: min-phase RBJ tone + tanh saturation, RMS-match, ceiling 0.99."""
import os
import sys
import numpy as np

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
from analyze_audio import load
from eq_demo import rbj_peak, rbj_hshelf

def saturate(y, drive, flavor):
    k = 1.0 + drive * 3.0
    if flavor == "tube":  # even-harmonic warmth: asymmetric soft clip
        pos = np.tanh(k * np.maximum(y, 0)) / np.tanh(k)
        neg = np.tanh(k * 0.85 * np.minimum(y, 0)) / np.tanh(k * 0.85)
        return pos + neg
    if flavor == "tape15":  # symmetric + slight hysteresis feel via soft knee
        return np.tanh(k * 0.8 * y) / np.tanh(k * 0.8)
    if flavor == "transformer":  # barely-there iron: gentle 2nd-order curve
        return y / (1.0 + drive * 0.3 * np.abs(y))
    return np.tanh(k * y) / np.tanh(k)  # pultec: clean tube stage

def tone(y, sr, flavor, drive):
    from scipy import signal
    out = y.copy()
    if flavor == "pultec":
        # low trick: boost + cut at 60Hz with different Q = resonant tighten (not cancellation)
        # air: +1dB shelf @12k scaled by drive
        for c in range(out.shape[1]):
            for f0, g, q in [(60, 2.0, 1.0), (60, -2.0, 1.4), (12000, 1.0 * (0.5 + drive), 0.7)]:
                b, a = rbj_peak(f0, g, q, sr) if f0 < 10000 else rbj_hshelf(f0, g, sr, 0.7)
                out[:, c] = signal.lfilter(b, a, out[:, c])
    elif flavor == "tape15":
        sos = signal.butter(2, 18000, btype="lowpass", fs=sr, output="sos")
        for c in range(out.shape[1]):
            b, a = rbj_peak(60, 0.5, 1.0, sr)
            out[:, c] = signal.lfilter(b, a, out[:, c])
            out[:, c] = signal.sosfilt(sos, out[:, c])
    elif flavor == "tube":
        for c in range(out.shape[1]):
            b, a = rbj_peak(200, 0.4 * drive + 0.2, 1.0, sr)
            out[:, c] = signal.lfilter(b, a, out[:, c])
    return out

def main():
    a = sys.argv
    if len(a) < 3:
        sys.exit("usage: vintage_color.py <in.wav> <out.wav> [--flavor pultec|tape15|tube|transformer --drive 0.5 --mix 1.0]")
    src, dst = a[1], a[2]
    flavor = a[a.index("--flavor") + 1] if "--flavor" in a else "pultec"
    drive = float(a[a.index("--drive") + 1]) if "--drive" in a else 0.5
    mix = float(a[a.index("--mix") + 1]) if "--mix" in a else 1.0
    assert flavor in ("pultec", "tape15", "tube", "transformer"), "unknown flavor"
    drive = max(0.0, min(drive, 1.0))
    y, sr = load(src)
    orig_rms = float(np.sqrt((y ** 2).mean()))
    toned = tone(y, sr, flavor, drive)
    sat = saturate(toned / max(np.abs(toned).max(), 1e-9) * 0.9, drive, flavor)
    sat *= np.sqrt((toned ** 2).mean()) / max(np.sqrt((sat ** 2).mean()), 1e-12)
    out = toned * (1 - mix) + sat * mix
    out *= orig_rms / max(np.sqrt((out ** 2).mean()), 1e-12)
    th = 0.95
    m = np.abs(out) > th
    out[m] = np.sign(out[m]) * (th + (1 - th) * np.tanh((np.abs(out[m]) - th) / (1 - th)))
    peak = float(np.abs(out).max())
    out = (out * 0.99 / peak).astype(np.float32) if peak > 0.99 else out.astype(np.float32)  # ceiling-only
    added = float(np.sqrt(((out - y * (np.sqrt((out**2).mean()) / max(np.sqrt((y**2).mean()), 1e-12))) ** 2).mean()))
    from scipy.io import wavfile
    wavfile.write(dst, sr, out)
    print(f"flavor={flavor} drive={drive} mix={mix} rms={float(np.sqrt((out**2).mean())):.4f} peak={float(np.abs(out).max()):.3f} color={added:.4f}")
    print(f"wrote {dst}")

if __name__ == "__main__":
    main()
