import subprocess
import json
import os
import sys
import math
import re
import time
import pickle
from datetime import datetime

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

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def load_json(path, default):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

# ─── CHECKING ───────────────────────────────────────────────────────────

def get_video_info(url):
    cmd = ["yt-dlp", "--dump-json", "--no-download", "--skip-download", url]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(result.stdout)

def is_official(info):
    t = info.get("title", "").lower()
    c = info.get("channel", "").lower()
    f = info.get("channel_follower_count") or 0
    v = info.get("channel_is_verified", False)
    return v and f > 50000 and bool(set(c.split()) & set(t.split()))

def check_video(info):
    issues = []
    title = info.get("title", "")
    desc = info.get("description", "") or ""
    channel = info.get("channel", "")
    followers = info.get("channel_follower_count") or 0
    verified = info.get("channel_is_verified", False)
    cats = info.get("categories", []) or []
    duration = info.get("duration", 0)
    official = is_official(info)
    tl = title.lower()

    rfk = RED_FLAG_TITLE_KEYWORDS.copy()
    if official:
        rfk = [kw for kw in rfk if kw not in ("official video", "music video", "audio")]
    found = [kw for kw in rfk if kw in tl]
    if found: issues.append(f"Title: {found}")

    dl = desc.lower()
    found = [p for p in RED_FLAG_DESC_KEYWORDS if re.search(p, dl)]
    if found: issues.append("Description has disclaimer patterns")

    if not verified: issues.append("Channel not verified")
    if followers < 10000: issues.append(f"Only {followers:,} followers")
    if "music" in str(cats).lower() and not official:
        issues.append("Music from non-official channel")
    if duration > 3600: issues.append("Very long video")
    if not (set(channel.lower().split()) & set(tl.split())):
        issues.append("Channel not in title")

    level = "LOW"
    if len(issues) >= 4: level = "HIGH"
    elif len(issues) >= 2: level = "MEDIUM"
    return level, issues

# ─── TRENDING ───────────────────────────────────────────────────────────

def get_trending():
    seen = set()
    videos = []
    for q in TRENDING_SEARCHES:
        try:
            r = subprocess.run(
                ["yt-dlp", "--flat-playlist", "--dump-json", "--no-download", q],
                capture_output=True, text=True, check=True
            )
            for line in r.stdout.strip().split("\n"):
                if line:
                    try:
                        item = json.loads(line)
                        vid = item.get("id", "")
                        if vid not in seen:
                            seen.add(vid)
                            videos.append(item)
                    except json.JSONDecodeError:
                        continue
        except subprocess.CalledProcessError:
            continue
    videos.sort(key=lambda v: v.get("view_count", 0) or 0, reverse=True)
    return videos

# ─── DOWNLOAD & CLIP ────────────────────────────────────────────────────

def download_video(url):
    os.makedirs("original", exist_ok=True)
    tpl = os.path.join("original", "%(title)s.%(ext)s")
    subprocess.run(
        ["yt-dlp", "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
         "-o", tpl, url],
        check=True, capture_output=True, text=True
    )
    files = [f for f in os.listdir("original") if f.endswith(".mp4")]
    return max((os.path.join("original", f) for f in files), key=os.path.getmtime)

def get_duration(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True, check=True
    )
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
        subprocess.run(
            ["ffmpeg", "-y", "-i", path, "-ss", str(i * seg), "-t", str(seg), "-c", "copy", p],
            check=True, capture_output=True, text=True
        )
        paths.append(p)
    return paths

# ─── SEO CAPTION GENERATION ─────────────────────────────────────────────

def generate_short_caption(clip_index, total_clips, video_info):
    title = video_info.get("title", "")
    channel = video_info.get("channel", "")
    tags = video_info.get("tags", []) or []
    view_count = video_info.get("view_count", 0)
    duration = video_info.get("duration", 0)

    # Extract top keywords from tags/description
    desc = video_info.get("description", "") or ""
    words = (title + " " + desc + " " + " ".join(tags[:10])).lower()
    words = re.sub(r"[^a-z0-9\s]", "", words)
    word_list = [w for w in words.split() if len(w) > 3]
    freq = {}
    for w in word_list:
        freq[w] = freq.get(w, 0) + 1
    top_keywords = [w for w, c in sorted(freq.items(), key=lambda x: -x[1]) if c > 1][:5]

    # Build SEO caption
    kw_str = " ".join(top_keywords[:3]) if top_keywords else title.split()[0]

    hashtags = ["#shorts", "#trending", "#viral"]
    if top_keywords:
        hashtags.extend(["#" + kw for kw in top_keywords[:3]])

    caption = (
        f"{kw_str.title()} | {title[:50]} "
        f"Part {clip_index}/{total_clips} "
        f"{' '.join(hashtags)}"
    )

    # Keep under ~100 words
    words_count = len(caption.split())
    if words_count > 95:
        caption = " ".join(caption.split()[:95])

    return caption

# ─── UPLOAD ─────────────────────────────────────────────────────────────

def authenticate_youtube():
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    if not os.path.exists(SECRET_FILE):
        log(f"ERROR: {SECRET_FILE} not found.")
        log("Download from https://console.cloud.google.com -> APIs & Services -> Credentials")
        sys.exit(1)

    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                SECRET_FILE, ["https://www.googleapis.com/auth/youtube.upload"]
            )
            creds = flow.run_localServer(port=0)
        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)
    return build("youtube", "v3", credentials=creds)

def upload_short(youtube, filepath, title, description, tags):
    from googleapiclient.http import MediaFileUpload
    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": tags[:500],
            "categoryId": "22",
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
        },
    }
    media = MediaFileUpload(filepath, chunksize=-1, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    log(f"Uploading: {title[:60]}...")
    response = request.execute()
    log(f"Uploaded: https://youtube.com/watch?v={response['id']}")
    return response["id"]

# ─── MAIN PIPELINE ──────────────────────────────────────────────────────

def main():
    used = load_json(DAILY_LOG, [])
    today = datetime.now().strftime("%Y-%m-%d")

    # Check how many uploaded today
    uploaded_today = [u for u in used if u["date"] == today]
    already_uploaded_files = set(u["file"] for u in used)
    need_count = CLIPS_PER_DAY - len(uploaded_today)

    if need_count <= 0:
        log(f"Already uploaded {CLIPS_PER_DAY} clips today. Done.")
        return

    log(f"Need {need_count} more clip(s) today")

    # Find available unused clips
    available = []
    if os.path.exists("clips"):
        for f in sorted(os.listdir("clips")):
            fp = os.path.join("clips", f)
            if f.endswith(".mp4") and fp not in already_uploaded_files:
                available.append(fp)

    log(f"Found {len(available)} unused clips in /clips")
    clips_to_upload = available[:need_count]
    remaining = need_count - len(clips_to_upload)

    # If we need more clips, download from trending
    source_videos_info = {}  # url -> info for caption generation

    while remaining > 0:
        log(f"Need {remaining} more clips from trending...")
        candidates = get_trending()
        chosen_url = None
        chosen_info = None

        for c in candidates:
            vid_url = f"https://youtube.com/watch?v={c.get('id', '')}"
            try:
                info = get_video_info(vid_url)
                level, issues = check_video(info)
                dur = info.get("duration", 0)
                clips_from_this = math.ceil(dur / CLIP_DURATION)

                log(f"  {c['title'][:60]} -> {level} ({clips_from_this} clips)")

                if level == "HIGH":
                    continue
                if clips_from_this < 1:
                    continue

                chosen_url = vid_url
                chosen_info = info
                break
            except Exception as e:
                continue

        if not chosen_url:
            log("No suitable trending video found.")
            break

        log(f"Downloading: {chosen_info['title'][:60]}")
        video_path = download_video(chosen_url)
        new_clips = clip_video(video_path)
        log(f"Created {len(new_clips)} clips")

        source_videos_info[chosen_url] = chosen_info

        for cp in new_clips:
            if cp not in already_uploaded_files and cp not in clips_to_upload:
                clips_to_upload.append(cp)
                already_uploaded_files.add(cp)
                remaining -= 1
                if remaining <= 0:
                    break

    if not clips_to_upload:
        log("No clips to upload.")
        return

    # Upload
    youtube = authenticate_youtube()
    uploaded_count = 0

    for idx, clip_path in enumerate(clips_to_upload[:CLIPS_PER_DAY]):
        # Find which source video this clip came from
        clip_name = os.path.basename(clip_path)
        source_url = None
        source_info = None
        for url, info in source_videos_info.items():
            if clip_name.startswith(os.path.splitext(info.get("title", ""))[0][:30]):
                source_url = url
                source_info = info
                break

        # Fallback: try extracting info from the file name
        if not source_info:
            source_info = {"title": clip_name.replace("_part", " - Part "), "channel": "Trending", "tags": [], "description": "", "view_count": 0, "duration": 30}

        caption = generate_short_caption(idx + 1, len(clips_to_upload), source_info)
        desc = f"{caption}\n\n#shorts #trending #viral"
        tags = ["shorts", "trending", "viral"] + (source_info.get("tags", []) or [])[:5]

        try:
            upload_short(youtube, clip_path, caption, desc, tags)
            used.append({"date": today, "file": clip_path, "title": caption, "source_url": source_url or ""})
            save_json(DAILY_LOG, used)
            uploaded_count += 1
            log(f"Uploaded {uploaded_count}/{len(clips_to_upload)}")
        except Exception as e:
            log(f"Upload failed: {e}")
            continue

    log(f"Done! Uploaded {uploaded_count} clip(s) today.")

if __name__ == "__main__":
    main()
