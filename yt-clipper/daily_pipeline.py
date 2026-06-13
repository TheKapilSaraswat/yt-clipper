import os
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")

import config
from clipper_shared import (
    find_suitable_videos,
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


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def main():
    used = load_json(DAILY_LOG, [])
    today_date = datetime.now().strftime("%Y-%m-%d")

    used_source_urls = set(u.get("source_url", "") for u in used if u.get("source_url"))
    uploaded_today = [u for u in used if u["date"] == today_date]
    already = set(u["file"] for u in used)
    need = CLIPS_PER_DAY - len(uploaded_today)

    if need <= 0:
        log(f"Already uploaded {CLIPS_PER_DAY} clips today. Done.")
        return

    log(f"Need {need} more clip(s) today")

    clips = []
    if os.path.exists("clips"):
        for f in sorted(os.listdir("clips")):
            fp = os.path.join("clips", f)
            if f.endswith(".mp4") and fp not in already:
                clips.append(fp)
    clips = clips[:need]
    log(f"Existing clips: {len(clips)}")
    remaining = need - len(clips)

    # Find suitable trending videos upfront (single batch)
    if remaining > 0:
        log(f"Scanning trending for {remaining} clean videos...")
        new_videos = find_suitable_videos(remaining, used_source_urls, log)
        if not new_videos:
            log("No suitable trending videos found.")

        for video in new_videos:
            chosen_url = video["url"]
            chosen_info = video["info"]
            video_id = chosen_url.split("v=")[-1]
            used_source_urls.add(chosen_url)

            log(f"\n[{len(clips)+1}/{need}] {chosen_info.get('title', '')[:60]}")
            log(f"  Views: {chosen_info.get('view_count', 0):,} | Risk: {video['level']}")

            vp = download_video(chosen_url)
            ext = os.path.splitext(vp)[1]
            renamed = os.path.join(os.path.dirname(vp), f"{video_id}{ext}")
            if os.path.exists(vp) and not os.path.exists(renamed):
                os.rename(vp, renamed)
                vp = renamed

            nc = clip_video(vp)  # limit=1
            if not nc:
                log("  No clips created, skipping")
                continue
            cp = nc[0]
            log(f"  Created 30s clip")
            clips.append(cp)

    if not clips:
        log("No clips to upload.")
        return

    # Authenticate once, upload all clips
    youtube = authenticate_youtube()
    if not youtube:
        log(f"\nCreated {len(clips)} clip(s) in 'clips/' folder.")
        log("Set up client_secret.json to enable auto-upload.")
        for folder in ("clips", "original"):
            if os.path.exists(folder):
                for f in os.listdir(folder):
                    fp = os.path.join(folder, f)
                    if os.path.isfile(fp):
                        os.remove(fp)
        return

    uploaded = 0
    for idx, cp in enumerate(clips[:CLIPS_PER_DAY]):
        clip_name = os.path.basename(cp)
        src_info = {"title": clip_name.replace("_part", " - Part "), "tags": [], "description": "", "channel": "Trending", "view_count": 0, "duration": 30}
        cap = generate_caption(idx + 1, len(clips), src_info)
        desc = f"{cap}\n\n#shorts #trending #viral"
        tags = ["shorts", "trending", "viral"]

        try:
            log(f"  Uploading [{idx+1}/{len(clips)}]: {cap[:50]}...")
            upload_short(youtube, cp, cap, desc, tags)
            used.append({"date": today_date, "file": cp, "title": cap, "source_url": ""})
            save_json(DAILY_LOG, used)
            uploaded += 1
            log(f"  \u2713 Uploaded")
        except Exception as e:
            log(f"  Upload failed: {e}")

    log(f"\nDone! Uploaded {uploaded}/{len(clips)} clip(s) today.")

    for folder in ("clips", "original"):
        if os.path.exists(folder):
            for f in os.listdir(folder):
                fp = os.path.join(folder, f)
                if os.path.isfile(fp):
                    os.remove(fp)


if __name__ == "__main__":
    main()
