# Pillar 1 hardening - `reel cast`: generate a reference portrait per character so
# character_ref is ALWAYS populated and scenes inherit it automatically.
from pathlib import Path
from ..models import Character


def slug(name: str) -> str:
    return ''.join(c if c.isalnum() else '_' for c in name.lower()).strip('_')


def portrait_prompt(char: Character) -> str:
    p = ('Photorealistic head-and-shoulders portrait of ' + char.anchor_description.rstrip('.')
         + (', wearing ' + char.wardrobe.rstrip('.') if char.wardrobe else '')
         + ', facing the camera directly, neutral expression, soft studio lighting, '
           'plain dark background, sharp focus on face, 85mm portrait lens')
    return p


def ensure_cast_images(ep_dir: Path, characters, provider, force=False):
    ep_dir = Path(ep_dir)
    cast_dir = ep_dir / 'assets' / 'cast'
    cast_dir.mkdir(parents=True, exist_ok=True)
    made, skipped = [], []
    for ch in characters:
        if ch.reference_image and Path(ch.reference_image).exists() and not force:
            skipped.append(ch.name)
            continue
        out = cast_dir / (slug(ch.name) + '.png')
        provider.generate(portrait_prompt(ch), out)
        ch.reference_image = str(out)
        made.append(ch.name)
    return made, skipped
