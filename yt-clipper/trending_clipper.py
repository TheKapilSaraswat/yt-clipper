import os
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")

import config
from clipper_shared import (
    find_best_trending,
    check_video,
    download_video,
    clip_video,
    generate_caption,
    load_json,
    save_json,
)

DAILY_LOG = config.cfg["daily_log"]

def main():
    used = load_json(DAILY_LOG, [])
    used_source_urls = set(u.get("source_url", "") for u in used if u.get("source_url"))

    print("Fetching trending candidates...")
    chosen_url, chosen_info = find_best_trending(used_source_urls)
    if not chosen_url:
        print("No suitable trending video found.")
        return

    print(f"Video: {chosen_info.get('title', '?')[:70]}")
    print(f"Views: {chosen_info.get('view_count', 0):,}")
    print(f"Channel: {chosen_info.get('channel', '?')}")

    level, issues = check_video(chosen_info)
    print(f"Risk: {level} ({len(issues)} issues)")

    for iss in issues[:5]:
        print(f"  - {iss}")

    video_path = download_video(chosen_url)
    print(f"Downloaded to: {video_path}")
    clips = clip_video(video_path)
    print(f"Clipped into {len(clips)} segments")

    caption = generate_caption(1, len(clips), chosen_info)
    print(f"SEO caption: {caption}")

    used.append({
        "date": datetime.now().strftime("%Y-%m-%d"),
        "file": video_path,
        "title": chosen_info.get("title", ""),
        "source_url": chosen_url,
    })
    save_json(DAILY_LOG, used)

    for folder in ("clips", "original"):
        if os.path.exists(folder):
            for f in os.listdir(folder):
                fp = os.path.join(folder, f)
                if os.path.isfile(fp):
                    os.remove(fp)


if __name__ == "__main__":
    main()
