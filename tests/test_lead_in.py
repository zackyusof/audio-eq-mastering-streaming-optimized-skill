#!/usr/bin/env python3
"""The render lead-in is exactly two seconds without moving program samples."""

import os
import sys
import unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
from lead_in import enforce_two_second_lead, find_program_start

SR = 48000
TARGET = 2 * SR


def tone_with_lead(seconds):
    t = np.arange(SR) / SR
    program = np.column_stack((0.1 * np.cos(2 * np.pi * 440 * t),
                               0.1 * np.cos(2 * np.pi * 660 * t))).astype(np.float32)
    source = np.concatenate((np.zeros((round(seconds * SR), 2), dtype=np.float32), program))
    return source, program


class TestLeadIn(unittest.TestCase):
    def test_short_exact_and_long_leads(self):
        for lead in (0, 1, 2, 3):
            with self.subTest(lead=lead):
                source, program = tone_with_lead(lead)
                rendered, info = enforce_two_second_lead(source, SR)
                self.assertEqual(len(rendered), TARGET + len(program))
                self.assertTrue(np.array_equal(rendered[:TARGET], 0 * rendered[:TARGET]))
                self.assertTrue(np.array_equal(rendered[TARGET:], program))
                self.assertEqual(info["duration_change_seconds"], 2 - lead)

    def test_isolated_pre_roll_click_is_not_program(self):
        source, _ = tone_with_lead(1)
        source[100, 0] = 0.5
        self.assertEqual(find_program_start(source, SR), SR)

    def test_mp3_frame_guard_keeps_pcm_under_two_seconds(self):
        source, program = tone_with_lead(1)
        rendered, info = enforce_two_second_lead(source, SR, encoder_guard_samples=1152)
        self.assertEqual(info["after_seconds"], 2 - 1152 / SR)
        self.assertEqual(len(rendered), TARGET - 1152 + len(program))
        self.assertTrue(np.array_equal(rendered[TARGET - 1152:], program))

    def test_all_silent_file_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "all-silent"):
            enforce_two_second_lead(np.zeros((SR, 2), dtype=np.float32), SR)


if __name__ == "__main__":
    unittest.main()
