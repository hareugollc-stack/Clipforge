# ✂️ ClipForge — local AI video clipper

Upload a video → get back the most viral-ready vertical clips, with
karaoke-style captions, virality scores, auto titles and hashtags.

**No API keys. No cost per video. No watermark. No expiring exports.**

Built to beat the top clipper sites (OpusClip, Vizard, Ssemble, Submagic,
Klap) on the things users complain about most — see `competitor-research.md`.

## How it works

1. **Transcribe** — faster-whisper runs locally (free), word-level timestamps
2. **Score** — every candidate moment gets an honest 0–100 virality score
   (hooks, questions, numbers, emotional charge, payoff — no inflated 90s)
3. **Render** — ffmpeg cuts each moment, center-crops to 9:16, scales to
   1080×1920, and burns Hormozi-style karaoke captions (gold active word)

## Quick start

```bash
python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
# system dep: ffmpeg  (sudo apt install ffmpeg / brew install ffmpeg)

# CLI — one video in, clips out:
./venv/bin/python clip.py myvideo.mp4 --clips 5 --out output

# or paste a link (YouTube etc.) — it downloads then clips:
./venv/bin/python clip.py --url "https://www.youtube.com/watch?v=..."

# Web UI:
./venv/bin/python web/app.py   # → http://localhost:5057  (upload or paste a link)
```

Note: model download needs working HTTPS. If your shell has a broken
`no_proxy` with IPv6 brackets (httpx2 chokes on `[::1]`), run with:
`no_proxy="localhost,127.0.0.1" NO_PROXY="localhost,127.0.0.1"`.

## Project layout

```
clip.py              CLI entry point
src/transcribe.py    local whisper transcription
src/score.py         virality scoring + title/hashtag generation
src/render.py        ffmpeg 9:16 cuts + karaoke captions
web/app.py           Flask upload → clips web UI
competitor-research.md  what the top 5 clipper sites do (and get wrong)
samples/             test-video generation
```

## Roadmap

- v2: face/active-speaker tracking for the 9:16 crop (currently center crop)
- v2: paste-a-YouTube-link ingestion
- v2: caption style presets (Submagic-style)
- v3: optional LLM brain for moment detection (FreeLLMAPI allowed here —
  not for hareugo — but its credentials need rotating first)
