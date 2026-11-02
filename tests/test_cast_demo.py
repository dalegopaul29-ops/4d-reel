from fourd_reel.models import Episode, Scene, Character
from fourd_reel.pipeline.cast import slug, portrait_prompt
from fourd_reel.pipeline.storyboard import jobs_for
from fourd_reel.pipeline.demo import clip_for_emotion, EMOTION_MAP, CLIPS
from fourd_reel.pipeline.sentiment import parse_feedback_vector


def _ep(with_ref=True):
    ch = Character(name='Sarah',
                   anchor_description='early 30s, short auburn hair, green eyes',
                   wardrobe='a red blazer')
    if with_ref:
        ch.reference_image = 'assets/cast/sarah.png'
    return Episode(title='T', hook='H', characters=[ch],
                   scenes=[Scene(scene_number=1, visual_prompt='Sarah enters.'),
                           Scene(scene_number=2, visual_prompt='A man waits outside.')])


def test_slug():
    assert slug('Sarah Jane!') == 'sarah_jane'


def test_portrait_prompt_uses_anchor_and_wardrobe():
    p = portrait_prompt(_ep().characters[0])
    assert 'auburn hair' in p and 'red blazer' in p
    assert 'head-and-shoulders' in p


def test_jobs_for_inherits_reference_image():
    jobs = list(jobs_for(_ep()))
    assert jobs[0][1].kind == 'image_to_video'
    assert jobs[0][1].reference_image == 'assets/cast/sarah.png'
    assert jobs[1][1].kind == 'text_to_video'   # scene 2 names nobody


def test_jobs_for_without_reference_stays_t2v():
    jobs = list(jobs_for(_ep(with_ref=False)))
    assert jobs[0][1].kind == 'text_to_video'


def test_emotion_map_covers_all_sentiment_outputs():
    for emotion in ('fear', 'outrage', 'empathy', 'calm'):
        assert emotion in EMOTION_MAP


def test_clip_for_emotion_defaults_calm():
    key, spec = clip_for_emotion('unknown-thing')
    assert key == 'calm'
    assert 'title' in spec and 'color' in spec


def test_demo_clip_specs_match_clips():
    for key in EMOTION_MAP.values():
        assert key in CLIPS


def test_sentiment_drives_mapping_end_to_end():
    vec = parse_feedback_vector('RUN, he is BEHIND YOU, OMG')
    key, spec = clip_for_emotion(vec['dominant_emotion'])
    assert key == 'fear'
