"""Free neural TTS via edge-tts (Microsoft Edge voices). No API key needed.
Browse voices: `edge-tts --list-voices` (e.g. en-US-EmmaMultilingualNeural,
en-ZA-LukeNeural for a South African accent)."""
import asyncio
from pathlib import Path


class EdgeSpeechProvider:
    async def synthesize_async(self, text: str, out_path: Path,
                               voice: str = "en-US-EmmaMultilingualNeural") -> Path:
        import edge_tts  # lazy
        await edge_tts.Communicate(text, voice).save(str(out_path))
        return out_path

    def synthesize(self, text: str, out_path: Path,
                   voice: str = "en-US-EmmaMultilingualNeural") -> Path:
        return asyncio.run(self.synthesize_async(text, out_path, voice))
