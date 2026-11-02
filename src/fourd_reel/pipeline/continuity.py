"""Pillar 1 — Persistent Asset Context (the 2026-honest version).

True volumetric world models are research-stage. What ACTUALLY stops characters
morphing across calls today: (a) a fixed reference image, (b) a verbatim anchor
block injected into every prompt, (c) fixed seeds, (d) an explicit state journal
the writer model must respect. This module enforces b and d.
"""
from pathlib import Path
from typing import List
from ..models import Episode, Character, ContinuityBook

BOOK_FILE = "continuity.json"


def build_book(episode: Episode) -> ContinuityBook:
    return ContinuityBook(characters=episode.characters,
                          state=dict(episode.state))


def save_book(book: ContinuityBook, ep_dir: Path) -> Path:
    p = Path(ep_dir) / BOOK_FILE
    p.write_text(book.model_dump_json(indent=2))
    return p


def load_book(ep_dir: Path) -> ContinuityBook:
    return ContinuityBook.model_validate_json((Path(ep_dir) / BOOK_FILE).read_text())


def anchor_block(char: Character) -> str:
    block = char.anchor_description.rstrip(".")
    if char.wardrobe:
        block += f", wearing {char.wardrobe.rstrip('.')}"
    return block + "."


def inject_anchors(episode: Episode, book: ContinuityBook) -> int:
    """Append each referenced character's anchor block to its scene prompt if absent.
    Returns number of injections made. Mutates the episode in place."""
    injections = 0
    for scene in episode.scenes:
        prompt = scene.visual_prompt
        for char in book.characters:
            named = char.name.lower() in prompt.lower()
            if named and anchor_block(char) not in prompt:
                prompt = prompt.rstrip(".") + ". " + anchor_block(char)
                injections += 1
        scene.visual_prompt = prompt
    return injections


def consistency_report(episode: Episode, book: ContinuityBook) -> List[str]:
    """Flag scenes that name a character but lack the locked anchor (morph risk)."""
    problems = []
    for scene in episode.scenes:
        for char in book.characters:
            if char.name.lower() in scene.visual_prompt.lower() and anchor_block(char) not in scene.visual_prompt:
                problems.append(f"scene {scene.scene_number}: '{char.name}' named but anchor missing")
            if char.reference_image is None and char.name.lower() in scene.visual_prompt.lower():
                problems.append(f"scene {scene.scene_number}: '{char.name}' has no reference image (face-lock weak)")
    return problems


def update_state(book: ContinuityBook, event: str, value: str) -> ContinuityBook:
    """Journal a world-state change (e.g. location='office', prop='safe_key')."""
    book.state[event] = value
    return book
