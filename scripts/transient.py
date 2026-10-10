#!/usr/bin/env python3
"""Transient shaper (attack / sustain) for punch control. numpy+scipy only.

Dual envelope follower separates the transient (fast attack) from the body (slow envelope).
--attack boosts/reduces the sharp front (drum punch, Low-End-Focus "punch"); --sustain does
the tail/body ("warmth"). Bounded, RMS-matched, soft-clip safety. Attack shaping is done on
the difference band so it stays mono-safe and does not pump sustained material.

Usage: transient.py <in.wav> <out.wav> [--attack 3] [--sustain -1]
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
from analyze_audio import load


def envelopes(x, sr, fast_ms=1.0, slow_ms=40.0):
    from scipy import signal
    a_f = np.exp(-1.0 / max(sr * fast_ms / 1000.0, 1))
    a_s = np.exp(-1.0 / max(sr * slow_ms / 1000.0, 1))
    fast = signal.lfilter([1 - a_f], [1, -a_f], np.abs(x))
    slow = signal.lfilter([1 - a_s], [1, -a_s], np.abs(x))
    return fast, slow


def shape(x, sr, attack_db, sustain_db):
    fast, slow = envelopes(x, sr)
    body = slow + 1e-9
    trans = np.clip(fast / body - 1.0, -1.0, 3.0)  # >0 = transient present
    g_att = 10 ** (attack_db * np.clip(trans, 0, 1) / 20.0)
    g_sus = 10 ** (sustain_db / 20.0) * np.ones_like(x)
    # attack scales the transient excess; sustain scales the body
    return x * g_sus + (x * (g_att - 1.0)) * np.clip(trans, 0, 1)


def main():
    a = sys.argv
    if len(a) < 3:
        sys.exit("usage: transient.py <in.wav> <out.wav> [--attack 3] [--sustain -1]")
    src, dst = a[1], a[2]
    attack = float(a[a.index("--attack") + 1]) if "--attack" in a else 3.0
    sustain = float(a[a.index("--sustain") + 1]) if "--sustain" in a else 0.0
    y, sr = load(src)
    orig_rms = float(np.sqrt((y ** 2).mean()))
    out = np.empty_like(y)
    for c in range(y.shape[1]):
        out[:, c] = shape(y[:, c], sr, attack, sustain)
    out *= orig_rms / max(np.sqrt((out ** 2).mean()), 1e-12)
    th = 0.95
    m = np.abs(out) > th
    out[m] = np.sign(out[m]) * (th + (1 - th) * np.tanh((np.abs(out[m]) - th) / (1 - th)))
    peak = float(np.abs(out).max())
    out = (out * 0.99 / peak).astype(np.float32) if peak > 0.99 else out.astype(np.float32)
    from scipy.io import wavfile
    wavfile.write(dst, sr, out)
    print(f"transient attack {attack:+.1f} dB sustain {sustain:+.1f} dB | rms-matched "
          f"peak={float(np.abs(out).max()):.3f}")
    print(f"wrote {dst}")


if __name__ == "__main__":
    main()
