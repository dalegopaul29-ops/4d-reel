from fourd_reel.models import Episode, Scene, RenderJob
from fourd_reel.pipeline.captions import segments_to_srt


def test_episode_roundtrip():
    ep = Episode(title="T", hook="H",
                 scenes=[Scene(scene_number=1, visual_prompt="p", dialogue="d")])
    ep2 = Episode.model_validate_json(ep.model_dump_json())
    assert ep2.scenes[0].dialogue == "d"


def test_render_job_defaults_vertical():
    job = RenderJob(kind="text_to_video", prompt="x")
    assert job.aspect_ratio == "9:16"
    assert "watermark" in job.negative_prompt


def test_srt_format():
    srt = segments_to_srt([{"start": 0.5, "end": 2.0, "text": "Hello"}])
    assert "00:00:00,500 --> 00:00:02,000" in srt
    assert srt.strip().startswith("1")
