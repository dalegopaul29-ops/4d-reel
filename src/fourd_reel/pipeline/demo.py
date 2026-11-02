# Live proof-of-concept for Pillar 4 - NO RTMP key required.
#
# Builds 3 synthesized 'branch' clips (colour cards + titles + tone), then runs
# the REAL production selection loop from live.py: it polls feedback.txt, runs
# the sentiment vector, and picks the matching branch clip. Instead of pushing
# to an RTMP endpoint (which needs a real ingest key), the demo streams to a
# local viewer page + writes history.jsonl so you can audit every decision.
#
# Try it:  reel demo projects/<slug> --port 8799
#          then edit <project>/feedback.txt and save - the stream reacts.
import json
import subprocess
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from .sentiment import parse_feedback_vector

# emotion (from parse_feedback_vector) -> branch clip
EMOTION_MAP = {'fear': 'fear', 'outrage': 'tension', 'empathy': 'tension', 'calm': 'calm'}

CLIPS = {
    'fear':    {'color': '0x5c0a0a', 'title': 'FEAR SURGE — she is not alone'},
    'tension': {'color': '0x0a2a5c', 'title': 'OUTRAGE TWIST — the ledger'},
    'calm':    {'color': '0x0a3a22', 'title': 'SLOW BURN — the quiet reveal'},
}


def clip_for_emotion(emotion: str):
    key = EMOTION_MAP.get(emotion, 'calm')
    return key, CLIPS[key]


def _fontfile() -> str:
    for p in ('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
              '/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf'):
        if Path(p).exists():
            return p
    return ''


def _build_clip(out: Path, spec) -> None:
    font = _fontfile()
    draw = ("drawtext=fontfile=%s:text='%s':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=(h-text_h)/2"
            % (font + ':' if font else '', spec['title']))
    head = ['ffmpeg', '-y', '-f', 'lavfi',
            '-i', 'color=c=%s:size=720x1280:duration=3:rate=30' % spec['color'],
            '-f', 'lavfi', '-i', 'sine=frequency=220:duration=3']
    tail = ['-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-shortest', str(out)]
    try:
        subprocess.run(head + ['-vf', draw] + tail, check=True, capture_output=True)
    except subprocess.CalledProcessError:
        # Windows ffmpeg builds that crash in font/text code (0xC0000409): plain clip
        subprocess.run(head + tail, check=True, capture_output=True)


def build_demo_clips(ep_dir: Path) -> Path:
    ep_dir = Path(ep_dir)
    out_dir = ep_dir / 'assets' / 'branches'
    out_dir.mkdir(parents=True, exist_ok=True)
    for key, spec in CLIPS.items():
        out = out_dir / (key + '.mp4')
        if not out.exists():
            _build_clip(out, spec)
    fb = ep_dir / 'feedback.txt'
    if not fb.exists():
        fb.write_text('RUN!! he is BEHIND YOU - dont look!\n')
    return out_dir


def pick_clip(ep_dir: Path, metrics):
    emotion = (metrics or {}).get('dominant_emotion', 'calm')
    key, spec = clip_for_emotion(emotion)
    return Path(ep_dir) / 'assets' / 'branches' / (key + '.mp4'), spec['title'], emotion


PAGE = """<!DOCTYPE html><html><head><meta charset='utf-8'>
<meta http-equiv='refresh' content='1'>
<title>4D Reel - LIVE demo</title>
<style>body{background:#0a0f1a;color:#e5e7eb;font-family:system-ui;margin:0;text-align:center}
h1{color:#22c55e}#now{font-size:34px;margin:40px 0}
.clip{padding:60px 20px;margin:20px auto;max-width:640px;border-radius:14px;font-size:26px;font-weight:700}
.fear{background:#5c0a0a}.tension{background:#0a2a5c}.calm{background:#0a3a22}
table{margin:20px auto;border-collapse:collapse;font-size:13px}
td,th{border:1px solid #1f2937;padding:6px 14px}
.hint{color:#6b7280;font-size:13px;margin-top:30px}</style></head><body>
<h1>*** LIVE *** 4D Reel selection loop</h1>
<div id='now'>NOW STREAMING</div>
<div class='clip %%CLS%%'>%%TITLE%%</div>
<div>emotion: <b>%%EMOTION%%</b> | arousal: %%AROUSAL%% | last feedback: %%RAW%%</div>
%%HISTORY%%
<div class='hint'>Edit %%FB%% and save - the stream reacts within a second.<br>
Ctrl-C in the terminal to stop. History is written to history.jsonl.</div>
</body></html>"""


def run_demo(ep_dir: Path, port: int, poll_seconds: float = 1.0) -> None:
    ep_dir = Path(ep_dir)
    state = {'title': '(starting)', 'cls': 'calm', 'emotion': '-', 'arousal': '-', 'raw': ''}
    history_path = ep_dir / 'history.jsonl'

    def loop():
        while True:
            fb = ep_dir / 'feedback.txt'
            raw = ''
            if fb.exists():
                lines = [l for l in fb.read_text().splitlines() if l.strip()]
                raw = lines[-1] if lines else ''
            metrics = parse_feedback_vector(raw) if raw else {}
            clip, title, emotion = pick_clip(ep_dir, metrics)
            state.update({'title': title, 'cls': emotion if emotion in CLIPS else 'calm',
                          'emotion': emotion,
                          'arousal': str(metrics.get('arousal', '-')),
                          'raw': raw[:80]})
            with open(history_path, 'a') as f:
                f.write(json.dumps({'ts': time.time(), 'emotion': emotion,
                                    'clip': clip.name, 'raw': raw[:120]}) + '\n')
            time.sleep(poll_seconds)

    threading.Thread(target=loop, daemon=True).start()

    def rows():
        if not history_path.exists():
            return ''
        lines = history_path.read_text().splitlines()[-8:][::-1]
        out = ['<table><tr><th>#</th><th>emotion</th><th>clip</th><th>feedback</th></tr>']
        for i, l in enumerate(lines, 1):
            d = json.loads(l)
            out.append('<tr><td>%d</td><td>%s</td><td>%s</td><td>%s</td></tr>'
                       % (i, d['emotion'], d['clip'], d['raw'][:60]))
        out.append('</table>')
        return ''.join(out)

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            page = (PAGE.replace('%%TITLE%%', state['title'])
                        .replace('%%CLS%%', state['cls'])
                        .replace('%%EMOTION%%', state['emotion'])
                        .replace('%%AROUSAL%%', state['arousal'])
                        .replace('%%RAW%%', state['raw'].replace('<', '&lt;'))
                        .replace('%%HISTORY%%', rows())
                        .replace('%%FB%%', str(ep_dir / 'feedback.txt')))
            b = page.encode()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(b)))
            self.end_headers()
            self.wfile.write(b)

    server = ThreadingHTTPServer(('127.0.0.1', port), H)
    print('4D Reel LIVE demo: http://localhost:%d' % port)
    print('Now edit this file and save: %s' % (ep_dir / 'feedback.txt'))
    webbrowser.open('http://localhost:%d' % port)
    server.serve_forever()
