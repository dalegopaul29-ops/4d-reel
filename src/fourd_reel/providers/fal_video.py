# BYOK video generation via fal.ai - RECOMMENDED PRIMARY PROVIDER.
# Why fal first (decision log 2026-10-23): fastest cold-starts for batch scene
# rendering, pay-per-use open weights (Wan 2.2 class), ~$0.10-0.40 per 5s clip;
# roughly 3-10x cheaper per episode than direct Kling/Runway APIs. Stdlib only.
# NOTE: model slugs move fast - verify against the fal.ai model library.
import base64
import json
import os
import urllib.request
from pathlib import Path
from ..models import RenderJob

BASE = 'https://fal.run/'


def _image_url(reference):
    if reference.startswith(('http://', 'https://', 'data:')):
        return reference
    data = Path(reference).read_bytes()
    return 'data:image/png;base64,' + base64.b64encode(data).decode()


class FalVideoProvider:
    DEFAULT_T2V = 'fal-ai/wan-2.2/t2v'   # verify current slug
    DEFAULT_I2V = 'fal-ai/wan-2.2/i2v'   # verify current slug

    def __init__(self, key=None, t2v_slug=None, i2v_slug=None):
        self.key = key or os.environ.get('FAL_KEY', '')
        if not self.key:
            raise RuntimeError('FAL_KEY missing - set it in .env')
        self.t2v_slug = t2v_slug or self.DEFAULT_T2V
        self.i2v_slug = i2v_slug or self.DEFAULT_I2V

    def generate(self, job: RenderJob, out_path: Path) -> Path:
        use_i2v = job.kind == 'image_to_video' and job.reference_image
        slug = self.i2v_slug if use_i2v else self.t2v_slug
        payload = {
            'prompt': job.prompt,
            'num_frames': max(16, int(job.seconds * 16) // 8 * 8),
            'aspect_ratio': job.aspect_ratio,
            'enable_safety_checker': True,
        }
        if use_i2v:
            payload['image_url'] = _image_url(job.reference_image)
        req = urllib.request.Request(
            BASE + slug,
            data=json.dumps(payload).encode(),
            headers={'Authorization': 'Key ' + self.key,
                     'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=900) as r:
            resp = json.loads(r.read())
        urllib.request.urlretrieve(resp['video']['url'], out_path)
        return out_path
