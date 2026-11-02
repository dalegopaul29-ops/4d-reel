# Offline demo renderer: synthesizes a colour clip with ffmpeg.
# Lets anyone try the full pipeline (UI -> job -> file) with ZERO keys.
# Self-healing: some Windows ffmpeg builds crash in the text/font code
# (0xC0000409) - if that happens we re-render without the text overlay.
import colorsys
import re
import subprocess
from pathlib import Path
from ..models import RenderJob


class TestVideoProvider:
    def generate(self, job: RenderJob, out_path: Path) -> Path:
        safe = re.sub(r'[^A-Za-z0-9 ]', '', job.prompt)[:40]
        h = (abs(hash(job.prompt)) % 360) / 360.0
        r, g, b = colorsys.hsv_to_rgb(h, 0.55, 0.45)
        color = '0x%02x%02x%02x' % (int(r * 255), int(g * 255), int(b * 255))
        freq = 200 + abs(hash(job.prompt)) % 400
        head = ['ffmpeg', '-y', '-f', 'lavfi', '-i',
                'color=c=%s:size=720x1280:duration=%.1f:rate=30' % (color, job.seconds),
                '-f', 'lavfi', '-i', 'sine=frequency=%d:duration=%.1f' % (freq, job.seconds)]
        tail = ['-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-shortest', str(out_path)]
        draw = ("drawtext=text='%s':fontcolor=white:fontsize=42:"
                'x=(w-text_w)/2:y=(h-text_h)/2:box=1:boxcolor=black@0.5' % safe)
        try:
            subprocess.run(head + ['-vf', draw] + tail, check=True, capture_output=True)
        except subprocess.CalledProcessError:
            subprocess.run(head + tail, check=True, capture_output=True)
        return Path(out_path)
