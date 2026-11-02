"""Provider interfaces.

Downstream code talks to these protocols, never to a vendor SDK directly.
That is what keeps the tool vendor-neutral: swap providers, keep the pipeline.
"""
from pathlib import Path
from typing import Protocol, runtime_checkable, List, Dict
from ..models import Episode, RenderJob


@runtime_checkable
class ScriptProvider(Protocol):
    def write_storyboard(self, premise: str, num_scenes: int = 4) -> Episode: ...


@runtime_checkable
class SpeechProvider(Protocol):
    def synthesize(self, text: str, out_path: Path,
                   voice: str = "en-US-EmmaMultilingualNeural") -> Path: ...


@runtime_checkable
class VideoProvider(Protocol):
    def generate(self, job: RenderJob, out_path: Path) -> Path: ...


@runtime_checkable
class Transcriber(Protocol):
    def transcribe(self, audio_path: Path) -> List[Dict]:  # [{"start":s,"end":s,"text":str}]
        ...
