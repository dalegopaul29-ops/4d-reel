'''Scene mux + vertical conform + concat. ffmpeg only — no editor needed.'''
import subprocess
from pathlib import Path


def _run(cmd):
    subprocess.run(cmd, check=True)


def mux_voice(scene_video: Path, voice: Path, out: Path) -> Path:
    _run(["ffmpeg", "-y", "-i", str(scene_video), "-i", str(voice),
          "-c:v", "copy", "-c:a", "aac", "-shortest", str(out)])
    return out


def conform_vertical(scene: Path, out: Path, target: str = "1080x1920") -> Path:
    w, h = map(int, target.split("x"))
    vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}"
    _run(["ffmpeg", "-y", "-i", str(scene), "-vf", vf, "-c:a", "copy", str(out)])
    return out


def concat_scenes(scene_paths, out: Path) -> Path:
    listfile = out.parent / "concat_list.txt"
    listfile.write_text("".join(f"file '{p.as_posix()}'\n" for p in scene_paths))
    _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listfile),
          "-c", "copy", str(out)])
    return out


def concat_audio(audio_paths, out: Path) -> Path:
    inputs = []
    for i, a in enumerate(audio_paths):
        inputs += ["-i", str(a)]
    chain = "".join(f"[{i}:a]" for i in range(len(audio_paths)))
    fc = f"{chain}concat=n={len(audio_paths)}:v=0:a=1[out]"
    _run(["ffmpeg", "-y", *inputs, "-filter_complex", fc, "-map", "[out]", str(out)])
    return out
