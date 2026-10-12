#!/usr/bin/env python3
"""Profiles are well-formed: known names, valid flag tokens, valued flags carry a value."""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
from profiles import PROFILES, profile_args, profile_names

REQUIRED = {"engineer", "genre", "basis", "confidence", "targets", "args"}
VALUED = {"--lufs", "--tp", "--tilt", "--tilt-target", "--pivot", "--skew", "--clip", "--color",
          "--mono", "--width", "--sidehpf", "--transient", "--dehum", "--spectral-smooth", "--profile"}


class TestProfiles(unittest.TestCase):
    def test_required_keys_and_targets(self):
        for name, p in PROFILES.items():
            with self.subTest(profile=name):
                self.assertEqual(REQUIRED - set(p), set())
                for k in ("lufs", "tp", "slope_dB_oct"):
                    self.assertIn(k, p["targets"])
                self.assertLessEqual(p["targets"]["tp"], -1.0)   # never above the -1 dBTP ceiling

    def test_args_well_formed(self):
        for name in profile_names():
            args = profile_args(name)
            self.assertIsInstance(args, list)
            for i, tok in enumerate(args):
                if tok in VALUED:
                    self.assertLess(i + 1, len(args), f"{name}: {tok} missing a value")
                    self.assertFalse(args[i + 1].startswith("--"),
                                     f"{name}: {tok} value looks like a flag")

    def test_unknown_profile_raises(self):
        with self.assertRaises(KeyError):
            profile_args("does-not-exist")

    def test_house_baseline_present(self):
        self.assertIn("modern-rock", PROFILES)

    def test_exactly_one_profile_ships(self):
        """This build ships the single house default - no engineer-derived presets."""
        self.assertEqual(profile_names(), ["modern-rock"])


if __name__ == "__main__":
    unittest.main()
