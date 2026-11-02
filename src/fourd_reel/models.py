"""Core data contract for the whole pipeline.

Every layer (script, speech, video, assembly) passes these models around,
so no layer ever needs to know about another vendor's SDK or file format.
"""
from typing import List, Literal, Optional, Dict
from pydantic import BaseModel, Field

AspectRatio = Literal["9:16", "16:9", "1:1", "4:5"]


class Scene(BaseModel):
    scene_number: int
    visual_prompt: str = Field(..., description="One continuous shot: subject, action, setting, lighting, camera move.")
    character_ref: Optional[str] = Field(default=None, description="Path/name of a locked reference image for this scene's character.")
    dialogue: str = Field(default="", description="Spoken line; empty means ambience only.")
    on_screen_text: str = Field(default="", description="Short overlay text; the hook lives in scene 1.")
    mood: str = Field(default="cinematic")
    target_seconds: float = Field(default=4.0, ge=1.0, le=15.0)
    sfx: List["SfxCue"] = Field(default_factory=list, description="Object-positioned sound-effect cues for the foley mixer.")


class Character(BaseModel):
    """Pillar 1: a persistent cast member. The anchor_description is reused
    VERBATIM in every prompt referencing this character — that, plus a fixed
    reference image and seed, is the real anti-morph mechanism of 2026."""
    name: str
    anchor_description: str = Field(..., description="Word-for-word visual block reused in every prompt (face, build, distinguishing marks).")
    reference_image: Optional[str] = None
    voice: str = "en-US-EmmaMultilingualNeural"
    wardrobe: str = ""


class SfxCue(BaseModel):
    """Pillar 3: one positioned sound event inside a scene."""
    cue: str = Field(..., description="SFX label, e.g. 'glass_slams_table'.")
    at_seconds: float = 0.0
    pan: float = Field(default=0.0, ge=-1.0, le=1.0, description="-1 hard left, +1 hard right.")
    gain_db: float = 0.0
    file: Optional[str] = Field(default=None, description="Path to SFX audio; None = synthesize/hook.")


class Episode(BaseModel):
    title: str
    hook: str
    aspect_ratio: AspectRatio = "9:16"
    scenes: List[Scene]
    characters: List[Character] = Field(default_factory=list)
    state: Dict[str, str] = Field(default_factory=dict, description="Continuity state journal: location, props, wardrobe flags.")


class RenderJob(BaseModel):
    """One unit of work handed to any video provider."""
    kind: Literal["text_to_video", "image_to_video"]
    prompt: str
    negative_prompt: str = "low quality, watermark, deformed hands, extra fingers, text artifacts"
    seconds: float = 4.0
    aspect_ratio: AspectRatio = "9:16"
    reference_image: Optional[str] = None
    seed: Optional[int] = None


class PlotBranch(BaseModel):
    """Pillar 2: a narrative course-correction computed from live audience feedback."""
    chosen_path_title: str
    narrative_justification: str = Field(description="Why this shift fits the audience's emotional feedback.")
    next_immediate_hook: str = Field(description="The chaotic twist opening the next clip.")
    visual_prompt_shift: str = Field(description="How the visual aesthetic changes to match the new mood.")
    new_dialogue: str = Field(description="The next spoken line reflecting the audience choice.")
    mood_shift: str = "tense"


class ContinuityBook(BaseModel):
    """Pillar 1: the persistent context layer. Saved as continuity.json per project."""
    characters: List[Character] = Field(default_factory=list)
    state: Dict[str, str] = Field(default_factory=dict, description="Current world state: location, held props, wardrobe, time of day.")
