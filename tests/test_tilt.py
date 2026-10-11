#!/usr/bin/env python3
"""Tilt EQ: pivot is neutral, extremes move by +/- T/2, slope tracks the sign."""

import os
import sys
import unittest

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
from tilt import apply_tilt, measure_slope, tilt_for_target, curvature_db

SR = 48000
PIVOT = 800.0


def band_gain(y, sr, lo, hi):
    sos = signal.butter(4, [lo, hi], btype="bandpass", fs=sr, output="sos")
    return float(np.sqrt((signal.sosfilt(sos, y.mean(axis=1)) ** 2).mean()))


def sines():
    t = np.arange(SR * 3) / SR
    low = 0.2 * np.sin(2 * np.pi * 60 * t)
    high = 0.2 * np.sin(2 * np.pi * 10000 * t)
    return np.column_stack((low + high, low + high))


class TestTilt(unittest.TestCase):
    def test_zero_tilt_is_identity(self):
        x = sines()
        self.assertTrue(np.array_equal(apply_tilt(x, SR, 0.0, PIVOT), x))

    def test_extremes_move_by_half_the_tilt(self):
        x = sines()
        for tilt in (6.0, -6.0, 12.0):
            with self.subTest(tilt=tilt):
                y = apply_tilt(x, SR, tilt, PIVOT)
                lo_db = 20 * np.log10(band_gain(y, SR, 50, 80) / band_gain(x, SR, 50, 80))
                hi_db = 20 * np.log10(band_gain(y, SR, 9000, 11000) / band_gain(x, SR, 9000, 11000))
                self.assertAlmostEqual(lo_db, -tilt / 2, delta=0.6)
                self.assertAlmostEqual(hi_db, +tilt / 2, delta=0.6)

    def test_positive_tilt_raises_slope_negative_lowers_it(self):
        rng = np.random.default_rng(0)
        x = (rng.standard_normal((SR * 3, 2)) * 0.1).astype(np.float64)
        base, _, _ = measure_slope(x.mean(axis=1), SR)
        up, _, _ = measure_slope(apply_tilt(x, SR, 4.0, PIVOT).mean(axis=1), SR)
        dn, _, _ = measure_slope(apply_tilt(x, SR, -4.0, PIVOT).mean(axis=1), SR)
        self.assertGreater(up, base + 0.3)
        self.assertLess(dn, base - 0.3)

    def test_target_helper_sign_and_clamp(self):
        # darker than target -> positive (brighter) tilt; brighter than target -> negative
        self.assertGreater(tilt_for_target(-2.5, -1.9), 0.0)
        self.assertLess(tilt_for_target(-1.2, -1.9), 0.0)
        # already at target -> ~0
        self.assertAlmostEqual(tilt_for_target(-1.9, -1.9), 0.0, places=6)
        # absurd gap is clamped to the +/-3 dB ceiling
        self.assertEqual(tilt_for_target(-9.0, 0.0), 3.0)
        self.assertEqual(tilt_for_target(9.0, 0.0), -3.0)

    def test_curvature_detects_scoop_vs_hump(self):
        rng = np.random.default_rng(1)
        x = (rng.standard_normal((SR * 3, 2)) * 0.1)
        # a scoop (mid cut) -> negative curvature; a mid boost -> positive
        scoop = signal.sosfilt(signal.butter(2, [250, 1500], btype="bandstop", fs=SR, output="sos"), x, axis=0)
        hump = signal.sosfilt(signal.butter(2, [250, 1500], btype="bandpass", fs=SR, output="sos"), x, axis=0)
        flat = curvature_db(x.mean(axis=1), SR)
        self.assertLess(curvature_db(scoop.mean(axis=1), SR), flat - 1.0)
        self.assertGreater(curvature_db(hump.mean(axis=1), SR), flat + 1.0)

    def test_pivot_is_neutral_ish(self):
        x = sines()
        tilt = 6.0
        y = apply_tilt(x, SR, tilt, PIVOT)
        piv_db = 20 * np.log10(band_gain(y, SR, PIVOT * 0.85, PIVOT * 1.15)
                               / band_gain(x, SR, PIVOT * 0.85, PIVOT * 1.15))
        # a band straddling the pivot has a small net move (the zero-crossing is a single
        # frequency) but must be far smaller than the half-tilt at the extremes
        self.assertLess(abs(piv_db), 0.25 * (tilt / 2))


if __name__ == "__main__":
    unittest.main()
