#!/usr/bin/env python3
"""Xing/Info VBR header for MP3s produced by lameenc (which writes none).

Why: without a Xing/Info header, players + parsers assume CBR from the first
frame's bitrate and report wildly wrong durations for VBR files (e.g. a 4:47
track shown as 39 min). The audio is fine; only the duration metadata is wrong.

This inserts a standard Xing frame (frames | bytes | TOC) as the FIRST audio
frame, after any ID3v2 tag, LOSSLESSLY (no re-encode). Also usable standalone:
    python3 xing_header.py <file.mp3> [more.mp3 ...]   # repair in place (.bak kept)
    python3 xing_header.py --dry <file.mp3>            # report only
"""
import os, struct, sys

# MPEG1 Layer III bitrate table (kbps). MPEG2/2.5 Layer III differs.
_BR_V1L3 = [0,32,40,48,56,64,80,96,112,128,160,192,224,256,320,0]
_BR_V2L3 = [0,8,16,24,32,40,48,56,64,80,96,112,128,144,160,0]
_SR = {3: [44100,48000,32000], 2: [22050,24000,16000], 0: [11025,12000,8000]}
_SIDE_STEREO = {3: 32, 2: 17}   # MPEG1 / MPEG2-2.5, stereo/joint
_SIDE_MONO   = {3: 17, 2: 9}


def _id3v2_end(d):
    """Return byte offset where audio starts (end of leading ID3v2, else 0)."""
    if d[:3] != b"ID3":
        return 0
    flags = d[5]
    sz = ((d[6] & 0x7f) << 21) | ((d[7] & 0x7f) << 14) | ((d[8] & 0x7f) << 7) | (d[9] & 0x7f)
    end = 10 + sz
    if flags & 0x10:      # footer present
        end += 10
    return end


def scan_frames(d, start=0):
    """Walk valid MPEG frames from `start`. Returns (frames, offsets, sr, mpeg_ver, stereo)."""
    n = len(d)
    i = start
    frames = []
    sr = None
    ver = None
    stereo = True
    while i < n - 4:
        if d[i] == 0xFF and (d[i + 1] & 0xE0) == 0xE0:
            h1, h2, h3 = d[i + 1], d[i + 2], d[i + 3]
            v = (h1 >> 3) & 0x3
            layer = (h1 >> 1) & 0x3
            br_idx = (h2 >> 4) & 0xF
            sr_idx = (h2 >> 2) & 0x3
            pad = (h2 >> 1) & 0x1
            if layer == 1 and v in _SR and sr_idx < 3 and br_idx in range(16):
                table = _BR_V1L3 if v == 3 else _BR_V2L3
                br = table[br_idx]
                if br > 0:
                    srate = _SR[v][sr_idx]
                    if sr is None:
                        sr = srate; ver = v
                        stereo = ((h3 >> 6) & 0x3) != 3
                    spf = 1152 if v == 3 else 576
                    flen = (spf // 8) * br * 1000 // srate + pad
                    frames.append((i, flen))
                    i += flen
                    continue
        i += 1
    return frames, sr, ver, stereo


def has_header(d, start=0):
    first = d[start:start + 4]
    if not (first and first[0] == 0xFF and (first[1] & 0xE0) == 0xE0):
        return False
    w = d[start:start + 200]
    return b"Xing" in w or b"Info" in w


def build_xing(d, start, frames_offsets, sr, ver, stereo):
    """Construct a Xing frame (frames|bytes|toc) sized to a 128kbps frame at sr."""
    nstream = len(frames_offsets)
    header_start = frames_offsets[0][0]
    total_bytes = len(d) - header_start  # audio region incl. this new frame
    side = (_SIDE_STEREO if stereo else _SIDE_MONO)[ver]

    # choose 128 kbps (index 9 in both tables) for the info frame
    br_idx = 9
    table = _BR_V1L3 if ver == 3 else _BR_V2L3
    br = table[br_idx]
    spf = 1152 if ver == 3 else 576
    flen = (spf // 8) * br * 1000 // sr  # no padding
    sr_idx = _SR[ver].index(sr)
    # samplerate index depends on version table: v1 -> [44100,48000,32000] index; ok
    b1 = 0xE0 | (ver << 3) | (1 << 1) | 0x1   # sync+ver+layerIII+noCRC
    b2 = (br_idx << 4) | (sr_idx << 2)
    b3 = (1 << 6) | 0x04                       # joint stereo + original
    header = bytes([0xFF, b1, b2, b3])

    flags = 0x0007  # frames | bytes | TOC
    frames_be = struct.pack(">I", nstream)
    bytes_be = struct.pack(">I", total_bytes)
    # TOC: 100 entries mapping 0..100% time -> position 0..256 of stream
    toc = bytearray(100)
    cum = []
    acc = 0
    for off, ln in frames_offsets:
        acc += ln
        cum.append(acc)
    tot = cum[-1] if cum else 1
    for i in range(100):
        target = i / 100.0 * tot
        # find frame whose cumulative end >= target
        lo, hi = 0, nstream - 1
        while lo < hi:
            mid = (lo + hi) // 2
            if cum[mid] < target:
                lo = mid + 1
            else:
                hi = mid
        toc[i] = min(255, int(256.0 * cum[lo] / tot)) if tot else 0

    tag = b"Xing" + struct.pack(">I", flags) + frames_be + bytes_be + bytes(toc)
    body = header + bytes(side) + tag
    if len(body) > flen:
        raise ValueError(f"Xing frame too small ({flen} < {len(body)}); raise info bitrate")
    body += bytes(flen - len(body))
    return body


def add_xing_to_bytes(d):
    """Return (new_bytes, info) injecting a Xing frame if absent. Idempotent."""
    start = _id3v2_end(d)
    if has_header(d, start):
        return d, "already-has-Xing"
    frames_offsets, sr, ver, stereo = scan_frames(d, start)
    if not frames_offsets or sr is None:
        return d, "no-frames-found"
    xf = build_xing(d, start, frames_offsets, sr, ver, stereo)
    new = d[:start] + xf + d[start:]
    dur = len(frames_offsets) * (1152 if ver == 3 else 576) / sr
    return new, f"added Xing: {len(frames_offsets)} frames, {dur:.2f}s @ {sr}Hz"


def repair(path, dry=False):
    with open(path, "rb") as f:
        d = f.read()
    new, info = add_xing_to_bytes(d)
    if new is d or info == "already-has-Xing":
        return info
    if dry:
        return info
    if not os.path.exists(path + ".bak"):
        with open(path + ".bak", "wb") as f:
            f.write(d)
    with open(path, "wb") as f:
        f.write(new)
    return info


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry" in sys.argv
    if not args:
        sys.exit("usage: xing_header.py <file.mp3> [...] [--dry]")
    for p in args:
        print(f"{os.path.basename(p):34s} {repair(p, dry)}")
