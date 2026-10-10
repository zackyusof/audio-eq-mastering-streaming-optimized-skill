#!/usr/bin/env python3
"""Signal-level checks for opt-in repair, space analysis, and default neutrality."""

import os
import sys
import unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))

from spectral_repair import declick_array, smooth_array
from stem_space import band_frames, peaking_cut
from stereo_tool import process

SR = 48000


class TestSpectralSpace(unittest.TestCase):
    def test_isolated_click_repairs_without_moving_clean_audio(self):
        t = np.arange(SR) / SR
        clean = (0.2 * np.sin(2 * np.pi * 440 * t))[:, None]
        damaged = clean.copy()
        damaged[10000, 0] = 0.95
        fixed, count = declick_array(damaged, SR)
        self.assertEqual(count, 1)
        self.assertLess(abs(fixed[10000, 0] - clean[10000, 0]), 0.002)
        self.assertTrue(np.array_equal(fixed[:9000], clean[:9000]))

    def test_smoothing_is_bounded_and_preserves_low_fundamental(self):
        t = np.arange(SR) / SR
        low = (0.2 * np.sin(2 * np.pi * 220 * t))[:, None]
        high = (0.2 * np.sin(2 * np.pi * 2000 * t))[:, None]
        low_out = smooth_array(low, SR, 1.5)
        high_out = smooth_array(high, SR, 1.5)
        low_ratio = np.sqrt(np.mean(low_out ** 2) / np.mean(low ** 2))
        high_ratio = np.sqrt(np.mean(high_out ** 2) / np.mean(high ** 2))
        self.assertAlmostEqual(low_ratio, 1.0, delta=0.01)
        self.assertGreaterEqual(high_ratio, 10 ** (-1.5 / 20) - 0.02)
        self.assertLess(high_ratio, 1.0)

    def test_short_flat_pop_repairs_with_returning_edges(self):
        t = np.arange(SR) / SR
        clean = (0.1 * np.sin(2 * np.pi * 440 * t))[:, None]
        damaged = clean.copy()
        damaged[10000:10048] += 0.5  # 1 ms rectangular pop
        fixed, count = declick_array(damaged, SR)
        self.assertGreaterEqual(count, 48)
        self.assertLess(np.max(np.abs(fixed - clean)), 0.02)

    def test_band_features_distinguish_overlapping_stems(self):
        t = np.arange(SR * 2) / SR
        a = (0.2 * np.sin(2 * np.pi * 500 * t))[:, None]
        same = (0.1 * np.sin(2 * np.pi * 500 * t))[:, None]
        distant = (0.1 * np.sin(2 * np.pi * 5000 * t))[:, None]
        fa, fs, fd = (band_frames(x, SR) for x in (a, same, distant))
        body = 2  # 400..800 Hz
        self.assertGreater(fs[body].sum(), fd[body].sum() * 100)
        self.assertGreater(fa[body].sum(), 0)

    def test_small_eq_cut_and_width_only(self):
        t = np.arange(SR) / SR
        mono = (0.1 * np.sin(2 * np.pi * 1000 * t))[:, None]
        cut = peaking_cut(mono, SR, 1000, 2, 0.9)
        ratio = np.sqrt(np.mean(cut ** 2) / np.mean(mono ** 2))
        self.assertAlmostEqual(20 * np.log10(ratio), -2.0, delta=0.15)
        stereo = np.column_stack((mono[:, 0], mono[:, 0] * 0.8))
        widened = process(stereo, SR, mono_freq=0, width=1.1)
        self.assertEqual(widened.shape, stereo.shape)
        self.assertTrue(np.isfinite(widened).all())
        self.assertGreater(np.sqrt(np.mean(((widened[:, 0] - widened[:, 1]) / 2) ** 2)),
                           np.sqrt(np.mean(((stereo[:, 0] - stereo[:, 1]) / 2) ** 2)))


if __name__ == "__main__":
    unittest.main()
