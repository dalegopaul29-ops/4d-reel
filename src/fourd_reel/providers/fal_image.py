# BYOK text-to-image via fal.ai - used by `reel cast` for character reference
# portraits (the face-lock anchor for image-to-video). Stdlib only.
# NOTE: verify slug + image_size options in the fal.ai model library; they move.
import base64
import json
import os
import urllib.request
from pathlib import Path

BASE = 'https://fal.run/'


class FalImageProvider:
    DEFAULT_SLUG = 'fal-ai/flux/schnell'   # fast + cheap; verify current slug

    def __init__(self, key=None, slug=None):
        self.key = key or os.environ.get('FAL_KEY', '')
        if not self.key:
            raise RuntimeError('FAL_KEY missing - set it in .env')
        self.slug = slug or self.DEFAULT_SLUG

    def generate(self, prompt: str, out_path: Path, image_size='square_hd') -> Path:
        payload = {'prompt': prompt, 'image_size': image_size,
                   'num_inference_steps': 4, 'num_images': 1,
                   'enable_safety_checker': True}
        req = urllib.request.Request(
            BASE + self.slug,
            data=json.dumps(payload).encode(),
            headers={'Authorization': 'Key ' + self.key,
                     'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=300) as r:
            resp = json.loads(r.read())
        urllib.request.urlretrieve(resp['images'][0]['url'], out_path)
        return out_path
