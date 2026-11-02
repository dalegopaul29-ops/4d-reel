from fourd_reel.models import (Episode, Scene, Character, SfxCue,
                                    ContinuityBook)
from fourd_reel.pipeline.continuity import (build_book, inject_anchors,
                                                 consistency_report)
from fourd_reel.pipeline.sentiment import parse_feedback_vector
from fourd_reel.pipeline.foley import build_sfx_filter
from fourd_reel.pipeline.export import resolution_for, export_plan
from pathlib import Path


def _ep():
    return Episode(
        title="T", hook="H",
        characters=[Character(name="Sarah",
                              anchor_description="Sarah: early 30s, short auburn hair, green eyes, small scar on left brow",
                              wardrobe="a red blazer")],
        scenes=[Scene(scene_number=1, visual_prompt="Sarah enters the office."),
                Scene(scene_number=2, visual_prompt="A man waits in the rain.")],
    )


def test_anchor_injection_only_where_named():
    ep, book = _ep(), build_book(_ep())
    n = inject_anchors(ep, book)
    assert n == 1                       # only scene 1 names Sarah
    assert "red blazer" in ep.scenes[0].visual_prompt
    assert "red blazer" not in ep.scenes[1].visual_prompt


def test_consistency_report_flags_missing_anchor():
    ep, book = _ep(), build_book(_ep())
    problems = consistency_report(ep, book)
    assert any("reference image" in p for p in problems)   # Sarah has no image yet
    assert any("anchor missing" in p for p in problems)


def test_sentiment_fear_surge():
    vec = parse_feedback_vector("RUN!! he's BEHIND YOU, dont look, OMG no no no")
    assert vec["dominant_emotion"] == "fear"
    assert vec["arousal"] > 0.5


def test_sentiment_calm():
    vec = parse_feedback_vector("nice cinematography, lovely pacing today")
    assert vec["dominant_emotion"] == "calm"


def test_foley_filter_pan_and_delay():
    fc = build_sfx_filter([{"at_seconds": 0.5, "pan": 1.0, "gain_db": -3.0},
                           {"at_seconds": 0.0, "pan": -1.0, "gain_db": 0.0}])
    assert "adelay=500|500" in fc
    assert "volume=-3.0dB" in fc
    assert "amix=inputs=3" in fc          # scene audio + 2 cues
    assert "c0=c0*0.00" in fc             # hard right: left muted


def test_export_resolutions():
    assert resolution_for("9:16") == (1080, 1920)
    assert resolution_for("16:9") == (1920, 1080)
    plan = export_plan(Path("in.mp4"), Path("out"), ["9:16", "1:1"])
    assert len(plan) == 2
    assert plan[1][2].name == "in_1x1.mp4"


def test_sfx_cue_bounds():
    cue = SfxCue(cue="glass", pan=0.5, at_seconds=1.0)
    assert -1.0 <= cue.pan <= 1.0
