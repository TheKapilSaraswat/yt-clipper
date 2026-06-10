import subprocess
import json
import os
import sys
import math
import re
import pickle
import threading
import time
from datetime import datetime
from flask import Flask, jsonify, render_template_string

TRENDING_SEARCHES = [
    "ytsearch15:today's trending videos",
    "ytsearch15:viral videos today",
    "ytsearch15:trending on youtube today",
]

RED_FLAG_TITLE_KEYWORDS = [
    "lyrics", "cover", "remix", "mashup", "full movie", "full episode",
    "movie clip", "scene from", "official video", "music video", "audio",
]
RED_FLAG_DESC_KEYWORDS = [
    r"no copyright", r"copyright (disclaimer|notice|free)",
    r"fair use", r"all rights belong", r"i do not own",
    r"no infringement", r"for entertainment purposes only",
]

DAILY_LOG = "upload_log.json"
SECRET_FILE = "client_secret.json"
TOKEN_FILE = "yt_token.pickle"
CLIPS_PER_DAY = 6
CLIP_DURATION = 30

app = Flask(__name__)
pipeline_status = []  # Shared status list

HTML = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>YouTube Clipper</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: -apple-system, 'Segoe UI', Roboto, sans-serif;
      background: #0f0f0f;
      color: #fff;
      display: flex;
      flex-direction: column;
      align-items: center;
      min-height: 100vh;
      padding: 20px;
    }
    h1 { font-size: 24px; margin: 30px 0 10px; color: #ff0044; }
    .subtitle { color: #888; font-size: 14px; margin-bottom: 30px; }
    .btn {
      width: 200px; height: 200px; border-radius: 50%;
      background: linear-gradient(135deg, #ff0044, #ff5500);
      border: none; color: #fff; font-size: 22px; font-weight: bold;
      cursor: pointer; box-shadow: 0 8px 32px rgba(255,0,68,0.4);
      transition: transform 0.2s, box-shadow 0.2s;
      display: flex; align-items: center; justify-content: center;
      text-align: center; line-height: 1.3; padding: 20px;
    }
    .btn:active { transform: scale(0.95); }
    .btn:disabled { opacity: 0.5; transform: scale(0.98); box-shadow: none; }
    .status-box {
      width: 100%; max-width: 500px; margin-top: 30px;
      background: #1a1a1a; border-radius: 16px; padding: 16px;
      max-height: 400px; overflow-y: auto;
      font-size: 13px; font-family: monospace; line-height: 1.6;
    }
    .status-box div { padding: 2px 0; border-bottom: 1px solid #222; }
    .info { color: #aaa; }
    .ok { color: #00e676; }
    .warn { color: #ffab00; }
    .err { color: #ff1744; }
    .done { color: #00e5ff; }
    .today-count {
      margin-top: 20px; padding: 12px 24px;
      background: #1a1a1a; border-radius: 12px; font-size: 14px;
    }
    .today-count span { color: #ff0044; font-weight: bold; font-size: 18px; }
  </style>
</head>
<body>
  <h1>YouTube Clipper</h1>
  <p class="subtitle">Tap to find trending → clip → upload 6 shorts</p>

  <button class="btn" id="goBtn" onclick="startPipeline()">
    ▶<br>START
  </button>

  <div class="today-count">
    Uploaded today: <span id="todayCount">0</span> / 6
  </div>

  <div class="status-box" id="statusBox">
    <div class="info">Ready. Tap START to begin.</div>
  </div>

  <script>
    function startPipeline() {
      document.getElementById('goBtn').disabled = true;
      document.getElementById('goBtn').innerHTML = '⏳<br>WORKING';
      document.getElementById('statusBox').innerHTML = '';
      fetch('/start', {method:'POST'});
    }

    function poll() {
      fetch('/status')
        .then(r => r.json())
        .then(data => {
          const box = document.getElementById('statusBox');
          box.innerHTML = data.logs.map(l => '<div class="'+l.type+'">'+l.msg+'</div>').join('');
          box.scrollTop = box.scrollHeight;
          document.getElementById('todayCount').textContent = data.todayCount;

          if (data.running) {
            setTimeout(poll, 1000);
          } else {
            document.getElementById('goBtn').disabled = false;
            document.getElementById('goBtn').innerHTML = '▶<br>START';
          }
        });
    }
    setInterval(poll, 2000);
    poll();
  </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/status")
def status():
    used = load_json(DAILY_LOG, [])
    today = datetime.now().strftime("%Y-%m-%d")
    today_count = len([u for u in used if u["date"] == today])
    return jsonify({
        "logs": pipeline_status[-100:] if pipeline_status else [{"type": "info", "msg": "Ready"}],
        "running": pipeline_status and pipeline_status[-1].get("running", False) if pipeline_status else False,
        "todayCount": today_count
    })

@app.route("/start", methods=["POST"])
def start():
    thread = threading.Thread(target=run_pipeline, daemon=True)
    thread.start()
    return jsonify({"ok": True})

# ─── LOGGING ────────────────────────────────────────────────────────────

def add_log(msg, typ="info"):
    ts = datetime.now().strftime("%H:%M:%S")
    pipeline_status.append({"msg": f"[{ts}] {msg}", "type": typ, "running": True})

def mark_done():
    if pipeline_status:
        pipeline_status[-1]["running"] = False

# ─── HELPERS ────────────────────────────────────────────────────────────

def load_json(path, default):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def get_video_info(url):
    r = subprocess.run(["yt-dlp", "--dump-json", "--no-download", "--skip-download", url],
                       capture_output=True, text=True, check=True)
    return json.loads(r.stdout)

def is_official(info):
    t = info.get("title", "").lower()
    c = info.get("channel", "").lower()
    f = info.get("channel_follower_count") or 0
    v = info.get("channel_is_verified", False)
    return v and f > 50000 and bool(set(c.split()) & set(t.split()))

def check_video(info):
    issues = []
    title, desc = info.get("title", ""), info.get("description", "") or ""
    channel, followers = info.get("channel", ""), info.get("channel_follower_count") or 0
    verified, cats = info.get("channel_is_verified", False), info.get("categories", []) or []
    dur, official = info.get("duration", 0), is_official(info)
    tl = title.lower()
    rfk = [kw for kw in RED_FLAG_TITLE_KEYWORDS if kw not in ("official video", "music video", "audio")] if official else RED_FLAG_TITLE_KEYWORDS
    found = [kw for kw in rfk if kw in tl]
    if found: issues.append(f"Title: {found}")
    found = [p for p in RED_FLAG_DESC_KEYWORDS if re.search(p, desc.lower())]
    if found: issues.append("Has disclaimer patterns")
    if not verified: issues.append("Not verified")
    if followers < 10000: issues.append(f"Only {followers:,} followers")
    if "music" in str(cats).lower() and not official: issues.append("Music from non-official")
    if dur > 3600: issues.append("Very long")
    if not (set(channel.lower().split()) & set(tl.split())): issues.append("Channel not in title")
    level = "LOW"
    if len(issues) >= 4: level = "HIGH"
    elif len(issues) >= 2: level = "MEDIUM"
    return level, issues

def get_trending():
    seen = set()
    videos = []
    for q in TRENDING_SEARCHES:
        try:
            r = subprocess.run(["yt-dlp", "--flat-playlist", "--dump-json", "--no-download", q],
                               capture_output=True, text=True, check=True)
            for line in r.stdout.strip().split("\n"):
                if line:
                    try:
                        item = json.loads(line)
                        vid = item.get("id", "")
                        if vid not in seen:
                            seen.add(vid)
                            videos.append(item)
                    except: continue
        except: continue
    videos.sort(key=lambda v: v.get("view_count", 0) or 0, reverse=True)
    return videos

def download_video(url):
    os.makedirs("original", exist_ok=True)
    tpl = os.path.join("original", "%(title)s.%(ext)s")
    subprocess.run(["yt-dlp", "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best", "-o", tpl, url],
                   check=True, capture_output=True, text=True)
    files = [f for f in os.listdir("original") if f.endswith(".mp4")]
    return max((os.path.join("original", f) for f in files), key=os.path.getmtime)

def get_duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                       capture_output=True, text=True, check=True)
    return float(r.stdout.strip())

def clip_video(path, output_dir="clips", seg=CLIP_DURATION):
    os.makedirs(output_dir, exist_ok=True)
    dur = get_duration(path)
    num = math.ceil(dur / seg)
    base = os.path.splitext(os.path.basename(path))[0]
    paths = []
    for i in range(num):
        name = f"{base}_part{i+1:03d}.mp4"
        p = os.path.join(output_dir, name)
        subprocess.run(["ffmpeg", "-y", "-i", path, "-ss", str(i * seg), "-t", str(seg), "-c", "copy", p],
                       check=True, capture_output=True, text=True)
        paths.append(p)
    return paths

def gen_caption(idx, total, info):
    title = info.get("title", "")
    tags = info.get("tags", []) or []
    desc = info.get("description", "") or ""
    words = (title + " " + desc + " " + " ".join(tags[:10])).lower()
    words = re.sub(r"[^a-z0-9\s]", "", words)
    wlist = [w for w in words.split() if len(w) > 3]
    freq = {}
    for w in wlist: freq[w] = freq.get(w, 0) + 1
    top_kw = [w for w, c in sorted(freq.items(), key=lambda x: -x[1]) if c > 1][:5]
    kw_str = " ".join(top_kw[:3]) if top_kw else title.split()[0] if title else "trending"
    hashtags = ["#shorts", "#trending", "#viral"]
    hashtags.extend(["#" + kw for kw in top_kw[:3]])
    caption = f"{kw_str.title()} | {title[:50]} Part {idx}/{total} {' '.join(hashtags)}"
    if len(caption.split()) > 95:
        caption = " ".join(caption.split()[:95])
    return caption

def authenticate():
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    if not os.path.exists(SECRET_FILE):
        add_log(f"ERROR: {SECRET_FILE} missing! Get it from Google Cloud Console.", "err")
        return None
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as f: creds = pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(SECRET_FILE, ["https://www.googleapis.com/auth/youtube.upload"])
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "wb") as f: pickle.dump(creds, f)
    return build("youtube", "v3", credentials=creds)

def upload_short(youtube, filepath, title, desc, tags):
    from googleapiclient.http import MediaFileUpload
    body = {
        "snippet": {"title": title[:100], "description": desc[:5000], "tags": tags[:500], "categoryId": "22"},
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False},
    }
    media = MediaFileUpload(filepath, chunksize=-1, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    add_log(f"Uploading: {title[:50]}...")
    response = request.execute()
    add_log(f"Uploaded: https://youtube.com/watch?v={response['id']}", "done")
    return response["id"]

# ─── PIPELINE ───────────────────────────────────────────────────────────

def run_pipeline():
    pipeline_status.clear()
    used = load_json(DAILY_LOG, [])
    today = datetime.now().strftime("%Y-%m-%d")

    uploaded_today = [u for u in used if u["date"] == today]
    already_uploaded = set(u["file"] for u in used)
    need = CLIPS_PER_DAY - len(uploaded_today)

    add_log(f"Uploaded {len(uploaded_today)}/{CLIPS_PER_DAY} today, need {need} more")
    if need <= 0:
        add_log("Already done for today!", "ok")
        mark_done()
        return

    # Collect unused clips
    available = []
    if os.path.exists("clips"):
        for f in sorted(os.listdir("clips")):
            fp = os.path.join("clips", f)
            if f.endswith(".mp4") and fp not in already_uploaded:
                available.append(fp)
    add_log(f"{len(available)} unused clips available")

    clips_to_upload = available[:need]
    remaining = need - len(clips_to_upload)

    # Download from trending if needed
    while remaining > 0:
        add_log(f"Scanning trending for clean videos...")
        candidates = get_trending()
        found_source = False

        for c in candidates:
            vid_url = f"https://youtube.com/watch?v={c.get('id', '')}"
            try:
                info = get_video_info(vid_url)
                level, issues = check_video(info)
                dur = info.get("duration", 0)
                clip_count = math.ceil(dur / CLIP_DURATION)
                add_log(f"{c['title'][:50]} -> {level} ({clip_count} clips)")
                if level == "HIGH":
                    add_log(f"  Skipped (HIGH risk)", "warn")
                    continue
                if clip_count < 1:
                    continue
                add_log(f"Selected: {info['title'][:60]}", "ok")
                found_source = True
                break
            except Exception as e:
                continue

        if not found_source:
            add_log("No suitable trending videos found!", "err")
            break

        add_log("Downloading...")
        video_path = download_video(vid_url)
        add_log("Clipping into 30s segments...")
        new_clips = clip_video(video_path)
        add_log(f"Created {len(new_clips)} clips", "ok")

        for cp in new_clips:
            if cp not in already_uploaded and cp not in clips_to_upload:
                clips_to_upload.append(cp)
                already_uploaded.add(cp)
                remaining -= 1
                if remaining <= 0:
                    break

    if not clips_to_upload:
        add_log("No clips to upload.", "err")
        mark_done()
        return

    add_log("Authenticating with YouTube...")
    youtube = authenticate()
    if not youtube:
        mark_done()
        return

    uploaded_count = 0
    for idx, clip_path in enumerate(clips_to_upload[:CLIPS_PER_DAY]):
        info = {"title": os.path.basename(clip_path).replace("_part", " - Part "), "tags": [], "description": ""}
        caption = gen_caption(idx + 1, len(clips_to_upload), info)
        desc = f"{caption}\n\n#shorts #trending #viral"
        tags = ["shorts", "trending", "viral"]
        try:
            upload_short(youtube, clip_path, caption, desc, tags)
            used.append({"date": today, "file": clip_path, "title": caption})
            save_json(DAILY_LOG, used)
            uploaded_count += 1
        except Exception as e:
            add_log(f"Upload failed: {e}", "err")
            continue

    add_log(f"Done! Uploaded {uploaded_count} clips today.", "done")
    mark_done()

def main():
    host = "0.0.0.0"
    port = 5000
    print(f"Starting server...")
    print(f"Open http://localhost:{port} or http://YOUR_PHONE_IP:{port} on your phone")
    app.run(host=host, port=port, debug=False)

if __name__ == "__main__":
    main()
