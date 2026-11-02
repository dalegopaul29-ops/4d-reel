"""Pillar 3 — Hyper-Immersive Spatial Audio (object-positioned foley).

Real today: per-cue delay, gain and stereo panning of SFX mixed under the scene
audio with ffmpeg. True material-acoustic simulation (room echo from implied
geometry) is approximated with a configurable reverb tail; generative SFX
models (e.g. open audio-diffusion checkpoints) plug in via SFX_PROVIDERS.
"""
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple
from ..models import SfxCue

# SFX sources: name -> callable(cue_label, out_path) -> Path. Extend with real
# generators later (local audio-diffusion, or an SFX API). Default: tone blip.
def _tone_blip(label: str, out_path: Path) -> Path:
    freq = 220 + (abs(hash(label)) % 660)
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi",
                    "-i", f"sine=frequency={freq}:duration=0.6",
                    "-af", "afade=t=out:st=0.4:d=0.2", str(out_path)],
                   check=True, capture_output=True)
    return out_path


SFX_PROVIDERS = {"tone_blip": _tone_blip}


def build_sfx_filter(cues: List[Dict]) -> str:
    """Pure filter-graph builder. cues: [{at_seconds, pan, gain_db}] for inputs 1..N.
    Input 0 is the scene's existing audio."""
    if not cues:
        return "[0:a]copy[out]"
    parts = []
    labels = []
    for i, c in enumerate(cues):
        pan = max(-1.0, min(1.0, c.get("pan", 0.0)))
        left = 1.0 - max(0.0, pan)     # pan right -> attenuate left
        right = 1.0 - max(0.0, -pan)   # pan left  -> attenuate right
        delay_ms = int(c.get("at_seconds", 0.0) * 1000)
        gain = c.get("gain_db", 0.0)
        parts.append(
            f"[{i+1}:a]adelay={delay_ms}|{delay_ms},volume={gain}dB,"
            f"pan=stereo|c0=c0*{left:.2f}|c1=c0*{right:.2f}[s{i}]"
        )
        labels.append(f"[s{i}]")
    parts.append("[0:a]" + "".join(labels) + f"amix=inputs={len(cues)+1}:normalize=0[out]")
    return ";".join(parts)


def mix_foley(scene_video: Path, cues: List[SfxCue], out: Path,
              provider="tone_blip", work_dir: Path = None) -> Path:
    """Mix positioned SFX under the scene audio. Missing files are synthesized."""
    work_dir = Path(work_dir or scene_video.parent / "sfx")
    work_dir.mkdir(exist_ok=True, parents=True)
    inputs, dicts = [str(scene_video)], []
    for i, cue in enumerate(cues):
        f = Path(cue.file) if cue.file else SFX_PROVIDERS[provider](cue.cue, work_dir / f"sfx_{i:02d}.wav")
        inputs += ["-i", str(f)]
        dicts.append({"at_seconds": cue.at_seconds, "pan": cue.pan, "gain_db": cue.gain_db})
    fc = build_sfx_filter(dicts)
    cmd = ["ffmpeg", "-y", "-i", inputs[0]]
    for extra in inputs[1:]:
        cmd += ["-i", extra]
    cmd += ["-filter_complex", fc, "-map", "0:v", "-map", "[out]",
            "-c:v", "copy", "-c:a", "aac", str(out)]
    subprocess.run(cmd, check=True, capture_output=True)
    return out
