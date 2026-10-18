"""
ClipForge web UI — upload a video, get viral clips back.

Run:  ./venv/bin/python web/app.py
Open: http://localhost:5057
"""
import json
import os
import sys
import threading
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from flask import Flask, request, jsonify, send_from_directory, render_template_string

BASE = os.path.join(os.path.dirname(__file__), "..")
UPLOADS = os.path.join(BASE, "web", "uploads")
OUTPUTS = os.path.join(BASE, "web", "outputs")
os.makedirs(UPLOADS, exist_ok=True)
os.makedirs(OUTPUTS, exist_ok=True)

app = Flask(__name__)
jobs = {}

PAGE = """
<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ClipForge — AI Video Clipper</title>
<style>
body{font-family:system-ui,sans-serif;max-width:760px;margin:2rem auto;padding:0 1rem;color:#1a1a2e}
h1{font-size:1.6rem} .gold{color:#b8860b}
.card{border:1px solid #ddd;border-radius:12px;padding:1rem;margin:1rem 0}
video{max-width:100%;border-radius:8px}
.score{display:inline-block;background:#1E0248;color:#F0D000;font-weight:bold;
  border-radius:8px;padding:.2rem .6rem;margin-right:.5rem}
.tag{color:#555;font-size:.9rem}
button{background:#1E0248;color:#F0D000;border:none;border-radius:8px;
  padding:.7rem 1.4rem;font-size:1rem;cursor:pointer}
button:disabled{opacity:.5}
</style></head><body>
<h1>✂️ ClipForge <span class="gold">— AI Video Clipper</span></h1>
<p>Upload a video. Get back the most viral-ready vertical clips, captioned and scored.</p>
<form id="f" enctype="multipart/form-data">
  <input type="file" name="video" accept="video/*" required>
  <button type="submit" id="btn">Make clips</button>
</form>
<p style="text-align:center;color:#888">— or —</p>
<form id="fu">
  <input type="url" name="url" id="url" placeholder="Paste a YouTube link…" required
    style="width:70%;padding:.6rem;border:1px solid #ccc;border-radius:8px">
  <button type="submit" id="btn2">Clip this link</button>
</form>
<div id="status"></div>
<div id="results"></div>
<script>
const f=document.getElementById('f'),st=document.getElementById('status'),
      res=document.getElementById('results'),btn=document.getElementById('btn'),
      fu=document.getElementById('fu'),btn2=document.getElementById('btn2');
function watch(job_id){st.textContent='Working… download → transcription → scoring → rendering';
  const t=setInterval(async()=>{
    const s=await (await fetch('/status/'+job_id)).json();
    st.textContent='Status: '+s.status+(s.detail?' — '+s.detail:'');
    if(s.status==='done'){clearInterval(t);btn.disabled=false;btn2.disabled=false;show(s.clips);}
    if(s.status==='error'){clearInterval(t);btn.disabled=false;btn2.disabled=false;}
  },3000);}
f.onsubmit=async e=>{e.preventDefault();btn.disabled=true;btn2.disabled=true;
  st.textContent='Uploading…';
  const r=await fetch('/upload',{method:'POST',body:new FormData(f)});
  const {job_id}=await r.json();watch(job_id);};
fu.onsubmit=async e=>{e.preventDefault();btn.disabled=true;btn2.disabled=true;
  st.textContent='Fetching link…';
  const fd=new FormData();fd.append('url',document.getElementById('url').value);
  const r=await fetch('/ingest',{method:'POST',body:fd});
  const j=await r.json();
  if(j.error){st.textContent='Error: '+j.error;btn.disabled=false;btn2.disabled=false;return;}
  watch(j.job_id);};
function show(clips){res.innerHTML='<h2>Your clips</h2>'+clips.map(c=>`
  <div class="card"><span class="score">${c.score}</span><b>${c.title}</b>
  <div class="tag">${c.hashtags.join(' ')}</div>
  <video src="/outputs/${c.file}" controls playsinline></video><br>
  <a href="/outputs/${c.file}" download>Download</a></div>`).join('');}
</script></body></html>
"""


def run_job(job_id, video_path, out_dir):
    try:
        from transcribe import transcribe
        from score import find_moments, make_hashtags
        from render import render_clip
        jobs[job_id]["status"] = "transcribing"        segments, _ = transcribe(video_path)
        jobs[job_id]["status"] = "scoring"
        jobs[job_id]["detail"] = f"{len(segments)} segments"
        moments = find_moments(segments, min_score=50)
        clips = []
        for i, m in enumerate(moments[:8]):
            jobs[job_id]["status"] = "rendering"
            jobs[job_id]["detail"] = f"clip {i+1}/{min(8, len(moments))}"
            fname = f"{job_id}-clip{i+1:02d}-{int(m['score'])}.mp4"
            render_clip(video_path, m, os.path.join(out_dir, fname))
            clips.append({"file": fname, "score": m["score"],
                          "title": m["title"],
                          "hashtags": make_hashtags(m["text"])})
        jobs[job_id].update(status="done", clips=clips, detail="")
    except Exception as e:  # noqa: BLE001
        jobs[job_id].update(status="error", detail=str(e)[:300])


@app.route("/")
def index():
    return render_template_string(PAGE)


@app.route("/upload", methods=["POST"])
def upload():
    f = request.files.get("video")
    if not f:
        return jsonify({"error": "no file"}), 400
    job_id = uuid.uuid4().hex[:8]
    vpath = os.path.join(UPLOADS, job_id + "-" + f.filename)
    f.save(vpath)
    out_dir = os.path.join(OUTPUTS, job_id)
    os.makedirs(out_dir, exist_ok=True)
    jobs[job_id] = {"status": "queued", "detail": "", "clips": []}
    threading.Thread(target=run_job, args=(job_id, vpath, out_dir),
                     daemon=True).start()
    return jsonify({"job_id": job_id})


@app.route("/ingest", methods=["POST"])
def ingest():
    from ingest import download_url
    url = (request.form.get("url") or "").strip()
    if not url:
        return jsonify({"error": "no URL"}), 400
    job_id = uuid.uuid4().hex[:8]
    out_dir = os.path.join(OUTPUTS, job_id)
    os.makedirs(out_dir, exist_ok=True)
    jobs[job_id] = {"status": "downloading", "detail": url[:60], "clips": []}

    def _ingest():
        try:
            vpath = download_url(url, out_dir)
            threading.Thread(target=run_job, args=(job_id, vpath, out_dir),
                             daemon=True).start()
        except Exception as e:  # noqa: BLE001
            jobs[job_id].update(status="error", detail=str(e)[:300])

    threading.Thread(target=_ingest, daemon=True).start()
    return jsonify({"job_id": job_id})


@app.route("/status/<job_id>")
def status(job_id):
    j = jobs.get(job_id)
    if not j:
        return jsonify({"status": "unknown"}), 404
    return jsonify({"status": j["status"], "detail": j.get("detail", ""),
                    "clips": j.get("clips", [])})


@app.route("/outputs/<job_id>/<fname>")
def outputs(job_id, fname):
    return send_from_directory(os.path.join(OUTPUTS, job_id), fname)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5057)
