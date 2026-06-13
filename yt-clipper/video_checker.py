import sys
import argparse

sys.stdout.reconfigure(encoding="utf-8")

from clipper_shared import get_video_info, check_video


def main():
    parser = argparse.ArgumentParser(description="Check a YouTube video for safety")
    parser.add_argument("url", help="YouTube video URL")
    args = parser.parse_args()

    print(f"Checking: {args.url}")
    info = get_video_info(args.url)

    print(f"Title: {info.get('title', '?')}")
    print(f"Channel: {info.get('channel', '?')}")
    print(f"Verified: {info.get('channel_is_verified', False)}")
    print(f"Followers: {info.get('channel_follower_count', 0):,}")
    print(f"Views: {info.get('view_count', 0):,}")
    print(f"Duration: {info.get('duration', 0)}s")
    print(f"Categories: {info.get('categories', [])}")
    print(f"Age limit: {info.get('age_limit', 'none')}")
    print(f"Availability: {info.get('availability', 'public')}")

    level, issues = check_video(info)
    print(f"\nRisk level: {level}")
    if issues:
        print("Issues:")
        for iss in issues:
            print(f"  - {iss}")
    else:
        print("No issues found.")


if __name__ == "__main__":
    main()
