#!/usr/bin/env python3
"""House MP3 export: 48kHz, 320kbps-ceiling VBR, 16-bit stereo + house ID3 defaults. numpy+lameenc+mutagen.
Usage: export_mp3.py <in.wav> <out.mp3> [--rate 48000 --bitrate 320] [--title T] [--artist A] [--album B] [--year Y] [--composer C]
   or: export_mp3.py <existing.mp3>  (retag-only: apply house defaults, no re-encode)
House tags (ID3v2.3, UTF-8): Title = output filename minus extension. Album-level tags
(TALB/TPE1/TPE2/TCOM/TDRC) are INHERITED from an existing sibling .mp3 in the destination folder
when one exists — a new track follows the album's already-tagged MP3s; --album/--artist/--composer/
--year override. With no sibling, Album = SOURCE file's project ROOT dir name, Artist/AlbumArtist =
Zack Yusof, Composer = Artist, Year = current year (verified live).
Final MP3 renders reserve one encoder frame below the 2-second leading-silence ceiling.
Missing-field rule (user directive): if title/album resolve empty and no override is given, exit
non-zero naming the missing field so the user can supply it — never ship untagged masters.
Why lameenc, not afconvert: this host's afconvert MPG3 encoder fails ('fmt?' — encode path
unavailable on macOS 27; AAC path works but user spec is MP3). pip install lameenc (wheels bundle
libmp3lame, no system lame/ffmpeg needed). VBR_MTRH q0, mean=ceiling 320 / min 128 — dense mixes
land ~250kbps avg; the 320 is the ceiling, actual average is always reported. 16-bit = int16 PCM
feed (decoded MP3 yields 16-bit PCM on playback). Resamples via polyphase only if input != 48k."""
import datetime
import os
import sys
import numpy as np

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
from analyze_audio import load

HOUSE_ARTIST = "Zack Yusof"

def _sibling_album_tags(dst):
    """Album-level tags from an existing sibling .mp3 in dst's folder (deliverable convention:
    a new track follows the album's already-tagged MP3s). Returns {} if none exist or unreadable."""
    import glob
    folder = os.path.dirname(os.path.abspath(dst))
    own = os.path.abspath(dst)
    for p in sorted(glob.glob(os.path.join(folder, "*.mp3"))):
        if os.path.abspath(p) == own:
            continue
        try:
            from mutagen.id3 import ID3
            t = ID3(p)
        except Exception:
            continue
        got = {k: str(t.get(k)) for k in ("TALB", "TPE1", "TPE2", "TCOM", "TDRC") if t.get(k)}
        if got:
            return got
    return {}


def house_tags(dst, src_for_album, opt):
    title = opt.get("title") or os.path.splitext(os.path.basename(dst))[0]
    sib = _sibling_album_tags(dst)  # existing album MP3s win over the folder name
    d = os.path.dirname(os.path.abspath(src_for_album))
    if os.path.basename(d).lower() in ("mp3", "mastered", "output", "out", "tmp", "temp"):
        d = os.path.dirname(d)  # deliverable container dirs are not album names — use project root
    album = opt.get("album") or sib.get("TALB") or os.path.basename(d)
    artist = opt.get("artist") or sib.get("TPE1") or HOUSE_ARTIST
    albumartist = sib.get("TPE2") or artist
    composer = opt.get("composer") or sib.get("TCOM") or artist
    year = opt.get("year") or sib.get("TDRC") or str(datetime.datetime.now().year)
    missing = [n for n, v in (("title", title), ("album", album), ("artist", artist), ("year", year)) if not (v or "").strip()]
    if missing:
        sys.exit(f"missing ID3 fields (no default resolvable): {', '.join(missing)} — supply via --title/--artist/--album/--year")
    from mutagen.mp3 import MP3
    from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TPE2, TCOM
    audio = MP3(dst, ID3=ID3)
    if audio.tags is None:
        audio.add_tags()
    audio.tags.add(TIT2(encoding=3, text=title))
    audio.tags.add(TPE1(encoding=3, text=artist))
    audio.tags.add(TALB(encoding=3, text=album))
    audio.tags.add(TDRC(encoding=3, text=year))
    audio.tags.add(TPE2(encoding=3, text=albumartist))
    audio.tags.add(TCOM(encoding=3, text=composer))
    audio.save(v2_version=3)
    return title, artist, album, year

def main():
    a = sys.argv
    if len(a) < 2 or (len(a) < 3 and not a[1].lower().endswith(".mp3")):
        sys.exit("usage: export_mp3.py <in.wav> <out.mp3> [options] | export_mp3.py <existing.mp3> (retag-only)")
    if a[1].lower().endswith(".mp3"):
        src, dst = None, a[1]
    else:
        src, dst = a[1], a[2]
    opt = {}
    for k in ("--title", "--artist", "--album", "--year", "--composer"):
        if k in a:
            opt[k[2:]] = a[a.index(k) + 1]
    if src is None:  # retag-only
        t = house_tags(dst, dst, opt)
        print(f"retagged {dst}: title={t[0]} artist={t[1]} album={t[2]} year={t[3]}")
        return
    rate = int(a[a.index("--rate") + 1]) if "--rate" in a else 48000
    ceil = int(a[a.index("--bitrate") + 1]) if "--bitrate" in a else 320
    y, sr = load(src)
    if y.shape[1] == 1:
        y = np.repeat(y, 2, axis=1)
        print("mono -> dual-mono stereo (spec is stereo)")
    if sr != rate:
        from scipy.signal import resample_poly
        import math
        g = math.gcd(sr, rate)
        y = resample_poly(y, rate // g, sr // g, axis=0).astype(np.float64)
        print(f"resampled {sr} -> {rate}Hz (polyphase)")
        sr = rate
    peak = float(np.abs(y).max())
    if peak >= 1.0:
        y = y * 0.99 / peak
        print(f"scaled {peak:.3f}->0.99 pre-encode")
    from lead_in import enforce_two_second_lead
    y, lead = enforce_two_second_lead(y, sr, encoder_guard_samples=1152)
    print(f"lead-in: {lead['before_seconds']:.3f}s -> {lead['after_seconds']:.3f}s PCM silence "
          f"(one MP3 frame reserved; duration {lead['duration_change_seconds']:+.3f}s)")
    pcm = (np.clip(y, -1, 1) * 32767).astype('<i2')
    import lameenc
    enc = lameenc.Encoder()
    enc.set_bit_rate(ceil)
    enc.set_in_sample_rate(sr)
    enc.set_out_sample_rate(sr)
    enc.set_channels(2)
    enc.set_quality(2)
    enc.set_vbr(lameenc.VBR_MTRH)
    enc.set_vbr_quality(0)
    enc.set_vbr_mean_bitrate_kbps(ceil)
    enc.set_vbr_min_bitrate_kbps(128)
    enc.set_vbr_max_bitrate_kbps(ceil)
    mp3 = enc.encode(pcm.tobytes()) + enc.flush()
    assert mp3[:2] == b'\xff\xfb' or mp3[0] == 0xFF, "no MP3 frame sync — encode failed"
    # lameenc writes NO Xing/Info VBR header -> players report bogus durations for
    # VBR files (assume CBR from first frame bitrate). Inject one, losslessly.
    from xing_header import add_xing_to_bytes
    mp3, xinfo = add_xing_to_bytes(mp3)
    print(f"vbr header: {xinfo}")
    with open(dst, 'wb') as f:
        f.write(mp3)
    dur = len(y) / sr
    avg = len(mp3) * 8 / dur / 1000
    print(f"wrote {dst} 48kHz stereo VBR ceiling {ceil}k avg {avg:.0f}k 16-bit {dur:.1f}s")
    t = house_tags(dst, src, opt)
    print(f"tagged: title={t[0]} artist={t[1]} album={t[2]} year={t[3]} +albumartist/composer")
    # HARD GATE: the tagged MP3 must report the SAME duration as the rendered PCM. Guards
    # against a missing Xing/Info VBR header (lameenc writes none) => players show a
    # bogus duration (4:47 track as ~39 min). Never ship an MP3 that fails this.
    from mutagen.mp3 import MP3
    reported = MP3(dst).info.length
    if abs(reported - dur) > 0.5:
        try:
            os.remove(dst)
        except OSError:
            pass
        sys.exit(f"FATAL: {dst} reports {reported:.2f}s but rendered PCM is {dur:.2f}s "
                 f"(VBR/Xing header missing or broken) — file removed, do NOT ship")
    print(f"verify: mp3 duration {reported:.2f}s == rendered PCM {dur:.2f}s OK")

if __name__ == "__main__":
    main()
