"""Storyboard writer backed by Gemini (BYOK), with forced structured JSON output."""
import os
from ..models import Episode


class GeminiScriptProvider:
    def __init__(self, api_key: str = None, model: str = "gemini-2.5-flash"):
        from google import genai  # lazy: keeps CLI light when only editing
        self.client = genai.Client(api_key=api_key or os.environ.get("GEMINI_API_KEY"))
        self.model = model

    def write_storyboard(self, premise: str, num_scenes: int = 4) -> Episode:
        from google.genai import types
        instructions = (
            "You are a writer-producer of viral vertical short-drama (TikTok/Reels). "
            "Rules: (1) the hook must be the single most dramatic beat and appears in scene 1; "
            "(2) each visual_prompt describes ONE continuous shot: subject, action, setting, "
            "lighting, camera move; (3) dialogue must be speakable within target_seconds at "
            "natural pace; (4) reuse identical character descriptions across scenes so a "
            "reference-image workflow can lock identity."
        )
        prompt = (
            f"Write a {num_scenes}-scene vertical drama episode from this premise: {premise}. "
            "Provide title, hook, and per-scene visual_prompt, dialogue, on_screen_text, "
            "mood, target_seconds."
        )
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=instructions,
                response_mime_type="application/json",
                response_schema=Episode,
                temperature=0.85,
            ),
        )
        return Episode.model_validate_json(response.text)
