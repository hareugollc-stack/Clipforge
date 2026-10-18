"""
Local transcription with faster-whisper (no API key, no cost).

Returns segments: [{start, end, text, words:[{word, start, end}]}]
"""
import os

_model = None


def _patch_av():
    """faster-whisper passes metadata_errors to av.open, which newer
    PyAV removed. Strip the kwarg via a thin wrapper."""
    try:
        import av
        import inspect
        try:
            inspect.signature(av.open)
        except (ValueError, TypeError):
            _orig_open = av.open

            def _open(*a, **k):
                k.pop("metadata_errors", None)
                return _orig_open(*a, **k)
            av.open = _open
    except ImportError:
        pass


_patch_av()


def get_model(size="base"):
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        # int8 = fast on CPU, good accuracy/size tradeoff
        _model = WhisperModel(size, device="cpu", compute_type="int8")
    return _model


def transcribe(video_path, model_size="base"):
    """Transcribe a video file. Returns (segments, info)."""
    model = get_model(model_size)
    segments_iter, info = model.transcribe(
        video_path, beam_size=5, word_timestamps=True,
        vad_filter=True,  # skip silence/noise
        vad_parameters={"min_silence_duration_ms": 500},
    )
    segments = []
    for s in segments_iter:
        words = []
        if s.words:
            for w in s.words:
                words.append({"word": w.word.strip(), "start": w.start, "end": w.end})
        segments.append({
            "start": s.start, "end": s.end,
            "text": s.text.strip(), "words": words,
        })
    return segments, {"language": info.language,
                      "duration": info.duration if hasattr(info, "duration") else None}


if __name__ == "__main__":
    import sys, json
    segs, info = transcribe(sys.argv[1])
    print(json.dumps({"info": info, "segments": segs[:3]}))
    print(f"... {len(segs)} segments total")
