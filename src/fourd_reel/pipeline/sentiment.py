"""Pillar 2 — Biometric & Neuro-Adaptive Script Evolution (2026-honest).

DEFAULT INPUT IS TEXT ONLY (stream chat, comments, poll votes). Camera-based
gaze/micro-expression tracking requires explicit, informed, per-session consent
and is POPIA-sensitive — if ever added, it lives behind a consent gate as an
optional plugin, never as a default. This module never sees biometric data.
"""
import re
from typing import Dict
from ..models import PlotBranch

# Lightweight arousal lexicon; extend freely.
_AROUSAL = ("run", "dont", "behind you", "omg", "no no", "gasp", "scream",
            "watch out", "hide", "danger", "plot twist", "what",
            "justice", "revenge", "caught", "liar")


def parse_feedback_vector(raw: str) -> Dict:
    """Turn raw audience text into a compact metric vector. Pure + testable."""
    low = raw.lower()
    hits = sum(low.count(w) for w in _AROUSAL)
    n_words = max(1, len(low.split()))
    intensity = min(1.0, hits / max(3, n_words / 12))
    # specific emotions first, arousal-count fallback, calm last - never first
    if any(w in low for w in ("cry", "cried", "sad", "heart", "tears")):
        emotion = "empathy"
    elif any(w in low for w in ("angry", "hate", "justice", "revenge")):
        emotion = "outrage"
    elif hits > 0:
        emotion = "fear"
    else:
        emotion = "calm"
    return {"arousal": round(intensity, 2), "dominant_emotion": emotion,
            "cue_count": hits, "raw_excerpt": raw[:160]}


def branch_plot(current_story: str, feedback_vector: Dict,
                script_provider=None, metrics_raw: str = "") -> PlotBranch:
    """Compute a narrative branch from the metric vector. Uses the configured
    script provider (Gemini BYOK); falls back to a deterministic template."""
    vec = parse_feedback_vector(metrics_raw) if metrics_raw else feedback_vector
    prompt = (f"CURRENT SHOW STATE: {current_story}\n"
              f"AUDIENCE METRICS: arousal={vec['arousal']}, dominant_emotion={vec['dominant_emotion']}, "
              f"cues={vec['cue_count']}. Excerpt: {vec['raw_excerpt']}\n"
              "Pivot the plot toward the audience's dominant emotion while keeping "
              "character core archetypes intact.")
    if script_provider is not None:
        return script_provider.branch(prompt)  # providers may expose branch()
    # Deterministic fallback so the pipeline never blocks on a key.
    return PlotBranch(
        chosen_path_title=f"Pivot: {vec['dominant_emotion'].title()} Surge",
        narrative_justification=f"Arousal {vec['arousal']} with {vec['dominant_emotion']} cues.",
        next_immediate_hook="The door opens — but it is not who anyone expected.",
        visual_prompt_shift="Tighter framing, colder grade, slower push-in.",
        new_dialogue="You should not have come here.",
        mood_shift="tense",
    )
