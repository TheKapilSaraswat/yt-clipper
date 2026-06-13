"""Tests for clipper_shared module."""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from clipper_shared import check_video, generate_caption


def make_info(overrides=None):
    base = {
        "title": "Amazing Test Video | Big Channel",
        "description": "Check out this amazing video from Big Channel!",
        "channel": "Big Channel Official",
        "channel_follower_count": 150000,
        "channel_is_verified": True,
        "categories": ["Entertainment"],
        "duration": 120,
        "view_count": 500000,
        "like_count": 25000,
        "tags": ["funny", "trending", "viral", "challenge", "reaction"],
        "age_limit": 0,
        "availability": "public",
        "embed": {"embeddable": True},
    }
    if overrides:
        base.update(overrides)
    return base


def test_low_risk():
    level, issues = check_video(make_info())
    assert level == "LOW", f"Expected LOW, got {level}: {issues}"


def test_medium_risk():
    info = make_info({"channel_is_verified": False, "channel_follower_count": 5000})
    level, issues = check_video(info)
    assert level == "MEDIUM", f"Expected MEDIUM, got {level}: {issues}"
    assert any("Not verified" in i for i in issues)
    assert any("followers" in i for i in issues)


def test_high_risk():
    info = make_info({
        "channel_is_verified": False,
        "channel_follower_count": 100,
        "title": "Best Lyrics Cover Full Movie",
        "categories": ["Music"],
        "age_limit": 18,
    })
    level, issues = check_video(info)
    assert level == "HIGH", f"Expected HIGH, got {level}: {issues}"


def test_red_flag_title():
    info = make_info({"title": "Song Lyrics Official Video"})
    level, issues = check_video(info)
    flagged = [i for i in issues if "Title:" in i]
    assert flagged, "Expected title keyword flag"


def test_disclaimer_pattern():
    info = make_info({"description": "I do not own this video. No copyright intended."})
    level, issues = check_video(info)
    assert any("disclaimer" in i for i in issues), f"Expected disclaimer issue: {issues}"


def test_age_restricted():
    info = make_info({"age_limit": 18})
    level, issues = check_video(info)
    assert any("Age restricted" in i for i in issues), f"Expected age restriction: {issues}"


def test_low_engagement():
    info = make_info({"like_count": 10, "view_count": 50000})
    level, issues = check_video(info)
    assert any("engagement" in i for i in issues), f"Expected engagement issue: {issues}"


def test_embeddable_false():
    info = make_info({"embed": {"embeddable": False}})
    level, issues = check_video(info)
    assert any("Embedding" in i for i in issues), f"Expected embedding issue: {issues}"


def test_not_public():
    info = make_info({"availability": "unlisted"})
    level, issues = check_video(info)
    assert any("public" in i for i in issues), f"Expected availability issue: {issues}"


def test_caption_generation():
    info = make_info()
    cap = generate_caption(1, 6, info)
    assert "Part 1/6" in cap, f"Expected part number in caption: {cap}"
    assert "#shorts" in cap, f"Expected #shorts hashtag: {cap}"
    assert len(cap.split()) <= 95, f"Caption too long: {len(cap.split())} words"


def test_caption_without_channel():
    info = make_info({"channel": "", "tags": []})
    cap = generate_caption(1, 3, info)
    assert cap, "Caption should not be empty"
    assert len(cap.split()) <= 95


def test_config_defaults():
    import config
    assert config.cfg["clips_per_day"] == 6
    assert config.cfg["clip_duration"] == 30
    assert len(config.cfg["trending_urls"]) >= 1
    assert config.cfg["shorts_width"] == 1080
    assert config.cfg["shorts_height"] == 1920


def test_retry_decorator():
    from clipper_shared import retry
    call_count = [0]

    @retry(max_attempts=3, delay=0.1)
    def fails():
        call_count[0] += 1
        raise ValueError("boom")

    try:
        fails()
    except ValueError:
        pass
    assert call_count[0] == 3, f"Expected 3 calls, got {call_count[0]}"


def test_is_official():
    from clipper_shared import is_official
    info = make_info()
    assert is_official(info), "Official channel should be recognized"

    info2 = make_info({"channel_is_verified": False, "channel_follower_count": 100})
    assert not is_official(info2), "Small unverified channel should not be official"


def test_save_load_json():
    from clipper_shared import load_json, save_json
    tmp = "test_tmp_log.json"
    data = [{"file": "test.mp4", "date": "2026-06-12"}]
    try:
        save_json(tmp, data)
        loaded = load_json(tmp, [])
        assert loaded == data
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
