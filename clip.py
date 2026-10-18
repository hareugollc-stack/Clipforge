#!/usr/bin/env python3
"""
ClipForge v1 — local AI clipper.

    python clip.py input.mp4 [--clips 5] [--out output_dir]

Pipeline: faster-whisper transcription → virality scoring →
ffmpeg 9:16 cuts with karaoke captions. No API keys, no cost,
no watermark, no expiring exports.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from transcribe import transcribe
from score import find_moments, make_hashtags
from render import render_clip, probe_duration


def main():
    ap = argparse.ArgumentParser(description="ClipForge — local AI video clipper")
    ap.add_argument("input", help="input video file")
    ap.add_argument("--clips", type=int, default=5, help="max clips to render")
    ap.add_argument("--out", default="output", help="output directory")
    ap.add_argument("--min-score", type=float, default=50,
                    help="minimum virality score (0-100)")
    ap.add_argument("--model", default="base", help="whisper model size")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    base = os.path.splitext(os.path.basename(args.input))[0]

    print("[1/4] Transcribing (local whisper, free)...")
    segments, info = transcribe(args.input, args.model)
    print(f"      {len(segments)} segments, language={info.get('language')}")

    print("[2/4] Scoring moments for virality...")
    moments = find_moments(segments, min_score=args.min_score)
    print(f"      {len(moments)} candidate moments found")
    if not moments:
        print("No moments above the score threshold. Try --min-score 40.")
        return

    print("[3/4] Rendering clips (9:16 + karaoke captions)...")
    results = []
    for i, m in enumerate(moments[:args.clips]):
        out = os.path.join(args.out, f"{base}-clip{i+1:02d}-{int(m['score'])}.mp4")
        render_clip(args.input, m, out)
        tags = make_hashtags(m["text"])
        results.append({
            "file": out, "score": m["score"],
            "start": m["start"], "end": m["end"],
            "title": m["title"], "hashtags": tags,
        })
        print(f"      clip {i+1}: score={m['score']} "
              f"{m['start']:.0f}s→{m['end']:.0f}s → {os.path.basename(out)}")

    manifest = os.path.join(args.out, f"{base}-clips.json")
    with open(manifest, "w") as f:
        json.dump(results, f, indent=2)
    print(f"[4/4] Done. {len(results)} clips + manifest: {manifest}")
    for r in results:
        print(f"  - {r['title']}  {' '.join(r['hashtags'])}")


if __name__ == "__main__":
    main()
