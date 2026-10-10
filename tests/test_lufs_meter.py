#!/usr/bin/env python3
"""Unit tests for lufs_meter.py (BS.1770-style, 4x true-peak approx). numpy+scipy only.
Run: python3 tests/test_lufs_meter.py (no pytest needed). Relative/tolerance assertions only."""
import os
import sys
import unittest
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
from lufs_meter import measure_array

SR = 48000

def sine(f=1000.0, dbfs=-20.0, secs=3.0, ch=2):
    t = np.arange(int(SR * secs)) / SR
    a = 10 ** (dbfs / 20)
    return np.stack([np.sin(2 * np.pi * f * t) * a] * ch, axis=1)

class TestLufsMeter(unittest.TestCase):
    def test_gain_tracks_lufs(self):
        m0 = measure_array(sine(dbfs=-20.0), SR)
        m1 = measure_array(sine(dbfs=-14.0), SR)
        self.assertAlmostEqual(m1["lufs"] - m0["lufs"], 6.0, delta=0.3)

    def test_silence_is_minus_inf(self):
        m = measure_array(np.zeros((SR * 2, 2)), SR)
        self.assertEqual(m["lufs"], float("-inf"))

    def test_true_peak_sine_within_half_db(self):
        # 100 Hz sine: 4x oversampling must read peak within 0.5 dB of 0 dBFS-normalized peak
        y = sine(f=100.0, dbfs=0.0) * 0.9
        m = measure_array(y, SR)
        true_peak = 20 * np.log10(0.9)
        self.assertAlmostEqual(m["tp"], true_peak, delta=0.5)

    def test_stereo_sums_3db_over_mono(self):
        t = np.arange(int(SR * 3.0)) / SR
        a = 10 ** (-20.0 / 20)
        mono = (np.sin(2 * np.pi * 1000 * t) * a).reshape(-1, 1)
        stereo = np.repeat(mono, 2, axis=1)
        self.assertAlmostEqual(
            measure_array(stereo, SR)["lufs"] - measure_array(mono, SR)["lufs"], 3.0, delta=0.3)

    def test_dc_blocked_below_40hz(self):
        # K-style HPF: 20 Hz tone must read much quieter than equal-SPL 1 kHz tone
        m_lo = measure_array(sine(f=20.0, dbfs=-10.0), SR)
        m_hi = measure_array(sine(f=1000.0, dbfs=-10.0), SR)
        self.assertGreater(m_hi["lufs"] - m_lo["lufs"], 10.0)

if __name__ == "__main__":
    unittest.main(verbosity=2)
