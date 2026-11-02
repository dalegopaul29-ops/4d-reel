"""Pillar 4 — Real-Time Autonomous Live Engine (honest architecture).

Sub-second GENERATION is not real in 2026. What IS real: pre-render the branch
graph (each PlotBranch pre-rendered as a clip), then let live feedback SELECT
the next edge — selection is instant, generation happened ahead of time.
The stream loop never blocks on a renderer.
"""
import json
import subprocess
import time
from pathlib import Path
from typing import Optional

BRANCHES_FILE = "branches.jsonl"


def log_branch(ep_dir: Path, branch: dict, metrics: dict) -> None:
    with open(Path(ep_dir) / BRANCHES_FILE, "a") as f:
        f.write(json.dumps({"ts": time.time(), "metrics": metrics, "branch": branch}) + "\n")


def read_feedback(source: Path) -> Optional[str]:
    """Poll a feedback file (stream chat export, mod bot, poll sink)."""
    p = Path(source)
    if not p.exists():
        return None
    lines = [l for l in p.read_text().splitlines() if l.strip()]
    return lines[-1] if lines else None


def stream_clip(clip: Path, rtmp_url: str) -> None:
    """Push one clip to an RTMP endpoint (TikTok Live/YouTube via ingest URL)."""
    subprocess.run(["ffmpeg", "-re", "-i", str(clip),
                    "-c", "copy", "-f", "flv", rtmp_url], check=True)


def run_live_loop(ep_dir: Path, rtmp_url: str, feedback_source: Path,
                  pick_clip, poll_seconds: float = 2.0) -> None:
    """Core loop: read feedback -> pick next clip -> stream it.
    `pick_clip(ep_dir, metrics) -> Path|None` is YOUR selection policy;
    the default CLI ships a round-robin over rendered branch clips.
    """
    ep_dir = Path(ep_dir)
    while True:
        raw = read_feedback(feedback_source)
        clip = pick_clip(ep_dir, raw)
        if clip is not None:
            stream_clip(clip, rtmp_url)
        time.sleep(poll_seconds)
