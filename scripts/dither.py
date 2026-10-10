#!/usr/bin/env python3
"""TPDF dither for 16-bit CD reduction ONLY. numpy+scipy only.
Usage: dither.py <in.wav> <out16.wav>
Doctrine: dither ONLY when reducing to 16-bit. Never on 24-bit/streaming deliverables.
Rectangular TPDF, 2 LSB peak-to-peak, applied in float before int16 quantize. Always last."""
import os
import sys
import numpy as np

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
from analyze_audio import load

def main():
    a = sys.argv
    if len(a) < 3:
        sys.exit("usage: dither.py <in.wav> <out16.wav>  (24-bit/float in -> dithered 16-bit out)")
    src, dst = a[1], a[2]
    y, sr = load(src)
    peak = float(np.abs(y).max())
    if peak >= 1.0:
        y = y * 0.99 / peak
        print(f"scaled {peak:.3f}->0.99 to avoid clip before quantize")
    rng = np.random.default_rng(0)  # deterministic for repeatable masters
    tpdf = rng.random(y.shape) - rng.random(y.shape)  # triangular, +-1 LSB-ish
    lsb = 1.0 / 32768.0
    dithered = y + tpdf * lsb
    q = np.clip(np.round(dithered * 32768.0), -32768, 32767).astype(np.int16)
    from scipy.io import wavfile
    wavfile.write(dst, sr, q)
    print(f"tpdf dither 2LSB -> 16-bit wrote {dst} peak={float(np.abs(q).max())/32768:.3f}")

if __name__ == "__main__":
    main()
