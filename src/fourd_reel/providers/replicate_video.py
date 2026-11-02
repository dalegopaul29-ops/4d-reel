"""BYOK cloud video generation via Replicate.

Model slugs are user-configurable: the open-weights landscape moves fast, so you
swap slugs, not pipeline code. Verify current slugs in the Replicate library.
"""
import os
import urllib.request
from pathlib import Path
from ..models import RenderJob


class ReplicateVideoProvider:
    # Examples only — confirm live slugs before relying on them.
    DEFAULT_T2V_SLUG = "wavespeedai/wan-2.2-t2v"
    DEFAULT_I2V_SLUG = "wavespeedai/wan-2.2-i2v"

    def __init__(self, token: str = None, t2v_slug: str = None, i2v_slug: str = None):
        os.environ["REPLICATE_API_TOKEN"] = token or os.environ.get("REPLICATE_API_TOKEN", "")
        self.t2v_slug = t2v_slug or self.DEFAULT_T2V_SLUG
        self.i2v_slug = i2v_slug or self.DEFAULT_I2V_SLUG

    def generate(self, job: RenderJob, out_path: Path) -> Path:
        import replicate  # lazy
        use_i2v = job.kind == "image_to_video" and job.reference_image
        slug = self.i2v_slug if use_i2v else self.t2v_slug
        inputs = {
            "prompt": job.prompt,
            "negative_prompt": job.negative_prompt,
            "aspect_ratio": job.aspect_ratio,
            # most open video models want frame counts in multiples of 8, ~16 fps
            "num_frames": max(16, int(job.seconds * 16) // 8 * 8),
        }
        if use_i2v:
            inputs["image"] = open(job.reference_image, "rb")
        output = replicate.run(slug, input=inputs)
        url = output[0] if isinstance(output, list) else output
        urllib.request.urlretrieve(url, out_path)
        return out_path
