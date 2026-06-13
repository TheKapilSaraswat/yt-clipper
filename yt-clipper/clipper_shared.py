import subprocess
import json
import os
import re
import math
import time
import pickle
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import wraps

import config

# ─── RETRY DECORATOR (#5) ────────────────────────────────────────────────

def retry(max_attempts=None, delay=None):
    if max_attempts is None:
        max_attempts = config.cfg["retry_attempts"]
    if delay is None:
        delay = config.cfg["retry_delay"]
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            last_err = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except Exception as e:
                    last_err = e
                    if attempt < max_attempts:
                        time.sleep(delay)
            raise last_err
        return wrapper
    return decorator


# ─── VIDEO INFO ──────────────────────────────────────────────────────────

@retry()
def get_video_info(url):
    cmd = ["yt-dlp", "--dump-json", "--no-download", "--skip-download", url]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=15)
    return json.loads(result.stdout)


# ─── SAFETY CHECKS (#6) ──────────────────────────────────────────────────

RED_FLAG_TITLE = config.cfg["red_flag_title_keywords"]
RED_FLAG_DESC = config.cfg["red_flag_desc_patterns"]
MUSIC_KEYWORDS = ["song", "music", "audio", "lyrics", "cover", "remix",
                  "official video", "music video", "official audio", "vevo",
                  "soundtrack", "album", "playlist", "live session", "acoustic"]


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

    # Title keywords
    rfk = RED_FLAG_TITLE.copy()
    if official:
        rfk = [kw for kw in rfk if kw not in ("official video", "music video", "official audio", "audio")]
    found = [kw for kw in rfk if kw in tl]
    if found:
        issues.append(f"Title: {found}")

    # Description disclaimer patterns
    dl = desc.lower()
    found = [p for p in RED_FLAG_DESC if re.search(p, dl)]
    if found:
        issues.append("Has disclaimer patterns")

    # Channel verification
    if not verified:
        issues.append("Not verified")

    # Follower count
    min_fol = config.cfg["min_followers"]
    if followers < min_fol:
        issues.append(f"Only {followers:,} followers")
    elif followers > 100000:
        pass  # well-established

    # Music category or title keywords
    if "music" in str(cats).lower() and not official:
        issues.append("Music from non-official")
    found_music = [kw for kw in MUSIC_KEYWORDS if kw in tl]
    if found_music:
        issues.append(f"Music keywords: {found_music}")

    # Duration
    max_dur = config.cfg["max_duration"]
    if duration > max_dur:
        issues.append(f"Very long ({duration//60}min)")

    # Channel name in title
    if not (set(channel.lower().split()) & set(tl.split())):
        issues.append("Channel not in title")

    # ── Enhanced checks (#6) ──
    age = info.get("age_limit", 0)
    if age and age > 0:
        issues.append(f"Age restricted ({18 if age >= 18 else age}+)")

    avail = info.get("availability", "")
    if avail and avail != "public":
        issues.append(f"Not public ({avail})")

    like_count = info.get("like_count", 0)
    view_count = info.get("view_count", 0)
    if view_count > 1000 and like_count > 0:
        ratio = like_count / view_count
        if ratio < 0.005:
            issues.append(f"Low engagement ({ratio:.1%} like/views)")

    embed = info.get("embed", None)
    if embed is not None:
        embeddable = embed if isinstance(embed, bool) else embed.get("embeddable", True)
        if not embeddable:
            issues.append("Embedding disabled")

    # Risk level
    thresholds = config.cfg["risk_thresholds"]
    if len(issues) >= thresholds["high"]:
        level = "HIGH"
    elif len(issues) >= thresholds["medium"]:
        level = "MEDIUM"
    else:
        level = "LOW"

    return level, issues


# ─── DETAILED RISK CHECK WITH WEIGHTED PROBABILITY SCORE ─────────────────

RISK_WEIGHTS = {
    "title_red_flags": 0.25,
    "desc_disclaimers": 0.40,
    "not_verified": 0.20,
    "low_followers": 0.15,
    "music_category": 0.35,
    "music_keywords": 0.30,
    "very_long": 0.10,
    "channel_not_in_title": 0.10,
    "age_restricted": 0.50,
    "not_public": 0.60,
    "low_engagement": 0.20,
    "embedding_disabled": 0.30,
}
AUTO_HIGH_KEYS = {"age_restricted", "not_public", "embedding_disabled"}


def check_video_detailed(info):
    checks = []
    title = info.get("title", "")
    desc = info.get("description", "") or ""
    channel = info.get("channel", "")
    followers = info.get("channel_follower_count") or 0
    verified = info.get("channel_is_verified", False)
    cats = info.get("categories", []) or []
    duration = info.get("duration", 0)
    official = is_official(info)
    tl = title.lower()

    rfk = RED_FLAG_TITLE.copy()
    if official:
        rfk = [kw for kw in rfk if kw not in ("official video", "music video", "official audio", "audio")]
    found = [kw for kw in rfk if kw in tl]
    checks.append({"test": "Title red-flag keywords", "passed": not found, "detail": f"Keywords: {found}" if found else "Clean", "weight_key": "title_red_flags"})

    dl = desc.lower()
    found = [p for p in RED_FLAG_DESC if re.search(p, dl)]
    checks.append({"test": "Description disclaimers", "passed": not found, "detail": f"Patterns: {found}" if found else "Clean", "weight_key": "desc_disclaimers"})

    checks.append({"test": "Channel verified", "passed": verified, "detail": "Verified" if verified else "Not verified", "weight_key": "not_verified"})

    min_fol = config.cfg["min_followers"]
    checks.append({"test": "Follower count", "passed": followers >= min_fol, "detail": f"{followers:,} followers (min {min_fol:,})", "weight_key": "low_followers"})

    music_cat = "music" in str(cats).lower() and not official
    checks.append({"test": "Music category", "passed": not music_cat, "detail": f"Categories: {cats}" if music_cat else "Not music category", "weight_key": "music_category"})

    found_music = [kw for kw in MUSIC_KEYWORDS if kw in tl]
    checks.append({"test": "Music keywords in title", "passed": not found_music, "detail": f"Keywords: {found_music}" if found_music else "Clean", "weight_key": "music_keywords"})

    max_dur = config.cfg["max_duration"]
    checks.append({"test": "Duration", "passed": duration <= max_dur, "detail": f"{duration//60}min (max {max_dur//60}min)" if duration > max_dur else f"{duration//60}min OK", "weight_key": "very_long"})

    ch_in_title = bool(set(channel.lower().split()) & set(tl.split()))
    checks.append({"test": "Channel name in title", "passed": ch_in_title, "detail": "Present" if ch_in_title else "Missing", "weight_key": "channel_not_in_title"})

    age = info.get("age_limit", 0)
    checks.append({"test": "Age restriction", "passed": not (age and age > 0), "detail": f"Age limit: {age}" if age else "None", "weight_key": "age_restricted"})

    avail = info.get("availability", "")
    checks.append({"test": "Public availability", "passed": not (avail and avail != "public"), "detail": avail if avail and avail != "public" else "Public", "weight_key": "not_public"})

    like_count = info.get("like_count", 0)
    view_count = info.get("view_count", 0)
    low_eng = view_count > 1000 and like_count > 0 and (like_count / view_count) < 0.005
    checks.append({"test": "Engagement ratio", "passed": not low_eng, "detail": f"{like_count:,}/{view_count:,} ({like_count/view_count:.1%})" if low_eng else f"{like_count:,}/{view_count:,}", "weight_key": "low_engagement"})

    embed = info.get("embed", None)
    embed_disabled = False
    if embed is not None:
        embeddable = embed if isinstance(embed, bool) else embed.get("embeddable", True)
        embed_disabled = not embeddable
    checks.append({"test": "Embedding enabled", "passed": not embed_disabled, "detail": "Disabled" if embed_disabled else "Enabled", "weight_key": "embedding_disabled"})

    score = 0.0
    issues = []
    for c in checks:
        if not c["passed"]:
            issues.append(c["test"])
            score += RISK_WEIGHTS.get(c["weight_key"], 0)
    score = min(score, 1.0)

    critical_failures = [c for c in checks if c["weight_key"] in AUTO_HIGH_KEYS and not c["passed"]]
    if critical_failures or score >= 0.5:
        level = "HIGH"
    elif score >= 0.2:
        level = "MEDIUM"
    else:
        level = "LOW"

    return level, issues, checks


# ─── BATCH SUITABLE VIDEO FINDER ─────────────────────────────────────────

def find_suitable_videos(count, used_source_urls=None, log_fn=print):
    if used_source_urls is None:
        used_source_urls = set()

    candidates = get_trending()
    if not candidates:
        log_fn("No trending candidates found.")
        return []

    seen_urls = set(used_source_urls)
    max_workers = config.cfg["concurrent_checks"]
    suitable = []
    all_results = []

    def check_candidate(c):
        vid_url = f"https://youtube.com/watch?v={c.get('id', '')}"
        if vid_url in seen_urls:
            return None
        try:
            info = get_video_info(vid_url)
            level, issues, checks = check_video_detailed(info)
            return {
                "url": vid_url,
                "info": info,
                "title": c.get("title", "?")[:80],
                "level": level,
                "issues": issues,
                "checks": checks,
                "view_count": info.get("view_count", 0) or 0,
            }
        except Exception:
            return None

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(check_candidate, c): c for c in candidates}
        for f in as_completed(futures):
            result = f.result()
            if result:
                all_results.append(result)
                if result["level"] != "HIGH":
                    suitable.append(result)

    suitable.sort(key=lambda r: r["view_count"], reverse=True)

    for r in sorted(all_results, key=lambda x: x["view_count"], reverse=True):
        issues = ", ".join(r["issues"]) if r["issues"] else "none"
        log_fn(f"  {r['title'][:50]} | {r['view_count']:,} views | Risk: {r['level']} | Issues: {issues}")

    log_fn(f"Suitable: {len(suitable)} videos")
    return suitable[:count]


# ─── TRENDING DISCOVERY (#1) ─────────────────────────────────────────────

def get_trending():
    urls = config.cfg["trending_urls"]
    seen = set()
    all_videos = []

    for url in urls:
        try:
            r = subprocess.run(
                ["yt-dlp", "--flat-playlist", "--dump-json", "--no-download", url],
                capture_output=True, text=True, check=True, timeout=60
            )
            for line in r.stdout.strip().split("\n"):
                if line:
                    try:
                        item = json.loads(line)
                        vid = item.get("id", "")
                        if vid and vid not in seen:
                            seen.add(vid)
                            all_videos.append(item)
                    except json.JSONDecodeError:
                        continue
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            continue

    all_videos.sort(key=lambda v: v.get("view_count", 0) or 0, reverse=True)
    return all_videos[: config.cfg["max_candidates"]]


def find_best_trending(used_source_urls=None, log_fn=print):
    if used_source_urls is None:
        used_source_urls = set()

    candidates = get_trending()
    if not candidates:
        return None, None

    # Concurrent checking (#4)
    max_workers = config.cfg["concurrent_checks"]
    batch = candidates[: max_workers * 2]

    def check_candidate(c):
        vid_url = f"https://youtube.com/watch?v={c.get('id', '')}"
        if vid_url in used_source_urls:
            return None
        try:
            info = get_video_info(vid_url)
            level, issues = check_video(info)
            dur = info.get("duration", 0)
            clips = math.ceil(dur / config.cfg["clip_duration"])
            return {
                "url": vid_url,
                "info": info,
                "title": c.get("title", "?")[:60],
                "level": level,
                "issues": issues,
                "clips": clips,
            }
        except Exception:
            return None

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(check_candidate, c): c for c in batch}
        results = []
        for f in as_completed(futures):
            result = f.result()
            if result and result["level"] != "HIGH" and result["clips"] >= 1:
                results.append(result)

    if not results:
        return None, None

    results.sort(key=lambda r: int(r["info"].get("view_count", 0) or 0), reverse=True)
    best = results[0]
    log_fn(f"  {best['title']} -> {best['level']} ({best['clips']} clips)")
    return best["url"], best["info"]


# ─── DOWNLOAD & CLIP ─────────────────────────────────────────────────────

@retry()
def download_video(url, output_dir="original"):
    os.makedirs(output_dir, exist_ok=True)
    tpl = os.path.join(output_dir, "%(title)s.%(ext)s")
    subprocess.run(
        ["yt-dlp", "-f", "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best",
         "-o", tpl, url],
        check=True, capture_output=True, text=True, timeout=600
    )
    video_exts = (".mp4", ".webm", ".mkv", ".m4a")
    files = [f for f in os.listdir(output_dir) if f.lower().endswith(video_exts)]
    if not files:
        raise FileNotFoundError(f"No video file found in {output_dir}")
    return max((os.path.join(output_dir, f) for f in files), key=os.path.getmtime)


def get_duration(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True, check=True
    )
    return float(r.stdout.strip())


def get_resolution(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0", path],
        capture_output=True, text=True, check=True
    )
    parts = r.stdout.strip().split(",")
    if len(parts) == 2:
        return int(parts[0]), int(parts[1])
    return 1920, 1080


def clip_video(path, output_dir="clips", seg=None, vertical=None, limit=1):
    if seg is None:
        seg = config.cfg["clip_duration"]
    if vertical is None:
        vertical = config.cfg["vertical_shorts"]

    os.makedirs(output_dir, exist_ok=True)
    dur = get_duration(path)
    vids = math.ceil(dur / seg)
    num = min(vids, limit) if limit else vids
    base = os.path.splitext(os.path.basename(path))[0]
    paths = []

    for i in range(num):
        name = f"{base}_part{i+1:03d}.mp4"
        p = os.path.join(output_dir, name)
        start = i * seg

        # ── Vertical 9:16 crop (#3) ──
        if vertical:
            w, h = get_resolution(path)
            aspect = w / h
            if aspect > 1:
                # Landscape: crop center to 9:16 then scale
                video_filter = (
                    f"crop=ih*9/16:ih,scale={config.cfg['shorts_width']}:{config.cfg['shorts_height']}:force_original_aspect_ratio=1,"
                    f"pad={config.cfg['shorts_width']}:{config.cfg['shorts_height']}:(ow-iw)/2:(oh-ih)/2"
                )
            elif aspect < 0.6:
                # Already very tall: just scale + pad
                video_filter = (
                    f"scale={config.cfg['shorts_width']}:{config.cfg['shorts_height']}:force_original_aspect_ratio=1,"
                    f"pad={config.cfg['shorts_width']}:{config.cfg['shorts_height']}:(ow-iw)/2:(oh-ih)/2"
                )
            else:
                # Near 4:3 or square: scale to fit, pad top/bottom
                video_filter = (
                    f"scale={config.cfg['shorts_width']}:{config.cfg['shorts_height']}:force_original_aspect_ratio=1,"
                    f"pad={config.cfg['shorts_width']}:{config.cfg['shorts_height']}:(ow-iw)/2:(oh-ih)/2"
                )
            cmd = [
                "ffmpeg", "-y",
                "-ss", str(start),
                "-i", path,
                "-t", str(seg),
                "-vf", video_filter,
                "-preset", "ultrafast",
                "-c:a", "aac",
                "-movflags", "+faststart",
                p,
            ]
        else:
            cmd = [
                "ffmpeg", "-y",
                "-ss", str(start),
                "-i", path,
                "-t", str(seg),
                "-c", "copy",
                p,
            ]
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        paths.append(p)

    return paths


# ─── SEO CAPTIONS (#2) ───────────────────────────────────────────────────

def generate_caption(clip_index, total_clips, video_info):
    title = video_info.get("title", "")
    channel = video_info.get("channel", "")
    tags = video_info.get("tags", []) or []
    view_count = video_info.get("view_count", 0)
    duration = video_info.get("duration", 0)
    desc = video_info.get("description", "") or ""

    # Build rich keyword corpus
    raw = f"{title} {channel} {desc} {' '.join(tags[:15])}"
    raw = re.sub(r"[^a-z0-9\s]", " ", raw.lower())
    words = [w for w in raw.split() if len(w) > 3]
    freq = {}
    for w in words:
        freq[w] = freq.get(w, 0) + 1
    top_kw = [w for w, c in sorted(freq.items(), key=lambda x: -x[1]) if c > 1][:5]

    # Build engaging SEO caption
    kw_part = " ".join(top_kw[:3]).title() if top_kw else (title.split()[0] if title else "Trending")

    # Hashtags: include channel name, content keywords
    ht = ["#shorts", "#trending", "#viral"]
    if channel:
        channel_tag = "#" + re.sub(r"[^a-zA-Z0-9]", "", channel.split()[0].lower())
        if channel_tag not in ht:
            ht.append(channel_tag)
    for kw in top_kw[:3]:
        ht.append("#" + kw)

    caption = (
        f"{kw_part} | {title[:60]} | "
        f"Part {clip_index}/{total_clips} | "
        f"{' '.join(ht)}"
    )

    if len(caption.split()) > 95:
        caption = " ".join(caption.split()[:95])

    return caption


# ─── UPLOAD ──────────────────────────────────────────────────────────────

def authenticate_youtube(readonly=False):
    try:
        from google.auth.transport.requests import Request
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError:
        return None

    if not os.path.exists(config.cfg["secret_file"]):
        return None

    scopes = ["https://www.googleapis.com/auth/youtube.upload"]
    if readonly:
        scopes.append("https://www.googleapis.com/auth/youtube.readonly")

    creds = None
    token_file = config.cfg["token_file"]
    if os.path.exists(token_file):
        with open(token_file, "rb") as f:
            creds = pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(config.cfg["secret_file"], scopes)
            creds = flow.run_local_server(port=0)
        with open(token_file, "wb") as f:
            pickle.dump(creds, f)
    return build("youtube", "v3", credentials=creds)


@retry()
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
    response = request.execute()
    return response["id"]


# ─── JSON HELPERS ────────────────────────────────────────────────────────

def load_json(path, default):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
