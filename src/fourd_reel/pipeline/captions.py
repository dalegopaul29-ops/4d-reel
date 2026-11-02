"""Whisper transcription -> styled SRT -> ffmpeg burn-in."""
import subprocess
from pathlib import Path

STYLE = (
    "FontName=Arial,Bold=1,Fontsize=20,PrimaryColour=&H0000FFFF,"
    "OutlineColour=&H00000000,Outline=2,Shadow=1,Alignment=5,MarginV=20"
)


def transcribe_segments(audio_path: Path, model_size: str = "base"):
    try:
        import whisper  # lazy: heavy import, captions extra only
    except ImportError:
        raise SystemExit(
            "Captions need the whisper extra: pip install -e \".\" - your Python "
            "may also be too new for whisper's prebuilt wheels (use Python 3.12-3.13).")
    model = whisper.load_model(model_size)
    result = model.transcribe(str(audio_path), word_timestamps=True)
    return [{"start": s["start"], "end": s["end"], "text": s["text"].strip()}
            for s in result["segments"]]


def segments_to_srt(segments) -> str:
    def ts(t: float) -> str:
        ms = int(round(t * 1000))
        h, ms = divmod(ms, 3600000)
        m, ms = divmod(ms, 60000)
        s, ms = divmod(ms, 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    blocks = []
    for i, seg in enumerate(segments, 1):
        blocks.append(f"{i}\n{ts(seg['start'])} --> {ts(seg['end'])}\n{seg['text']}\n")
    return "\n".join(blocks)


def burn_subtitles(video_path: Path, srt_path: Path, out_path: Path) -> Path:
    vf = f"subtitles='{srt_path.as_posix()}':force_style='{STYLE}'"
    subprocess.run(["ffmpeg", "-y", "-i", str(video_path), "-vf", vf,
                    "-c:a", "copy", str(out_path)], check=True)
    return out_path
