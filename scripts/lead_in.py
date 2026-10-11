#!/usr/bin/env python3
"""Give a final audio render exactly two seconds of digital silence before program.

Program onset is the first sample above -80 dBFS in the first two consecutive
10 ms blocks whose RMS exceeds -80 dBFS. The sustained-block check avoids
treating an isolated sample click as the beginning of a song. If a very short
file has no such run, use its first above-threshold sample instead.
"""

import numpy as np


TARGET_SECONDS = 2.0
SILENCE_DBFS = -80.0
FRAME_SECONDS = 0.01


def find_program_start(y, sr):
    """Return onset sample, or raise for an all-silent file."""
    x = np.asarray(y)
    if x.ndim == 1:
        x = x[:, None]
    if sr <= 0 or not len(x):
        raise ValueError("audio must contain samples at a valid sample rate")
    floor = 10 ** (SILENCE_DBFS / 20)
    frame = max(1, int(round(sr * FRAME_SECONDS)))
    first_active = None
    for start in range(0, len(x), frame):
        block = x[start : start + frame]
        rms = float(np.sqrt(np.mean(block.astype(np.float64) ** 2)))
        if rms >= floor:
            if first_active is not None:
                first_block = x[first_active : first_active + frame]
                crossings = np.flatnonzero(np.max(np.abs(first_block), axis=1) >= floor)
                return first_active + int(crossings[0]) if len(crossings) else first_active
            first_active = start
        else:
            first_active = None
    # A very short one-shot may not fill two blocks; preserve its onset.
    crossings = np.flatnonzero(np.max(np.abs(x), axis=1) >= floor)
    if len(crossings):
        return int(crossings[0])
    raise ValueError("no program above -80 dBFS; refusing to render an all-silent file")


def enforce_two_second_lead(y, sr, encoder_guard_samples=0):
    """Return zeros, then program, with EXACTLY a two-second lead-in (min and max).

    The program samples are untouched. Only the pre-program region is replaced:
    longer silence is trimmed, shorter is padded, so total duration changes by
    (target lead - original lead-in). For MP3, reserve one 1152-sample frame so
    codec delay cannot push the decoded onset past 2 s.
    """
    x = np.asarray(y)
    one_dimensional = x.ndim == 1
    if one_dimensional:
        x = x[:, None]
    onset = find_program_start(x, sr)
    target = int(round(TARGET_SECONDS * sr)) - encoder_guard_samples
    if target <= 0 or encoder_guard_samples < 0:
        raise ValueError("invalid encoder guard")
    zeros = np.zeros((target, x.shape[1]), dtype=x.dtype)
    out = np.concatenate((zeros, x[onset:]), axis=0)
    info = {"before_seconds": onset / sr, "after_seconds": target / sr,
            "duration_change_seconds": (target - onset) / sr, "onset_sample": onset}
    return (out[:, 0] if one_dimensional else out), info
