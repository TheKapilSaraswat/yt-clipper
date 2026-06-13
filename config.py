import os
import json

DEFAULTS = {
    "clips_per_day": 6,
    "clip_duration": 30,
    "max_candidates": 50,
    "region": "US",
    "trending_urls": [
        "https://www.youtube.com/results?search_query=a&sp=CAMSBAgEEAE%3D",
        "https://www.youtube.com/results?search_query=video&sp=CAMSBAgEEAE%3D",
        "https://www.youtube.com/results?search_query=trending&sp=CAMSBAgEEAE%3D",
    ],
    "red_flag_title_keywords": [
        "lyrics", "cover", "remix", "mashup", "full movie", "full episode",
        "movie clip", "scene from", "official video", "music video", "audio",
        "song", "vevo", "official audio", "soundtrack", "album", "playlist",
    ],
    "red_flag_desc_patterns": [
        r"no copyright", r"copyright (disclaimer|notice|free)",
        r"fair use", r"all rights belong", r"i do not own",
        r"no infringement", r"for entertainment purposes only",
    ],
    "risk_thresholds": {"low": 0, "medium": 2, "high": 4},
    "min_followers": 10000,
    "max_duration": 3600,
    "vertical_shorts": True,
    "shorts_width": 1080,
    "shorts_height": 1920,
    "retry_attempts": 3,
    "retry_delay": 2,
    "concurrent_checks": 5,
    "daily_log": "upload_log.json",
    "secret_file": "client_secret.json",
    "token_file": "yt_token.pickle",
}

CONFIG_FILE = "clipper_config.json"


def load():
    merged = dict(DEFAULTS)
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE) as f:
                user = json.load(f)
                merged.update(user)
        except (json.JSONDecodeError, OSError):
            pass
    return merged


def save(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


cfg = load()
