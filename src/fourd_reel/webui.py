# 4D Reel - local web dashboard (stdlib only; no framework, no tracking).
# Thin wrapper over the CLI: the CLI stays the engine, this is glass on top.
# Run:  python -m fourd_reel.webui [--port 8765] [--projects projects]
import argparse
import glob
import json
import os
import subprocess
import sys
import threading
import time
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ACCENT = "#22c55e"
BG = "#0a0f1a"
STEPS = ["voice", "scenes", "assemble", "continuity", "foley", "export"]

PAGE = """<!DOCTYPE html><html><head><meta charset="utf-8">
<title>4D Reel</title><style>
body{background:%%BG%%;color:#e5e7eb;font-family:system-ui;margin:0}
header{padding:18px 28px;border-bottom:1px solid #1f2937;display:flex;gap:12px;align-items:baseline}
h1{color:%%ACCENT%%;margin:0;font-size:22px}
main{padding:22px 28px;padding-bottom:220px}
.card{background:#111827;border:1px solid #1f2937;border-radius:12px;padding:16px;margin-bottom:16px}
.card h2{margin:0 0 10px;font-size:16px;color:%%ACCENT%%}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:16px}
.hook{color:#9ca3af;font-size:13px;min-height:32px}
.meta{font-size:12px;color:#6b7280;margin:8px 0}
button{background:%%ACCENT%%;color:#04120a;border:0;border-radius:8px;padding:9px 16px;
font-weight:700;cursor:pointer;margin:3px 4px 3px 0;font-size:13px}
button.ghost{background:#1f2937;color:#e5e7eb}
button:disabled{opacity:.5;cursor:wait}
input,select,textarea{background:#020617;color:#e5e7eb;border:1px solid #1f2937;
border-radius:8px;padding:9px;font-size:14px;width:100%;box-sizing:border-box;font-family:system-ui}
textarea{min-height:70px;resize:vertical}
.row{display:flex;gap:10px;flex-wrap:wrap;margin-top:10px}
.row > div{flex:1;min-width:130px}
label{font-size:11px;color:#6b7280;display:block;margin-bottom:4px}
#log{position:fixed;bottom:0;left:0;right:0;height:190px;background:#020617;
border-top:1px solid #1f2937;padding:12px 28px;overflow:auto;font-family:monospace;
font-size:12px;color:#86efac}
.pill{display:inline-block;background:#052e16;color:#86efac;border-radius:20px;
padding:3px 12px;font-size:12px;margin:2px 4px 2px 0}
.qresult{background:#020617;border:1px solid #052e16;border-radius:10px;padding:10px;
margin-top:10px;font-size:13px;display:none}
</style></head><body>
<header><h1>&#9654; 4D Reel</h1><span>prompt to video - your machine, your keys</span>
<button class="ghost" onclick="loadProjects()">refresh</button></header>
<main>
<div class="card">
  <h2>Quick Create</h2>
  <label>Describe your video</label>
  <textarea id="q-prompt" placeholder="A golden retriever catches a frisbee at sunset..."></textarea>
  <div class="row">
    <div><label>Style</label><select id="q-style"></select></div>
    <div><label>Format</label><select id="q-aspect">
      <option>9:16</option><option>16:9</option><option>1:1</option><option>4:5</option></select></div>
    <div><label>Engine</label><select id="q-provider">
      <option value="test">Test render (free, offline)</option>
      <option value="fal">fal.ai - Wan 2.2 (cheap)</option>
      <option value="gemini">Google Veo (realistic)</option>
      <option value="replicate">Replicate (fallback)</option></select></div>
    <div><label>Lock character/product (optional)</label><select id="q-ref"><option value="">none</option></select></div>
    <div><label>Seconds</label><input id="q-seconds" type="number" value="5" min="2" max="15"></div>
  </div>
  <div class="row"><button id="q-go" onclick="quickCreate()">Generate</button>
  <span id="q-status" class="meta"></span></div>
  <div class="qresult" id="q-result"></div>
</div>
<div class="card">
  <h2>New Episode (storyboard mode)</h2>
  <label>Premise</label>
  <textarea id="e-premise" placeholder="A billionaire poses as a janitor to test his fiancee..."></textarea>
  <div class="row">
    <div><label>Scenes</label><input id="e-scenes" type="number" value="4" min="2" max="10"></div>
    <div><label>Writer</label><select id="e-offline">
      <option value="offline">Template (free, offline)</option>
      <option value="gemini">Gemini AI writer (needs key)</option></select></div>
    <div style="flex:0;min-width:auto;align-self:end"><button onclick="newEpisode()">Create Episode</button></div>
  </div>
  <span id="e-status" class="meta"></span>
</div>
<h2 style="color:%%ACCENT%%;font-size:15px">Storyboard Episodes</h2>
<div id="projects" class="grid"></div>
</main>
<div id="log"></div>
<script>
function log(m){var el=document.getElementById("log");el.innerHTML+=m+"<br>";el.scrollTop=el.scrollHeight;}
function esc(s){return (s||"").replace(/[&<>"]/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c];});}

async function loadPresets(){
 try{var ps=await (await fetch("/api/presets")).json();
  var sel=document.getElementById("q-style");sel.innerHTML="";
  Object.keys(ps).forEach(function(k){
   var o=document.createElement("option");o.value=k;o.textContent=ps[k];sel.appendChild(o);});
 }catch(e){log("presets: "+e);}}

async function loadRefs(){
 try{var refs=await (await fetch("/api/refs")).json();
  var sel=document.getElementById("q-ref");sel.innerHTML="<option value=''>none</option>";
  refs.forEach(function(r){var o=document.createElement("option");
   o.value=r;o.textContent=r.split("/").pop();sel.appendChild(o);});
 }catch(e){log("refs: "+e);}}

async function quickCreate(){
 var prompt=document.getElementById("q-prompt").value.trim();
 if(!prompt){log("type a prompt first");return;}
 var btn=document.getElementById("q-go");btn.disabled=true;
 document.getElementById("q-result").style.display="none";
 document.getElementById("q-status").textContent="sending...";
 var body={prompt:prompt,style:q_style.value,aspect:q_aspect.value,
  provider:q_provider.value,ref:q_ref.value||null,seconds:parseFloat(q_seconds.value)||5};
 try{
  var r=await fetch("/api/quick",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
  var j=await r.json();
  if(!j.ok){log("quick ERROR: "+esc(j.err||""));btn.disabled=false;return;}
  log("&raquo; quick render queued ("+body.provider+")");
  pollQuick(j.id,btn);
 }catch(e){log("quick error: "+e);btn.disabled=false;}}

async function pollQuick(id,btn){
 var st=document.getElementById("q-status");
 try{
  var j=await (await fetch("/api/quickstatus?id="+id)).json();
  if(j.status==="running"){st.textContent="rendering... "+(j.elapsed||0)+"s";
   setTimeout(function(){pollQuick(id,btn);},2000);return;}
  st.textContent="";
  var res=document.getElementById("q-result");res.style.display="block";
  if(j.status==="done"){res.innerHTML="&#10004; saved: <b>"+esc(j.out)+"</b>";
   log("&nbsp;&nbsp;quick video: "+esc(j.out));}
  else{res.innerHTML="&#10008; failed: "+esc(j.err||"unknown");
   log("&nbsp;&nbsp;quick FAILED: "+esc((j.err||"").split(String.fromCharCode(10)).slice(-3).join(" | ")));}
 }catch(e){log("poll: "+e);}
 btn.disabled=false;}

async function loadProjects(){
 var r=await fetch("/api/projects");var ps=await r.json();
 var m=document.getElementById("projects");m.innerHTML="";
 if(!ps.length)m.innerHTML="<div class=card><h2>No projects yet</h2><div class=hook>Use Quick Create above, or run: reel new &#34;your premise&#34;</div></div>";
 for(const p of ps){
  var detail={};
  try{detail=await (await fetch("/api/project?p="+encodeURIComponent(p.dir))).json();}catch(e){}
  var c=document.createElement("div");c.className="card";
  var tags=(detail.characters||[]).map(function(ch){return "<span class=pill>"+esc(ch.name)+"</span>";}).join("");
  var btns=STEPS.map(function(s){return "<button class=ghost onclick=\"runStep(&apos;"+p.dir+"&apos;,&apos;"+s+"&apos;,this)\">"+s+"</button>";}).join("");
  c.innerHTML="<h2>"+esc(detail.title||p.name)+"</h2><div class=hook>"+esc(detail.hook||"")+"</div>"+tags+
   "<div class=meta>"+(detail.scenes||[]).length+" scenes</div>"+btns;
  m.appendChild(c);}
 log("projects loaded");}

async function runStep(dir,step,btn){
 btn.disabled=true;log("&raquo; reel "+step+" "+dir);
 try{
  var extra=(step==="assemble")?" --captions":"";
  var r=await fetch("/api/run",{method:"POST",headers:{"Content-Type":"application/json"},
   body:JSON.stringify({project:dir,step:step,extra:extra})});
  var j=await r.json();
  log(j.ok?"&nbsp;&nbsp;started: "+step:"&nbsp;&nbsp;ERROR: "+esc(j.err||""));
 }catch(e){log("error: "+e);}
 btn.disabled=false;loadRefs();}

async function newEpisode(){
 var premise=document.getElementById("e-premise").value.trim();
 if(!premise){log("type a premise first");return;}
 var st=document.getElementById("e-status");
 st.textContent="creating...";
 var offline=(document.getElementById("e-offline").value==="offline");
 try{
  var r=await fetch("/api/newepisode",{method:"POST",headers:{"Content-Type":"application/json"},
   body:JSON.stringify({premise:premise,scenes:parseInt(e_scenes.value)||4,offline:offline})});
  var j=await r.json();
  if(!j.ok){st.textContent="";log("new episode ERROR: "+esc(j.err||""));return;}
  pollEpisode(j.id,st,premise);
 }catch(e){st.textContent="";log("error: "+e);}}

async function pollEpisode(id,st,premise){
 try{
  var j=await (await fetch("/api/quickstatus?id="+id)).json();
  if(j.status==="running"){setTimeout(function(){pollEpisode(id,st,premise);},1500);return;}
  if(j.status==="done"){st.textContent="created: "+premise.slice(0,50);
   log("&nbsp;&nbsp;episode created - it appears below");loadProjects();}
  else{st.textContent="failed";log("&nbsp;&nbsp;new episode FAILED: "+esc((j.err||"").split(String.fromCharCode(10)).slice(-3).join(" | ")));}
 }catch(e){log("poll: "+e);}}

loadPresets();loadRefs();loadProjects();
</script></body></html>"""


def _projects(projects_root):
    root = Path(projects_root)
    if not root.exists():
        return []
    return [{"name": d.name, "dir": str(d)} for d in sorted(root.iterdir())
            if d.is_dir() and (d / "episode.json").exists()]


def _refs(projects_root):
    pat = str(Path(projects_root).parent / "**" / "assets" / "cast" / "*.png")
    return sorted(glob.glob(pat, recursive=True))


def _env(src_dir):
    return dict(os.environ, PYTHONPATH=str(src_dir))


def _run_step(project, step, extra, src_dir):
    cmd = [sys.executable, "-m", "fourd_reel.cli", step, project] + extra.split()
    return subprocess.run(cmd, capture_output=True, text=True, timeout=3600, env=_env(src_dir))


def _run_newepisode(body, projects_root, src_dir):
    cmd = [sys.executable, "-m", "fourd_reel.cli", "new", body["premise"],
           "--scenes", str(body.get("scenes", 4)),
           "--out", str(Path(projects_root))]
    if body.get("offline"):
        cmd.append("--offline")
    return subprocess.run(cmd, capture_output=True, text=True, timeout=600,
                          env=_env(src_dir))


def _run_quick(body, src_dir):
    cmd = [sys.executable, "-m", "fourd_reel.cli", "quick", body["prompt"],
           "--style", body.get("style", "realistic"),
           "--aspect", body.get("aspect", "9:16"),
           "--provider", body.get("provider", "test"),
           "--seconds", str(body.get("seconds", 5)),
           "--out", "outputs"]
    if body.get("ref"):
        cmd += ["--ref", body["ref"]]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=3600, env=_env(src_dir))


def serve(projects_root, port, host="127.0.0.1"):
    src_dir = Path(__file__).resolve().parent.parent
    jobs = {}
    lock = threading.Lock()
    page = (PAGE.replace("%%ACCENT%%", ACCENT).replace("%%BG%%", BG))

    def job_thread(jid, fn):
        started = time.time()
        with lock:
            jobs[jid] = {"status": "running", "started": started}
        r = fn()
        with lock:
            jobs[jid].update(
                status="done" if r.returncode == 0 else "error",
                out=(r.stdout or "").strip().splitlines()[-1] if r.returncode == 0 else "",
                err=(r.stderr or "")[-2000:],
                elapsed=int(time.time() - started))

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, code, body, ctype="text/html; charset=utf-8"):
            b = body.encode() if isinstance(body, str) else body
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def do_GET(self):
            u = urlparse(self.path)
            if u.path == "/":
                self._send(200, page)
            elif u.path == "/api/projects":
                self._send(200, json.dumps(_projects(projects_root)), "application/json")
            elif u.path == "/api/project":
                p = Path(parse_qs(u.query)["p"][0]) / "episode.json"
                self._send(200, p.read_text() if p.exists() else "{}", "application/json")
            elif u.path == "/api/presets":
                from .pipeline.presets import preset_labels
                self._send(200, json.dumps(preset_labels()), "application/json")
            elif u.path == "/api/refs":
                self._send(200, json.dumps(_refs(projects_root)), "application/json")
            elif u.path == "/api/quickstatus":
                jid = parse_qs(u.query)["id"][0]
                with lock:
                    j = dict(jobs.get(jid, {"status": "unknown"}))
                if j.get("status") == "running":
                    j["elapsed"] = int(time.time() - j["started"])
                self._send(200, json.dumps(j), "application/json")
            else:
                self._send(404, "not found", "text/plain")

        def do_POST(self):
            u = urlparse(self.path)
            if u.path == "/api/run":
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                project, step, extra = body["project"], body["step"], body.get("extra", "")
                if step not in STEPS:
                    return self._send(400, json.dumps({"ok": False, "err": "unknown step"}),
                                       "application/json")
                threading.Thread(target=lambda: job_thread(uuid.uuid4().hex,
                                    lambda: _run_step(project, step, extra, src_dir)),
                                 daemon=True).start()
                return self._send(200, json.dumps({"ok": True, "started": step}),
                                  "application/json")
            if u.path == "/api/quick":
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                if not body.get("prompt", "").strip():
                    return self._send(400, json.dumps({"ok": False, "err": "prompt required"}),
                                       "application/json")
                jid = uuid.uuid4().hex
                threading.Thread(target=lambda: job_thread(jid,
                                    lambda: _run_quick(body, src_dir)),
                                 daemon=True).start()
                return self._send(200, json.dumps({"ok": True, "id": jid}),
                                  "application/json")
            if u.path == "/api/newepisode":
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                if not body.get("premise", "").strip():
                    return self._send(400, json.dumps({"ok": False, "err": "premise required"}),
                                       "application/json")
                jid = uuid.uuid4().hex
                threading.Thread(target=lambda: job_thread(
                    jid, lambda: _run_newepisode(body, projects_root, src_dir)),
                    daemon=True).start()
                return self._send(200, json.dumps({"ok": True, "id": jid}),
                                  "application/json")
            self._send(404, "{}", "application/json")

    server = ThreadingHTTPServer((host, port), H)
    shown = "localhost" if host == "127.0.0.1" else host
    print("4D Reel dashboard: http://%s:%d  (projects: %s)" % (shown, port, projects_root))
    if host == "0.0.0.0":
        print("WARNING: listening on all interfaces - no login exists.")
        print("Only safe on your own network or behind Tailscale. Never expose to the internet.")
    webbrowser.open("http://localhost:%d" % port)
    server.serve_forever()


def main():
    ap = argparse.ArgumentParser(prog="reel-web")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--projects", default="projects")
    ap.add_argument("--host", default="127.0.0.1",
                    help="127.0.0.1 = this device only (safe default). "
                         "0.0.0.0 = LAN/Tailscale access (phone browser) - no auth, trust your network.")
    args = ap.parse_args()
    serve(args.projects, args.port, args.host)


if __name__ == "__main__":
    main()
