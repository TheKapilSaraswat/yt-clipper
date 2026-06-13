import os
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")

import config
from clipper_shared import (
    find_best_trending,
    download_video,
    clip_video,
    generate_caption,
    authenticate_youtube,
    upload_short,
    load_json,
    save_json,
)

DAILY_LOG = config.cfg["daily_log"]
CLIPS_PER_DAY = config.cfg["clips_per_day"]
SECRET_FILE = config.cfg["secret_file"]
TOKEN_FILE = config.cfg["token_file"]


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def main():
    used = load_json(DAILY_LOG, [])
    today_date = datetime.now().strftime("%Y-%m-%d")

    used_source_urls = set(u.get("source_url", "") for u in used if u.get("source_url"))
    uploaded_today = [u for u in used if u["date"] == today_date]
    already_uploaded_files = set(u["file"] for u in used)
    need_count = CLIPS_PER_DAY - len(uploaded_today)

    if need_count <= 0:
        log(f"Already uploaded {CLIPS_PER_DAY} clips today. Done.")
        return

    log(f"Need {need_count} more clip(s) today")

    available = []
    if os.path.exists("clips"):
        for f in sorted(os.listdir("clips")):
            fp = os.path.join("clips", f)
            if f.endswith(".mp4") and fp not in already_uploaded_files:
                available.append(fp)

    log(f"Found {len(available)} unused clips in /clips")
    clips_to_upload = available[:need_count]
    remaining = need_count - len(clips_to_upload)

    source_videos_info = {}
    source_url_by_video_id = {}

    while remaining > 0:
        log(f"Need {remaining} more clips from trending...")
        chosen_url, chosen_info = find_best_trending(used_source_urls, log)
        if not chosen_url:
            log("No suitable trending video found.")
            break

        used_source_urls.add(chosen_url)
        video_id = chosen_url.split("v=")[-1]
        log(f"Downloading: {chosen_info['title'][:60]}")
        video_path = download_video(chosen_url)
        ext = os.path.splitext(video_path)[1]
        renamed = os.path.join(os.path.dirname(video_path), f"{video_id}{ext}")
        if os.path.exists(video_path) and not os.path.exists(renamed):
            os.rename(video_path, renamed)
            video_path = renamed
        new_clips = clip_video(video_path)
        log(f"Created {len(new_clips)} clips")

        source_videos_info[chosen_url] = chosen_info
        source_url_by_video_id[video_id] = chosen_url

        cp = new_clips[0]
        if cp not in already_uploaded_files and cp not in clips_to_upload:
            clips_to_upload.append(cp)
            already_uploaded_files.add(cp)
            remaining -= 1

    if not clips_to_upload:
        log("No clips to upload.")
        return

    youtube = authenticate_youtube()
    if not youtube:
        log(f"\nCreated {len(clips_to_upload)} clip(s) in 'clips/' folder.")
        log("Set up client_secret.json to enable auto-upload to YouTube.")
        if os.path.exists("original"):
            for f in os.listdir("original"):
                fp = os.path.join("original", f)
                if os.path.isfile(fp):
                    os.remove(fp)
        return

    uploaded_count = 0
    processed_source_urls = set()

    for idx, clip_path in enumerate(clips_to_upload[:CLIPS_PER_DAY]):
        clip_name = os.path.basename(clip_path)
        source_info = None
        source_url_for_clip = ""

        clip_video_id = clip_name.split("_")[0]
        src_url = source_url_by_video_id.get(clip_video_id)
        if src_url:
            source_url_for_clip = src_url
            source_info = source_videos_info.get(src_url)
        if not source_info:
            source_info = {
                "title": clip_name.replace("_part", " - Part "),
                "channel": "Trending",
                "tags": [],
                "description": "",
                "view_count": 0,
                "duration": 30,
            }

        caption = generate_caption(idx + 1, len(clips_to_upload), source_info)
        desc = f"{caption}\n\n#shorts #trending #viral"
        tags = ["shorts", "trending", "viral"] + (source_info.get("tags", []) or [])[:5]

        try:
            upload_short(youtube, clip_path, caption, desc, tags)
            used.append({"date": today_date, "file": clip_path, "title": caption, "source_url": source_url_for_clip})
            processed_source_urls.add(source_url_for_clip)
            save_json(DAILY_LOG, used)
            uploaded_count += 1
            log(f"Uploaded {uploaded_count}/{len(clips_to_upload)}")
        except Exception as e:
            log(f"Upload failed: {e}")
            continue

    log(f"Done! Uploaded {uploaded_count} clip(s) today.")

    for url in source_videos_info:
        if url and url not in processed_source_urls:
            used.append({"date": today_date, "file": f"source:{url}", "title": f"source_blacklist:{url}", "source_url": url})
            save_json(DAILY_LOG, used)

    log("Cleaning up clips from today's source videos...")
    for folder in ("clips", "original"):
        if os.path.exists(folder):
            for f in os.listdir(folder):
                fp = os.path.join(folder, f)
                if os.path.isfile(fp):
                    os.remove(fp)
    log("Cleanup complete.")


if __name__ == "__main__":
    main()
