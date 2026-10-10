#!/usr/bin/env python3
"""Unit tests for limiter.py (lookahead brickwall + soft_clip). numpy+scipy only.
Run: python3 tests/test_limiter_true_peak.py (no pytest needed)."""
import os
import sys
import unittest
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
from limiter import limit, soft_clip
from lufs_meter import measure_array

SR = 48000

def hot_mix(db_over=12.0, secs=2.0):
    t = np.arange(int(SR * secs)) / SR
    y = (np.sin(2 * np.pi * 110 * t) + 0.5 * np.sin(2 * np.pi * 440 * t)) * 10 ** (db_over / 20) * 0.2
    return np.stack([y, y], axis=1)

class TestLimiterTruePeak(unittest.TestCase):
    def test_ceiling_holds_4x_measured(self):
        out, gr = limit(hot_mix(), SR, ceil_db=-1.0)
        tp = measure_array(out, SR)["tp"]
        self.assertLessEqual(tp, -1.0 + 0.3)  # 4x-approx tolerance

    def test_quiet_signal_transparent(self):
        t = np.arange(int(SR * 2.0)) / SR
        y = np.stack([np.sin(2 * np.pi * 440 * t) * 0.1] * 2, axis=1)
        _, gr = limit(y, SR, ceil_db=-1.0)
        self.assertAlmostEqual(gr, 0.0, delta=0.2)

    def test_gr_positive_on_hot_signal(self):
        _, gr = limit(hot_mix(), SR, ceil_db=-1.0)
        self.assertGreater(gr, 0.5)

    def test_soft_clip_shave_matches_request(self):
        t = np.arange(int(SR * 2.0)) / SR
        y = np.stack([np.sin(2 * np.pi * 100 * t) * 0.99] * 2, axis=1)
        _, shaved = soft_clip(y, 1.5)
        self.assertAlmostEqual(shaved, 1.5, delta=0.3)

    def test_soft_clip_never_exceeds_099(self):
        out, _ = soft_clip(hot_mix(db_over=12.0), 2.0)
        self.assertLessEqual(float(np.abs(out).max()), 0.999)

if __name__ == "__main__":
    unittest.main(verbosity=2)
