import subprocess
import json
import re
import sys

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

    # Title keywords check (skip "official video" / "music video" if official channel)
    red_flag_keywords = RED_FLAG_TITLE_KEYWORDS.copy()
    if official:
        red_flag_keywords = [kw for kw in red_flag_keywords if kw not in ("official video", "music video", "audio", "visualizer")]
    found_title_redflags = [kw for kw in red_flag_keywords if kw in title_lower]
    if found_title_redflags:
        issues.append(f"Title contains potential red flags: {found_title_redflags}")
    else:
        passed.append("Title looks clean")

    # Description red flags
    desc_lower = description.lower()
    found_desc_redflags = [pat for pat in RED_FLAG_DESC_KEYWORDS if re.search(pat, desc_lower)]
    if found_desc_redflags:
        issues.append("Description contains disclaimer patterns often used for reused content")
    else:
        passed.append("Description has no disclaimer patterns")

    # Channel verification
    if is_verified:
        passed.append("Channel is verified (lower risk)")
    else:
        issues.append("Channel is not verified")

    # Channel follower count
    if channel_follower_count > 100000:
        passed.append(f"Channel has {channel_follower_count:,} followers (established channel)")
    elif channel_follower_count > 10000:
        passed.append(f"Channel has {channel_follower_count:,} followers")
    else:
        issues.append(f"Channel has only {channel_follower_count:,} followers (small/unestablished channel)")

    # License check
    if "creative" in license_type.lower():
        passed.append("Video uses Creative Commons license (reuse-friendly)")
    else:
        issues.append("Video uses standard YouTube license (restrictive)")

    # Category check — only flag music if it's NOT the official channel
    if "music" in str(categories).lower():
        if official:
            passed.append("Music category — official channel upload (expected)")
        else:
            issues.append("Video categorized as Music — likely contains copyrighted audio")

    # Duration sanity
    if duration > 3600:
        issues.append(f"Video is {duration//60} min long — could be full movie/TV episode")
    elif duration > 1800:
        issues.append(f"Video is {duration//60} min long — verify it's not a full-length show")
    else:
        passed.append(f"Duration ({duration//60}m {duration%60}s) is typical for standard content")

    # Check if channel name appears in title (likely original)
    channel_words = set(channel.lower().split())
    title_words = set(title_lower.split())
    if channel_words & title_words:
        passed.append("Channel name appears in title (likely original content)")
    else:
        issues.append("Channel name doesn't appear in title (may be reused content)")

    return issues, passed

def risk_level(issues_count, total_checks):
    ratio = issues_count / total_checks if total_checks > 0 else 1
    if ratio <= 0.25:
        return "LOW"
    elif ratio <= 0.5:
        return "MEDIUM"
    else:
        return "HIGH"

def main():
    if len(sys.argv) < 2:
        print("Usage: python video_checker.py <youtube_url>")
        sys.exit(1)

    url = sys.argv[1]
    print(f"Scanning: {url}\n")

    try:
        info = get_video_info(url)
    except subprocess.CalledProcessError as e:
        print(f"Failed to fetch video info: {e.stderr or e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    title = info.get("title", "Unknown")
    channel = info.get("channel", "Unknown")
    duration = info.get("duration", 0)
    upload_date = info.get("upload_date", "")
    followers = info.get("channel_follower_count") or 0
    verified = info.get("channel_is_verified", False)
    license_type = info.get("license", "Unknown")
    categories = info.get("categories", [])
    tags = info.get("tags", []) or []

    print(f"Title:      {title}")
    print(f"Channel:    {channel}")
    print(f"Duration:   {duration//60}m {duration%60}s")
    print(f"Uploaded:   {upload_date}")
    print(f"Followers:  {followers:,}")
    print(f"Verified:   {'Yes' if verified else 'No'}")
    print(f"License:    {license_type}")
    print(f"Categories: {', '.join(categories) if categories else 'None'}")
    print(f"Tags:       {len(tags)} tags")
    print()

    issues, passed = check_video(info)
    total = len(issues) + len(passed)

    print("--- Check Results ---")
    for p in passed:
        print(f"  [OK] {p}")
    for i in issues:
        print(f"  [!] {i}")

    level = risk_level(len(issues), total)
    print(f"\nRisk Level: {level}", end="")
    if level == "LOW":
        print(" — likely safe to use")
    elif level == "MEDIUM":
        print(" — proceed with caution")
    else:
        print(" — high risk of copyright/policy issues")

if __name__ == "__main__":
    main()
