# 4D Reel (v0.2)

Local-first AI short-drama studio: premise -> structured storyboard -> voiceovers ->
scene clips -> vertical 9:16 assembled episode with burned-in captions.

Philosophy (same as 4D-Quill): your scripts, project files and renders live on YOUR
machine. Only the generation calls you explicitly configure (BYOK) leave the machine.

## Honest architecture notes (read before trusting any hype)

1. Proprietary models (Seedance, Veo, Kling, Runway) have NO open weights.
   Open-weights video models: Wan 2.2, LTX-Video, Mochi, CogVideoX, HunyuanVideo.
2. Local generation needs 12-45 GB VRAM. Default path = BYOK cloud APIs
   (Replicate/fal.ai run the open models). Local GPU is an optional provider.
3. "Speech-to-video" ships in two honest forms:
   - Avatar track: audio-driven lip-sync on a still face (Wav2Lip / LivePortrait) -> M3
   - Cinematic track: TTS voiceover -> generated scene clips (what v0.1 does)

## Decision log (2026-10-23)

- **Name:** 4D Reel (4D-suite). Package `fourd_reel`, CLI `reel`, dashboard `python -m fourd_reel.webui`.
- **Video provider:** fal.ai PRIMARY (fast cold-starts, Wan 2.2-class open weights, ~$0.10-0.40 per 5s clip; an 8-scene x2-take episode ~= $2-6). Replicate FALLBACK via `reel scenes --provider replicate`. Direct Kling/Runway APIs deferred (3-10x cost, credit throttling) - candidate premium 'hero shot' tier later.
- **Form factor:** CLI = engine; web dashboard = thin local wrapper (stdlib only, green 4D theme). Desktop packaging stays possible later because of this split.

## Install

    python -m venv .venv && source .venv/bin/activate
    pip install -e ".[dev]"
    cp .env.example .env   # fill in keys

## Usage

    reel new "a billionaire poses as a janitor to test his fiancee" --scenes 4
    reel voice projects/a_billionaire_poses...
    reel scenes projects/a_billionaire_poses...     # needs REPLICATE_API_TOKEN
    reel assemble projects/a_billionaire_poses... --captions

Without a video key: drop your own clips named assets/scene_XX/video.mp4 and run
`drama voice` + `drama assemble` — the pipeline works around manual footage too.

## Super-tool feature map (phased)

| Phase | Feature (paid-tool equivalent) | Module |
|---|---|---|
| M1 | Script-to-storyboard JSON (StoryShort) | providers/gemini_script.py |
| M1 | Free neural TTS voiceovers (-) | providers/edge_speech.py |
| M1 | Vertical conform + concat (CapCut) | pipeline/assemble.py |
| M1 | Auto captions, Whisper + ffmpeg | pipeline/captions.py |
| M2 | Text-to-video / image-to-video BYOK (Kling/Runway class) | providers/replicate_video.py |
| M2 | Face-locking reference images (Higgsfield/StoryShort cast) | reference_image in RenderJob |
| M3 | Speech-to-video avatar lip-sync (HeyGen) | providers/lip_sync.py (TBD) |
| M3 | Multi-language dubbing track | reuse edge-tts voices per scene |
| M4 | Long-form link -> short clips (OpusClip) | scene boundary detect (TBD) |
| M5 | Stock b-roll injection (Canva/Envato) | Pexels/Pixabay API hooks (TBD) |


## Quick Create (any video, not just drama)

The dashboard's Quick Create tab: type a prompt -> pick style / format / engine ->
Generate. `reel quick "prompt" --style realistic` does the same from the CLI.
Engines: `test` (free offline placeholder render), `fal` (Wan 2.2, cheap),
`gemini` (Veo, realistic - verify model id before shipping), `replicate` (fallback).
Use `--ref <image>` to lock a character or product across renders.

## The Five Pillars (2035 vision -> 2026-honest status)

| Pillar | What ships TODAY | What is research (not promised) |
|---|---|---|
| 1. Continuous Context World | `pipeline/continuity.py`: character anchor blocks injected verbatim into every prompt, per-project continuity.json state journal, reference-image face-lock, fixed seeds | True volumetric world models; diffusion-as-camera inside a locked 3D twin |
| 2. Neuro-Adaptive Scripts | `pipeline/sentiment.py`: live text/chat/poll feedback -> arousal/emotion vector -> PlotBranch; every branch logged to branches.jsonl; works offline with deterministic fallback | Front-camera gaze/micro-expression: opt-in consent-gated plugin only (POPIA-sensitive), never default |
| 3. Spatial Audio Fields | `pipeline/foley.py`: per-cue delay/gain/stereo-pan mixing under scene audio; swappable SFX providers | Physical material-acoustic simulation from implied room geometry (approximated via reverb tail) |
| 4. Autonomous Live Streams | `pipeline/live.py`: pre-rendered branch graph + real-time edge selection + RTMP push | Sub-second on-demand generation (selection is instant; generation is pre-computed — we do not fake this) |
| 5. Omni-Format Export | `pipeline/export.py`: 9:16 / 16:9 / 1:1 / 4:5 renders from one project | Gaussian-splat / volumetric headset output |

## Project format

A project is a folder. Everything is inspectable and editable by hand:

    projects/<slug>/
      episode.json              # the single source of truth
      episode.srt               # generated captions
      episode_draft.mp4         # assembled draft
      episode_captioned.mp4     # final
      assets/full_voice.mp3
      assets/scene_01/ video.mp4 voice.mp3 muxed.mp4 final.mp4

License: MIT (suggested — matches the 4D suite).
