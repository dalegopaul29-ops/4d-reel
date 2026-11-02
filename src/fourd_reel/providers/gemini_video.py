# Premium quality tier (BYOK): Google Veo via the Gemini API.
# Honest positioning: fal/Wan = cheap + good; Veo = realistic + pricier.
# Users choose per render. VERIFY the current Veo model id + pricing in the
# Gemini API docs before shipping - model ids for video move frequently.
import time
import os
import urllib.request
from pathlib import Path
from ..models import RenderJob

MODEL_ID = 'veo-3.0-generate-preview'   # verify current id


class GeminiVeoProvider:
    def __init__(self, api_key=None, model=MODEL_ID, poll_seconds=8, max_wait=900):
        from google import genai
        self.client = genai.Client(api_key=api_key or os.environ.get('GEMINI_API_KEY'))
        self.model = model
        self.poll_seconds = poll_seconds
        self.max_wait = max_wait

    def generate(self, job: RenderJob, out_path: Path) -> Path:
        from google.genai import types
        cfg_kwargs = dict(aspect_ratio=job.aspect_ratio,
                          negative_prompt=job.negative_prompt or None)
        if job.kind == 'image_to_video' and job.reference_image:
            img = self.client.files.upload(file=job.reference_image)
            op = self.client.models.generate_videos(
                model=self.model, prompt=job.prompt, image=img,
                config=types.GenerateVideosConfig(**{k: v for k, v in cfg_kwargs.items() if v}))
        else:
            op = self.client.models.generate_videos(
                model=self.model, prompt=job.prompt,
                config=types.GenerateVideosConfig(**{k: v for k, v in cfg_kwargs.items() if v}))
        waited = 0
        while not op.done:
            time.sleep(self.poll_seconds)
            waited += self.poll_seconds
            if waited > self.max_wait:
                raise TimeoutError('Veo render exceeded %ds' % self.max_wait)
            op = self.client.operations.get(op)
        video = op.response.generated_videos[0]
        self.client.files.download(file=video.video)
        Path(out_path).write_bytes(video.video.video_bytes)
        return Path(out_path)
