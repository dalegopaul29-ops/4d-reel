"""4D Reel — local-first CLI.

    reel quick "prompt" [--style]         ONE prompt -> ONE video, any style
    reel new <premise> [--scenes N]       write storyboard (Gemini BYOK)
    reel voice <project>                  render scene voiceovers (free edge-tts)
    reel scenes <project>                 render scene clips (Replicate BYOK)
    reel assemble <project> [--captions]    mux + 9:16 conform + concat + captions
    reel cast <project> [--force]         Pillar 1: generate character reference portraits
    reel continuity <project>             Pillar 1: build continuity.json + consistency report
    reel branch <project> --feedback "..."  Pillar 2: compute + log a plot branch
    reel foley <project>                    Pillar 3: mix positioned SFX into scene finals
    reel export <project> --formats 9:16,16:9  Pillar 5: omni-format renders
    reel live <project> --rtmp URL --feedback FILE  Pillar 4: live selection loop
"""
import argparse
import sys
from pathlib import Path

from .models import Episode, RenderJob
from .pipeline.storyboard import init_project, jobs_for
from .pipeline.assemble import mux_voice, conform_vertical, concat_scenes, concat_audio
from .pipeline.captions import transcribe_segments, segments_to_srt, burn_subtitles


def _load(project: str) -> tuple[Path, Episode]:
    ep_dir = Path(project)
    return ep_dir, Episode.model_validate_json((ep_dir / "episode.json").read_text())


def cmd_new(args):
    if args.offline:
        from .pipeline.storyboard import template_episode
        ep = template_episode(args.premise, args.scenes)
    else:
        from .providers.gemini_script import GeminiScriptProvider
        ep = GeminiScriptProvider().write_storyboard(args.premise, args.scenes)
    ep_dir = init_project(ep, Path(args.out))
    print(f"storyboard: {ep_dir}/episode.json")


def cmd_voice(args):
    from .providers.edge_speech import EdgeSpeechProvider
    ep_dir, ep = _load(args.project)
    tts = EdgeSpeechProvider()
    for sc in ep.scenes:
        if not sc.dialogue:
            continue
        out = ep_dir / "assets" / f"scene_{sc.scene_number:02d}" / "voice.mp3"
        tts.synthesize(sc.dialogue, out, voice=_voice_for(ep, sc))
        print(f"voice: {out}")


def _voice_for(ep: Episode, sc) -> str:
    """If the scene names a character with a configured voice, use it."""
    for ch in ep.characters:
        if ch.name.lower() in (sc.visual_prompt + sc.dialogue).lower():
            return ch.voice
    return "en-US-EmmaMultilingualNeural"


def cmd_quick(args):
    import time
    from .pipeline.presets import apply_preset
    ep_dir = Path(args.out)
    ep_dir.mkdir(parents=True, exist_ok=True)
    prompt, negative = apply_preset(args.prompt, args.style)
    job = RenderJob(kind='image_to_video' if args.ref else 'text_to_video',
                    prompt=prompt, negative_prompt=negative,
                    seconds=args.seconds, aspect_ratio=args.aspect,
                    reference_image=args.ref)
    vp = _video_provider(args.provider)
    out = ep_dir / ('quick_%d.mp4' % int(time.time()))
    print('rendering (%s, %s)...' % (args.provider, args.style))
    vp.generate(job, out)
    print('video:', out)


def _video_provider(name):
    if name == 'test':
        from .providers.test_video import TestVideoProvider
        return TestVideoProvider()
    if name == 'gemini':
        from .providers.gemini_video import GeminiVeoProvider
        return GeminiVeoProvider()
    if name == 'fal':
        from .providers.fal_video import FalVideoProvider
        return FalVideoProvider()
    from .providers.replicate_video import ReplicateVideoProvider
    return ReplicateVideoProvider()


def cmd_scenes(args):
    from .pipeline.continuity import build_book, inject_anchors, save_book
    ep_dir, ep = _load(args.project)
    book = build_book(ep)
    save_book(book, ep_dir)
    inject_anchors(ep, book)  # anti-morph: verbatim anchor blocks in every prompt
    (ep_dir / "episode.json").write_text(ep.model_dump_json(indent=2))
    vp = _video_provider(args.provider)
    for name, job in jobs_for(ep):
        out = ep_dir / "assets" / name / "video.mp4"
        if out.exists():
            print(f"skip {name} (exists)")
            continue
        print(f"rendering {name}...")
        vp.generate(job, out)
    print("scenes done.")


def cmd_assemble(args):
    ep_dir, ep = _load(args.project)
    finals, audios = [], []
    for sc in ep.scenes:
        d = ep_dir / "assets" / f"scene_{sc.scene_number:02d}"
        raw, voice = d / "video.mp4", d / "voice.mp3"
        if not raw.exists():
            print(f"missing {raw}. Run `drama scenes` or drop your own clip there.")
            sys.exit(1)
        if voice.exists():
            muxed = d / "muxed.mp4"
            mux_voice(raw, voice, muxed)
            audios.append(voice)
        else:
            muxed = raw
        conf = d / "final.mp4"
        conform_vertical(muxed, conf)
        finals.append(conf)
    draft = ep_dir / "episode_draft.mp4"
    concat_scenes(finals, draft)
    print(f"draft: {draft}")
    if args.captions and audios:
        full = ep_dir / "assets" / "full_voice.mp3"
        concat_audio(audios, full)
        srt = ep_dir / "episode.srt"
        srt.write_text(segments_to_srt(transcribe_segments(full)))
        captioned = ep_dir / "episode_captioned.mp4"
        burn_subtitles(draft, srt, captioned)
        print(f"captions: {captioned}")


def cmd_continuity(args):
    from .pipeline.continuity import build_book, save_book, inject_anchors, consistency_report
    ep_dir, ep = _load(args.project)
    book = build_book(ep)
    save_book(book, ep_dir)
    n = inject_anchors(ep, book)
    (ep_dir / "episode.json").write_text(ep.model_dump_json(indent=2))
    problems = consistency_report(ep, book)
    print(f"continuity.json written; {n} anchor injections")
    if problems:
        print("CONSISTENCY WARNINGS:")
        for p in problems:
            print(" -", p)
    else:
        print("consistency: OK")


def cmd_branch(args):
    from .pipeline.sentiment import parse_feedback_vector, branch_plot
    from .pipeline.live import log_branch
    ep_dir, ep = _load(args.project)
    metrics = parse_feedback_vector(args.feedback)
    branch = branch_plot(ep.hook, metrics)
    log_branch(ep_dir, branch.model_dump(), metrics)
    print(branch.model_dump_json(indent=2))


def cmd_foley(args):
    from .pipeline.foley import mix_foley
    ep_dir, ep = _load(args.project)
    for sc in ep.scenes:
        if not sc.sfx:
            continue
        d = ep_dir / "assets" / f"scene_{sc.scene_number:02d}"
        src = d / "final.mp4"
        if not src.exists():
            print(f"skip scene {sc.scene_number} (no final.mp4 yet)")
            continue
        out = d / "final_mix.mp4"
        mix_foley(src, sc.sfx, out)
        print(f"foley: {out}")


def cmd_export(args):
    from .pipeline.export import run_export
    ep_dir, _ = _load(args.project)
    src = ep_dir / "episode_captioned.mp4"
    if not src.exists():
        src = ep_dir / "episode_draft.mp4"
    if not src.exists():
        print("nothing to export; run assemble first")
        sys.exit(1)
    formats = [f.strip() for f in args.formats.split(",")]
    outs = run_export(src, ep_dir / "exports", formats)
    for o in outs:
        print("export:", o)


def cmd_live(args):
    from .pipeline.live import run_live_loop, read_feedback
    from .pipeline.sentiment import parse_feedback_vector

    rendered = sorted(Path(args.project).glob("assets/scene_*/final.mp4"))
    if not rendered:
        print("no rendered clips; run scenes + assemble first")
        sys.exit(1)
    idx = {"i": 0}

    def pick(ep_dir, raw):
        if raw:
            m = parse_feedback_vector(raw)
            print(f"[live] feedback: {m['dominant_emotion']} arousal={m['arousal']}")
        clip = rendered[idx["i"] % len(rendered)]
        idx["i"] += 1
        print(f"[live] streaming {clip.name}")
        return clip

    print("live loop started; Ctrl-C to stop. NOTE: selection is real-time; clips must be pre-rendered.")
    try:
        run_live_loop(Path(args.project), args.rtmp, Path(args.feedback), pick)
    except KeyboardInterrupt:
        print("stopped.")


def cmd_cast(args):
    from .pipeline.cast import ensure_cast_images
    from .providers.fal_image import FalImageProvider
    ep_dir, ep = _load(args.project)
    if not ep.characters:
        print('no characters in episode.json - add them or run `reel new` with a premise that defines cast')
        return
    made, skipped = ensure_cast_images(ep_dir, ep.characters, FalImageProvider(), force=args.force)
    (ep_dir / 'episode.json').write_text(ep.model_dump_json(indent=2))
    for n in made:
        print(f'cast portrait generated: {n}')
    for n in skipped:
        print(f'skipped (already has reference): {n}')


def cmd_demo(args):
    from .pipeline.demo import build_demo_clips, run_demo
    ep_dir, _ = _load(args.project)
    build_demo_clips(ep_dir)
    print('demo clips ready:', ep_dir / 'assets' / 'branches')
    try:
        run_demo(ep_dir, args.port)
    except KeyboardInterrupt:
        print('stopped.')


def main():
    p = argparse.ArgumentParser(prog="reel")
    sub = p.add_subparsers(dest="cmd", required=True)

    n = sub.add_parser("new")
    n.add_argument("premise")
    n.add_argument("--scenes", type=int, default=4)
    n.add_argument("--out", default="projects")
    n.add_argument("--offline", action="store_true",
                   help="template storyboard, no API key needed")
    n.set_defaults(func=cmd_new)

    v = sub.add_parser("voice")
    v.add_argument("project")
    v.set_defaults(func=cmd_voice)

    s = sub.add_parser("scenes")
    s.add_argument("project")
    s.add_argument("--provider", default="fal", choices=["fal", "replicate"])
    s.set_defaults(func=cmd_scenes)

    a = sub.add_parser("assemble")
    a.add_argument("project")
    a.add_argument("--captions", action="store_true")
    a.set_defaults(func=cmd_assemble)

    c = sub.add_parser("continuity")
    c.add_argument("project")
    c.set_defaults(func=cmd_continuity)

    b = sub.add_parser("branch")
    b.add_argument("project")
    b.add_argument("--feedback", required=True)
    b.set_defaults(func=cmd_branch)

    f = sub.add_parser("foley")
    f.add_argument("project")
    f.set_defaults(func=cmd_foley)

    e = sub.add_parser("export")
    e.add_argument("project")
    e.add_argument("--formats", default="9:16,16:9,1:1")
    e.set_defaults(func=cmd_export)

    l = sub.add_parser("live")
    l.add_argument("project")
    l.add_argument("--rtmp", required=True, help="ingest URL e.g. rtmp://a.rtmp.youtube.com/live2/KEY")
    l.add_argument("--feedback", default="feedback.txt")
    l.set_defaults(func=cmd_live)

    q = sub.add_parser("quick")
    q.add_argument("prompt")
    q.add_argument("--style", default="realistic",
                   choices=["realistic", "cinematic", "anime", "ugc", "product"])
    q.add_argument("--aspect", default="9:16", choices=["9:16", "16:9", "1:1", "4:5"])
    q.add_argument("--seconds", type=float, default=5.0)
    q.add_argument("--ref", default=None,
                   help="reference image for character/product locking (image-to-video)")
    q.add_argument("--provider", default="fal",
                   choices=["test", "fal", "replicate", "gemini"])
    q.add_argument("--out", default="outputs")
    q.set_defaults(func=cmd_quick)

    ca = sub.add_parser("cast")
    ca.add_argument("project")
    ca.add_argument("--force", action="store_true", help="regenerate even if reference exists")
    ca.set_defaults(func=cmd_cast)

    dm = sub.add_parser("demo")
    dm.add_argument("project")
    dm.add_argument("--port", type=int, default=8799)
    dm.set_defaults(func=cmd_demo)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
