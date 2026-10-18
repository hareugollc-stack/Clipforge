"""
Render a clip: cut segment, center-crop to 9:16, scale to 1080x1920,
burn karaoke-style word captions (ASS subtitles), output mp4.

Caption style: bold white words, black outline; the currently-spoken
word highlights in gold — the Hormozi-style look, no API needed.
"""
import os
import subprocess

W, H = 1080, 1920
GOLD = "&H0000D0F0"   # ASS color (AABBGGRR): gold #F0D000
WHITE = "&H00FFFFFF"
BLACK = "&H00000000"


def _escape(text):
    return text.replace("{", r"\{").replace("}", r"\}")


def build_ass(words, clip_start, ass_path, max_words_per_line=5):
    """Write an ASS subtitle file with word-level karaoke timing."""
    # group words into readable lines
    lines, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) >= max_words_per_line:
            lines.append(cur)
            cur = []
    if cur:
        lines.append(cur)

    events = []
    for line in lines:
        lstart = line[0]["start"] - clip_start
        lend = line[-1]["end"] - clip_start
        parts = []
        for w in line:
            dur_cs = max(1, int((w["end"] - w["start"]) * 100))
            parts.append(r"{\k%d}%s" % (dur_cs, _escape(w["word"])))
        events.append("Dialogue: 0,%s,%s,Captions,,0,0,0,,%s" % (
            _ts(lstart), _ts(lend), " ".join(parts)))

    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Captions,DejaVu Sans,72,%s,%s,%s,%s,-1,0,0,0,100,100,0,0,1,4,0,2,60,60,180,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" % (WHITE, GOLD, BLACK, BLACK)
    with open(ass_path, "w") as f:
        f.write(header + "\n".join(events) + "\n")
    return ass_path


def _ts(s):
    h, rem = divmod(max(0, s), 3600)
    m, sec = divmod(rem, 60)
    return "%d:%02d:%05.2f" % (h, m, sec)


def render_clip(video_path, clip, out_path, crf=20):
    """Cut + crop + caption one clip. Returns out_path."""
    start, end = clip["start"], clip["end"]
    ass_path = out_path + ".ass"
    build_ass(clip["words"], start, ass_path)

    # escape for ffmpeg ass filter (single quotes inside filter arg)
    ass_escaped = ass_path.replace("'", r"'\''").replace(":", r"\:")
    vf = (
        "crop=ih*9/16:ih:(iw-ih*9/16)/2:0,"  # center 9:16 crop
        "scale=1080:1920,"
        "ass='%s'," % ass_escaped +
        "format=yuv420p"  # phones can't decode the yuv444p that ass outputs
    )
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start), "-to", str(end),
        "-i", video_path,
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", str(crf),
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        out_path,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    try:
        os.remove(ass_path)
    except OSError:
        pass
    if r.returncode != 0:
        raise RuntimeError("ffmpeg failed: " + r.stderr[-2000:])
    return out_path


def probe_duration(video_path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", video_path],
        capture_output=True, text=True)
    return float(r.stdout.strip())
