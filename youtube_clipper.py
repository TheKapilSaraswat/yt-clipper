import sys
import argparse
import os

sys.stdout.reconfigure(encoding="utf-8")

import config
from clipper_shared import (
    get_video_info,
    check_video,
    download_video,
    clip_video,
    generate_caption,
)


def main():
    parser = argparse.ArgumentParser(description="Clip a YouTube video")
    parser.add_argument("url", help="YouTube video URL")
    args = parser.parse_args()

    print(f"Checking: {args.url}")
    info = get_video_info(args.url)

    level, issues = check_video(info)
    print(f"Risk: {level}")
    for iss in issues:
        print(f"  - {iss}")

    if level == "HIGH":
        print("Risk too high, skipping download.")
        return

    vpath = download_video(args.url)
    print(f"Downloaded: {vpath}")
    clips = clip_video(vpath)

    cap = generate_caption(1, len(clips), info)
    print(f"Clipped {len(clips)} segments")
    print(f"SEO caption: {cap}")

    if "--keep" not in sys.argv:
        for folder in ("clips", "original"):
            if os.path.exists(folder):
                for f in os.listdir(folder):
                    fp = os.path.join(folder, f)
                    if os.path.isfile(fp):
                        os.remove(fp)


if __name__ == "__main__":
    main()
