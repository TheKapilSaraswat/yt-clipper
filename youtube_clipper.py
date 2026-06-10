import subprocess
import sys
import os
import math
import json
import re

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
    cmd = [
        "yt-dlp", "--dump-json",
        "--no-download", "--skip-download",
        url
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(result.stdout)

def _is_likely_official(info):
    title = info.get("title", "").lower()
    channel = info.get("channel", "").lower()
    followers = info.get("channel_follower_count") or 0
    verified = info.get("channel_is_verified", False)
    channel_words = set(channel.split())
    title_words = set(title.split())
    overlap = channel_words & title_words
    channel_in_title = bool(overlap)
    return verified and followers > 50000 and channel_in_title

def check_video(info):
    issues = []
    passed = []

    title = info.get("title", "")
    description = info.get("description", "") or ""
    channel = info.get("channel", "")
    channel_follower_count = info.get("channel_follower_count") or 0
    is_verified = info.get("channel_is_verified", False)
    license_type = info.get("license", "")
    categories = info.get("categories", []) or []
    duration = info.get("duration", 0)
    official = _is_likely_official(info)

    title_lower = title.lower()

    red_flag_keywords = RED_FLAG_TITLE_KEYWORDS.copy()
    if official:
        red_flag_keywords = [kw for kw in red_flag_keywords if kw not in ("official video", "music video", "audio", "visualizer")]
    found_title_redflags = [kw for kw in red_flag_keywords if kw in title_lower]
    if found_title_redflags:
        issues.append(f"Title contains potential red flags: {found_title_redflags}")
    else:
        passed.append("Title looks clean")

    desc_lower = description.lower()
    found_desc_redflags = [pat for pat in RED_FLAG_DESC_KEYWORDS if re.search(pat, desc_lower)]
    if found_desc_redflags:
        issues.append("Description contains disclaimer patterns often used for reused content")
    else:
        passed.append("Description has no disclaimer patterns")

    if is_verified:
        passed.append("Channel is verified (lower risk)")
    else:
        issues.append("Channel is not verified")

    if channel_follower_count > 100000:
        passed.append(f"Channel has {channel_follower_count:,} followers (established channel)")
    elif channel_follower_count > 10000:
        passed.append(f"Channel has {channel_follower_count:,} followers")
    else:
        issues.append(f"Channel has only {channel_follower_count:,} followers (small/unestablished channel)")

    if "creative" in license_type.lower():
        passed.append("Video uses Creative Commons license (reuse-friendly)")
    else:
        issues.append("Video uses standard YouTube license (restrictive)")

    if "music" in str(categories).lower():
        if official:
            passed.append("Music category — official channel upload (expected)")
        else:
            issues.append("Video categorized as Music — likely contains copyrighted audio")

    if duration > 3600:
        issues.append(f"Video is {duration//60} min long — could be full movie/TV episode")
    elif duration > 1800:
        issues.append(f"Video is {duration//60} min long — verify it's not a full-length show")
    else:
        passed.append(f"Duration ({duration//60}m {duration%60}s) is typical for standard content")

    channel_words = set(channel.lower().split())
    title_words = set(title_lower.split())
    if channel_words & title_words:
        passed.append("Channel name appears in title (likely original content)")
    else:
        issues.append("Channel name doesn't appear in title (may be reused content)")

    return issues, passed

def risk_level(issues_count, total_checks):
    if total_checks == 0:
        return "LOW"
    ratio = issues_count / total_checks
    if ratio <= 0.25:
        return "LOW"
    elif ratio <= 0.5:
        return "MEDIUM"
    else:
        return "HIGH"

def download_youtube_video(url, output_dir="original"):
    os.makedirs(output_dir, exist_ok=True)
    output_template = os.path.join(output_dir, "%(title)s.%(ext)s")
    cmd = [
        "yt-dlp",
        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "-o", output_template,
        url
    ]
    print(f"Downloading: {url}")
    subprocess.run(cmd, check=True)
    files = [f for f in os.listdir(output_dir) if f.endswith(".mp4")]
    if not files:
        raise FileNotFoundError("No MP4 file was downloaded.")
    latest = max(
        (os.path.join(output_dir, f) for f in files),
        key=os.path.getmtime
    )
    return latest

def get_video_duration(video_path):
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "csv=p=0",
        video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(result.stdout.strip())

def split_video(video_path, segment_duration=30, output_dir="clips"):
    os.makedirs(output_dir, exist_ok=True)
    duration = get_video_duration(video_path)
    num_clips = math.ceil(duration / segment_duration)
    base = os.path.splitext(os.path.basename(video_path))[0]
    clip_paths = []

    for i in range(num_clips):
        start = i * segment_duration
        clip_name = f"{base}_part{i+1:03d}.mp4"
        clip_path = os.path.join(output_dir, clip_name)
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-ss", str(start),
            "-t", str(segment_duration),
            "-c", "copy",
            clip_path
        ]
        print(f"Creating clip {i+1}/{num_clips}: {clip_name}")
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        clip_paths.append(clip_path)

    return clip_paths

def main():
    if len(sys.argv) < 2:
        print("Usage: python youtube_clipper.py <youtube_url> [segment_duration]")
        print("       segment_duration defaults to 30 seconds")
        sys.exit(1)

    url = sys.argv[1]
    segment_duration = int(sys.argv[2]) if len(sys.argv) > 2 else 30

    try:
        print("--- Checking video before download ---")
        info = get_video_info(url)
        issues, passed = check_video(info)
        total = len(issues) + len(passed)
        level = risk_level(len(issues), total)

        print(f"Title:   {info.get('title', 'Unknown')}")
        print(f"Channel: {info.get('channel', 'Unknown')}")
        print(f"Risk:    {level} ({len(issues)} issue(s) found)\n")

        if level == "HIGH":
            print("Video has HIGH risk of copyright/policy issues. Download blocked.")
            print("Use 'video_checker.py <url>' to see details.")
            sys.exit(1)
        elif level == "MEDIUM":
            print("Video shows MEDIUM risk. Checking recommended.")
            print("Proceeding with download...\n")

        video_path = download_youtube_video(url)
        print(f"Downloaded: {video_path}")
        clips = split_video(video_path, segment_duration)
        print(f"\nDone! Created {len(clips)} clips in '{os.path.dirname(clips[0])}':")
        for c in clips:
            print(f"  {c}")
    except subprocess.CalledProcessError as e:
        print(f"Error: {e.stderr or e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
