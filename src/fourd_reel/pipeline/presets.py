# Style presets for Quick Create - any content type, not just drama.
# A preset = a positive style block + a negative block layered over the user's prompt.

PRESETS = {
    'realistic': {
        'label': 'Photorealistic (people, real-world)',
        'positive': 'photorealistic, natural skin texture, real-world lighting, 35mm film look, sharp focus',
        'negative': 'cartoon, anime, illustration, cgi look, plastic skin, oversaturated',
    },
    'cinematic': {
        'label': 'Cinematic (movies, trailers)',
        'positive': 'cinematic film still, dramatic lighting, shallow depth of field, anamorphic, high production value',
        'negative': 'amateur, webcam, flat lighting, video artifacts',
    },
    'anime': {
        'label': 'Anime / stylized',
        'positive': 'anime style, clean line art, vibrant color, studio quality animation',
        'negative': 'photorealistic, live action, blurry',
    },
    'ugc': {
        'label': 'UGC / product ad (phone-shot feel)',
        'positive': 'user-generated content style, handheld phone footage, natural indoor lighting, authentic',
        'negative': 'studio, polished commercial, stock footage look',
    },
    'product': {
        'label': 'Product showcase (clean studio)',
        'positive': 'studio product photography, seamless background, softbox lighting, macro detail, commercial',
        'negative': 'cluttered background, hands, people, watermark',
    },
}


def apply_preset(prompt: str, style: str):
    if style not in PRESETS:
        raise ValueError('unknown style %r; choose from %s' % (style, sorted(PRESETS)))
    p = PRESETS[style]
    return prompt.rstrip('.') + '. ' + p['positive'], p['negative']


def preset_labels():
    return {k: v['label'] for k, v in PRESETS.items()}
