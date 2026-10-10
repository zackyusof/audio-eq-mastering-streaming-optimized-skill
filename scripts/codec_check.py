#!/usr/bin/env python3
"""Lossy-codec true-peak gate (the checklist "lossy check"). numpy+scipy only (+afconvert/lameenc).

Encodes the master to AAC (afconvert) and, if lameenc is present, MP3; decodes back and
re-measures true peak / overs. Loud masters rise after encoding — clipped ones rise most.
Per the measured doctrine: AAC raises TP ~1.2 dB (limiter) to 2-4 dB (clipper).

Usage: codec_check.py <in.wav> [--aac 256] [--mp3 320] [--src-tp -1.0]
"""
import os
import subprocess
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
from analyze_audio import load
from lufs_meter import measure_array


def true_peak_db(y, sr):
    from scipy import signal
    up = signal.resample_poly(y, 4, 1, axis=0)
    return 20 * np.log10(float(np.abs(up).max()) + 1e-12)


def overs(y):
    return int((np.abs(y) >= 1.0).sum())


def wav_to(path, y, sr):
    from scipy.io import wavfile
    wavfile.write(path, sr, np.clip(y, -1.0, 1.0).astype(np.float32))


def aac_roundtrip(y, sr, kbps, tmp):
    src = os.path.join(tmp, "in.wav")
    m4a = os.path.join(tmp, "enc.m4a")
    back = os.path.join(tmp, "back.wav")
    wav_to(src, y, sr)
    subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", "-b", str(kbps * 1000), src, m4a],
                   check=True, capture_output=True)
    subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI24", m4a, back], check=True, capture_output=True)
    return load(back)


def mp3_roundtrip(y, sr, kbps, tmp):
    try:
        import lameenc
    except ImportError:
        return None
    enc = lameenc.Encoder()
    enc.set_bit_rate(kbps)
    enc.set_in_sample_rate(sr)
    enc.set_channels(y.shape[1])
    enc.set_quality(2)
    pcm = (np.clip(y, -1, 1) * 32767).astype(np.int16).tobytes()
    data = enc.encode(pcm) + enc.flush()
    mp = os.path.join(tmp, "enc.mp3")
    with open(mp, "wb") as f:
        f.write(data)
    back = os.path.join(tmp, "back_mp3.wav")
    subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI24", mp, back], check=True, capture_output=True)
    return load(back)


def main():
    a = sys.argv
    if len(a) < 2:
        sys.exit("usage: codec_check.py <in.wav> [--aac 256] [--mp3 320] [--src-tp -1.0]")
    src = a[1]
    aac_k = int(a[a.index("--aac") + 1]) if "--aac" in a else 256
    mp3_k = int(a[a.index("--mp3") + 1]) if "--mp3" in a else 320
    y, sr = load(src)
    base_tp = true_peak_db(y, sr)
    base_lufs = measure_array(y, sr)["lufs"]
    print(f"source: TP {base_tp:.2f} dBTP  I {base_lufs} LUFS")
    results = []
    with tempfile.TemporaryDirectory() as tmp:
        try:
            ye, sre = aac_roundtrip(y, sr, aac_k, tmp)
            results.append((f"AAC {aac_k}k", ye, sre))
        except Exception as e:
            print(f"AAC encode unavailable: {e}")
        ym = mp3_roundtrip(y, sr, mp3_k, tmp)
        if ym is not None:
            results.append((f"MP3 {mp3_k}k", ym[0], ym[1]))
        else:
            print("MP3: lameenc not installed (pip install lameenc) — skipped")
    ok = True
    for name, ye, sre in results:
        tp = true_peak_db(ye, sre)
        rise = tp - base_tp
        n_ov = overs(ye)
        flag = "FAIL" if n_ov > 0 else "ok"
        print(f"  after {name:9s}: TP {tp:.2f} dBTP  rise {rise:+.2f} dB  overs {n_ov}  [{flag}]")
        if n_ov > 0:
            ok = False
    if results:
        worst = max(true_peak_db(ye, sre) - base_tp for _, ye, sre in results)
        needed = base_tp + worst  # if source TP + worst rise <= 0
        print(f"worst-case rise {worst:+.2f} dB -> to stay <= 0 dBTP after codec, master TP should be <= {-worst:.2f} dBTP")
    sys.exit(0 if ok else 2)


if __name__ == "__main__":
    main()
