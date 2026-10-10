#!/usr/bin/env python3
"""Conservative full-mix mud-fix demo render. RMS-matched, soft-clip overs, ceiling 0.99."""
import sys
import numpy as np
from scipy import signal
from scipy.io import wavfile
from analyze_audio import load  # same dir

def rbj_peak(f0, g, Q, sr):
    A = 10 ** (g / 40); w0 = 2 * np.pi * f0 / sr; a = np.cos(w0); s = np.sin(w0) / (2 * Q)
    b = [1 + s * A, -2 * a, 1 - s * A]; t = [1 + s / A, -2 * a, 1 - s / A]
    return np.array(b) / t[0], np.array(t) / t[0]

def rbj_hshelf(f0, g, sr, S=0.9):
    A = 10 ** (g / 40); w0 = 2 * np.pi * f0 / sr; a = np.cos(w0)
    al = np.sin(w0) / 2 * np.sqrt((A + 1 / A) * (1 / S - 1) + 2)
    b = [A * ((A+1) + (A-1) * a + 2*np.sqrt(A)*al), -2*A * ((A-1) + (A+1)*a),
         A * ((A+1) + (A-1)*a - 2*np.sqrt(A)*al)]
    t = [(A+1) - (A-1)*a + 2*np.sqrt(A)*al, 2 * ((A-1) - (A+1)*a), (A+1) - (A-1)*a - 2*np.sqrt(A)*al]
    return np.array(b) / t[0], np.array(t) / t[0]

CHAIN = [("peak", 90, 0.8, 1.0), ("peak", 150, -1.5, 1.2), ("peak", 270, -3.5, 0.9),
         ("peak", 3200, 2.0, 0.9), ("hshelf", 10500, 2.5, 0.9)]

def main(src, dst):
    y, sr = load(src)
    orig_rms = float(np.sqrt((y ** 2).mean()))
    sos_hp = signal.butter(4, 28, btype="highpass", fs=sr, output="sos")
    out = np.empty_like(y)
    for c in range(y.shape[1]):
        s = signal.sosfilt(sos_hp, y[:, c])  # minimum-phase, like real EQ
        for kind, f0, g, q in CHAIN:
            b, a = rbj_peak(f0, g, q, sr) if kind == "peak" else rbj_hshelf(f0, g, sr, q)
            s = signal.lfilter(b, a, s)
        out[:, c] = s
    out *= orig_rms / np.sqrt((out ** 2).mean())  # RMS-match for fair A/B
    print(f"over-peak samples: {(np.abs(out) >= 0.99).sum()} / {out.size}")
    th = 0.95
    m = np.abs(out) > th  # soft-knee catch transients only
    out[m] = np.sign(out[m]) * (th + (1 - th) * np.tanh((np.abs(out[m]) - th) / (1 - th)))
    out = (out * 0.99 / max(np.abs(out).max(), 1e-9)).astype(np.float32)
    wavfile.write(dst, sr, out)
    print(f"wrote {dst} rms={float(np.sqrt((out**2).mean())):.4f} peak={float(np.abs(out).max()):.3f}")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
