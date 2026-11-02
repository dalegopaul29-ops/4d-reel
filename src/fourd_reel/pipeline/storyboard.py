"""Project scaffolding.

A project on disk is just a folder + episode.json + assets/ — inspectable and
hand-editable at any point, which is deliberate: you can fix any scene by hand
and re-run assembly without regenerating anything else.
"""
from pathlib import Path
from ..models import Episode, RenderJob, Character, Scene


def init_project(episode: Episode, root: Path) -> Path:
    slug = "".join(c if c.isalnum() else "_" for c in episode.title.lower()).strip("_")
    ep_dir = Path(root) / slug
    (ep_dir / "assets").mkdir(parents=True, exist_ok=True)
    (ep_dir / "episode.json").write_text(episode.model_dump_json(indent=2))
    for sc in episode.scenes:
        (ep_dir / "assets" / f"scene_{sc.scene_number:02d}").mkdir(exist_ok=True)
    return ep_dir


def _character_for(episode: Episode, scene) -> Character | None:
    for ch in episode.characters:
        if ch.name.lower() in scene.visual_prompt.lower():
            return ch
    return None


def jobs_for(episode: Episode):
    """Map scenes to render jobs. A scene that names a character with a
    reference image automatically becomes image-to-video (face-lock)."""
    for sc in episode.scenes:
        ref = sc.character_ref
        if ref is None:
            ch = _character_for(episode, sc)
            if ch is not None and ch.reference_image:
                ref = ch.reference_image
        yield f"scene_{sc.scene_number:02d}", RenderJob(
            kind="image_to_video" if ref else "text_to_video",
            prompt=sc.visual_prompt,
            seconds=sc.target_seconds,
            aspect_ratio=episode.aspect_ratio,
            reference_image=ref,
        )


def template_episode(premise: str, num_scenes: int = 4) -> Episode:
    """Offline storyboard: generic beat structure with the premise embedded.
    Used by `reel new --offline` so the full pipeline is demoable without a key.
    Replace with the Gemini writer the moment a key is present."""
    beats = ["establish the world and the protagonist",
             "introduce the tension",
             "the twist",
             "the cliffhanger"]
    scenes = []
    for i in range(num_scenes):
        beat = beats[i] if i < len(beats) else "develop the story"
        scenes.append(Scene(
            scene_number=i + 1,
            visual_prompt="%s - scene %d: %s. One continuous shot, cinematic."
                          % (premise, i + 1, beat),
            dialogue="",
            on_screen_text=premise if i == 0 else "",
            mood="cinematic"))
    return Episode(title=premise[:40], hook=premise[:80], scenes=scenes)
