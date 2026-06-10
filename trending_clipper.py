import subprocess
import json
import sys
import os
import math
import re
import time

RED_FLAG_TITLE_KEYWORDS = [
    "lyrics", "cover", "remix", "mashup", "tribute", "live cover",
    "full movie", "full episode", "movie clip", "scene from",
    "official video", "music video", "audio", "visualizer",
    "letras", "lyric", "sped up", "slowed", "reverb", "nightcore",
    "extended mix", "dj mix", "bootleg", "flip", "type beat",
]

RED_FLAG_DESC_KEYWORDS = [
    r"no copyright", r"copyright (disclaimer|notice|free)",
    r"fair use", r"all rights belong", r"i do not own",
    r"no infringement", r"copyright (strike|claim)",
    r"for entertainment purposes only", r"uploaded for (educational|promotional)",
    r"credit goes to", r"rights go to", r"owner(s|'s)? (of|:)"
]

def get_video_info(url):
    cmd = ["yt-dlp", "--dump-json", "--no-download", "--skip-download", url]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(result.stdout)

def _is_likely_official(info):
    title = info.get("title", "").lower()
    channel = info.get("channel", "").lower()
    followers = info.get("channel_follower_count") or 0
    verified = info.get("channel_is_verified", False)
    return verified and followers > 50000 and bool(set(channel.split()) & set(title.split()))

def check_video(info):
    issues, passed = [], []
    title = info.get("title", "")
    description = info.get("description", "") or ""
    channel = info.get("channel", "")
    followers = info.get("channel_follower_count") or 0
    verified = info.get("channel_is_verified", False)
    license_type = info.get("license", "")
    categories = info.get("categories", []) or []
    duration = info.get("duration", 0)
    official = _is_likely_official(info)
    title_lower = title.lower()

    rfk = RED_FLAG_TITLE_KEYWORDS.copy()
    if official:
        rfk = [kw for kw in rfk if kw not in ("official video", "music video", "audio", "visualizer")]
    found = [kw for kw in rfk if kw in title_lower]
    if found: issues.append(f"Title red flags: {found}")
    else: passed.append("Title clean")

    desc_lower = description.lower()
    found = [pat for pat in RED_FLAG_DESC_KEYWORDS if re.search(pat, desc_lower)]
    if found: issues.append("Description has disclaimer patterns")
    else: passed.append("Description clean")

    if verified: passed.append("Channel verified")
    else: issues.append("Channel not verified")

    if followers > 100000: passed.append(f"{followers:,} followers (established)")
    elif followers > 10000: passed.append(f"{followers:,} followers")
    else: issues.append(f"Only {followers:,} followers")

    if "creative" in license_type.lower(): passed.append("Creative Commons license")
    else: issues.append("Standard YouTube license")

    if "music" in str(categories).lower():
        if official: passed.append("Music — official channel")
        else: issues.append("Music — likely copyrighted audio")

    if duration > 3600: issues.append(f"{duration//60}min — could be full movie")
    elif duration > 1800: issues.append(f"{duration//60}min — verify content")
    else: passed.append(f"{duration//60}m{duration%60}s — typical duration")

    if set(channel.lower().split()) & set(title_lower.split()):
        passed.append("Channel in title — likely original")
    else:
        issues.append("Channel not in title — may be reused")

    return issues, passed

def risk_level(issues_count, total):
    if total == 0: return "LOW"
    r = issues_count / total
    return "LOW" if r <= 0.25 else "MEDIUM" if r <= 0.5 else "HIGH"

def get_trending_videos(max_results=20):
    print("Fetching trending videos...")

    queries = [
        "ytsearch10:today's trending videos",
        "ytsearch10:viral videos today",
    ]

    seen_ids = set()
    videos = []

    for q in queries:
        try:
            cmd = ["yt-dlp", "--flat-playlist", "--dump-json", "--no-download", q]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            for line in result.stdout.strip().split("\n"):
                if line:
                    try:
                        item = json.loads(line)
                        vid_id = item.get("id", "")
                        if vid_id not in seen_ids:
                            seen_ids.add(vid_id)
                            videos.append(item)
                    except json.JSONDecodeError:
                        continue
        except subprocess.CalledProcessError:
            continue

    videos.sort(key=lambda v: v.get("view_count", 0) or 0, reverse=True)
    return videos[:max_results]

def download_and_clip(url, segment_duration=30):
    os.makedirs("original", exist_ok=True)
    os.makedirs("clips", exist_ok=True)
    output_template = os.path.join("original", "%(title)s.%(ext)s")
    print(f"\nDownloading: {url}")
    subprocess.run(
        ["yt-dlp", "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
         "-o", output_template, url],
        check=True, capture_output=True, text=True
    )
    files = [f for f in os.listdir("original") if f.endswith(".mp4")]
    if not files:
        print("ERROR: No MP4 downloaded.")
        return
    latest = max((os.path.join("original", f) for f in files), key=os.path.getmtime)
    print(f"Downloaded: {os.path.basename(latest)}")

    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", latest]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    duration = float(result.stdout.strip())
    num_clips = math.ceil(duration / segment_duration)
    base = os.path.splitext(os.path.basename(latest))[0]
    print(f"Splitting into {num_clips} clip(s) of {segment_duration}s...")

    for i in range(num_clips):
        start = i * segment_duration
        clip_name = f"{base}_part{i+1:03d}.mp4"
        clip_path = os.path.join("clips", clip_name)
        print(f"  [{i+1}/{num_clips}] {clip_name}")
        subprocess.run(
            ["ffmpeg", "-y", "-i", latest, "-ss", str(start), "-t", str(segment_duration), "-c", "copy", clip_path],
            check=True, capture_output=True, text=True
        )
    print(f"\nDone! {num_clips} clips in 'clips/'")

def main():
    try:
        trending = get_trending_videos()
        if not trending:
            print("No trending videos found.")
            sys.exit(1)

        print(f"Found {len(trending)} trending videos. Scanning each one...\n")

        selected = None
        for i, v in enumerate(trending):
            vid_url = f"https://youtube.com/watch?v={v.get('id', '')}"
            title = v.get("title", "Unknown")
            channel = v.get("channel", v.get("uploader", "Unknown"))
            print(f"[{i+1}/{len(trending)}] Checking: {title[:60]}")

            try:
                info = get_video_info(vid_url)
                issues, passed = check_video(info)
                level = risk_level(len(issues), len(issues) + len(passed))

                status = "PASS" if level in ("LOW", "MEDIUM") else "BLOCKED"
                print(f"      Channel: {channel}")
                print(f"      Risk: {level} ({len(issues)} issues) -> {status}")

                if status == "PASS" and selected is None:
                    if level == "MEDIUM":
                        print(f"      -> Selected (MEDIUM risk, proceeding anyway)")
                    else:
                        print(f"      -> Selected!")
                    selected = vid_url
                    print()
                    break
                print()
                time.sleep(0.5)
            except Exception as e:
                print(f"      Error checking: {e}\n")
                continue

        if not selected:
            print("No suitable trending video found (all had HIGH risk or errors).")
            sys.exit(1)

        download_and_clip(selected)

    except subprocess.CalledProcessError as e:
        print(f"Error: {e.stderr or e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
