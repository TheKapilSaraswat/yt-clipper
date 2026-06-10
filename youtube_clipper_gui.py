import subprocess
import sys
import os
import math
import json
import re
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext

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
    channel_words = set(channel.split())
    title_words = set(title.split())
    return verified and followers > 50000 and bool(channel_words & title_words)

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
    (issues if found else passed).append(f"Title: {'red flags ' + str(found) if found else 'looks clean'}")

    desc_lower = description.lower()
    found = [pat for pat in RED_FLAG_DESC_KEYWORDS if re.search(pat, desc_lower)]
    (issues if found else passed).append(f"Description: {'disclaimers found' if found else 'no disclaimer patterns'}")

    (passed if verified else issues).append(f"Channel: {'verified' if verified else 'not verified'}")

    if followers > 100000:
        passed.append(f"Followers: {followers:,} (established)")
    elif followers > 10000:
        passed.append(f"Followers: {followers:,}")
    else:
        issues.append(f"Followers: {followers:,} (small channel)")

    (passed if "creative" in license_type.lower() else issues).append(f"License: {'Creative Commons' if 'creative' in license_type.lower() else 'standard YouTube (restrictive)'}")

    if "music" in str(categories).lower():
        (passed if official else issues).append(f"Music category: {'official channel' if official else 'likely copyrighted audio'}")

    if duration > 3600:
        issues.append(f"Duration: {duration//60}min (could be full movie/episode)")
    elif duration > 1800:
        issues.append(f"Duration: {duration//60}min (verify it's not a full show)")
    else:
        passed.append(f"Duration: {duration//60}m {duration%60}s (typical)")

    channel_words = set(channel.lower().split())
    title_words = set(title_lower.split())
    (passed if channel_words & title_words else issues).append(f"Channel in title: {'yes (original likely)' if channel_words & title_words else 'no (may be reused)'}")

    return issues, passed

def risk_level(issues_count, total):
    if total == 0:
        return "LOW"
    r = issues_count / total
    return "LOW" if r <= 0.25 else "MEDIUM" if r <= 0.5 else "HIGH"

class YouTubeClipperGUI:
    def __init__(self, root):
        self.root = root
        root.title("YouTube Clipper")
        root.geometry("640x520")
        root.resizable(False, False)

        main = ttk.Frame(root, padding=20)
        main.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main, text="YouTube Video URL:", font=("", 11)).pack(anchor=tk.W)

        self.url_entry = ttk.Entry(main, font=("", 10))
        self.url_entry.pack(fill=tk.X, pady=(5, 10))

        btn_frame = ttk.Frame(main)
        btn_frame.pack()

        self.check_btn = ttk.Button(btn_frame, text="Check Only", command=self.start_check)
        self.check_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.dl_btn = ttk.Button(btn_frame, text="Check & Download", command=self.start_process)
        self.dl_btn.pack(side=tk.LEFT)

        self.progress = ttk.Progressbar(main, mode="indeterminate")
        self.progress.pack(fill=tk.X, pady=(10, 5))

        self.status_text = scrolledtext.ScrolledText(main, height=18, font=("Consolas", 9), state=tk.DISABLED)
        self.status_text.pack(fill=tk.BOTH, expand=True)

    def log(self, msg):
        self.status_text.config(state=tk.NORMAL)
        self.status_text.insert(tk.END, msg + "\n")
        self.status_text.see(tk.END)
        self.status_text.config(state=tk.DISABLED)
        self.root.update()

    def run_check(self, url):
        self.log("-" * 50)
        self.log(f"Checking: {url}")
        try:
            info = get_video_info(url)
            title = info.get("title", "Unknown")
            channel = info.get("channel", "Unknown")
            self.log(f"Title:   {title}")
            self.log(f"Channel: {channel}")
            self.log("")

            issues, passed = check_video(info)
            for p in passed:
                self.log(f"  [OK] {p}")
            for i in issues:
                self.log(f"  [!] {i}")

            level = risk_level(len(issues), len(issues) + len(passed))
            msg = f"\nRisk Level: {level}"
            if level == "LOW":
                msg += " — likely safe to use"
            elif level == "MEDIUM":
                msg += " — proceed with caution"
            else:
                msg += " — high risk of copyright/policy issues"
            self.log(msg)
            return level == "HIGH"
        except Exception as e:
            self.log(f"Check failed: {e}")
            return True

    def check_only(self, url):
        try:
            self.run_check(url)
        finally:
            self.check_btn.config(state=tk.NORMAL)
            self.dl_btn.config(state=tk.NORMAL)
            self.progress.stop()

    def start_check(self):
        url = self.url_entry.get().strip()
        if not url:
            self.log("Please enter a YouTube URL.")
            return
        self.check_btn.config(state=tk.DISABLED)
        self.dl_btn.config(state=tk.DISABLED)
        self.progress.start()
        threading.Thread(target=self.check_only, args=(url,), daemon=True).start()

    def process(self, url):
        blocked = self.run_check(url)
        if blocked:
            self.log("Download BLOCKED due to high risk.")
            self.dl_btn.config(state=tk.NORMAL)
            self.check_btn.config(state=tk.NORMAL)
            self.progress.stop()
            return

        try:
            self.log("\nDownloading video...")
            os.makedirs("original", exist_ok=True)
            output_template = os.path.join("original", "%(title)s.%(ext)s")
            subprocess.run(
                ["yt-dlp", "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                 "-o", output_template, url],
                check=True, capture_output=True, text=True
            )
            self.log("Download complete.")

            files = [f for f in os.listdir("original") if f.endswith(".mp4")]
            if not files:
                self.log("ERROR: No MP4 file downloaded.")
                return

            latest = max((os.path.join("original", f) for f in files), key=os.path.getmtime)
            self.log(f"Video: {os.path.basename(latest)}")

            cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", latest]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            duration = float(result.stdout.strip())
            num_clips = math.ceil(duration / 30)
            self.log(f"Duration: {duration:.0f}s -> {num_clips} clip(s) of 30s")

            os.makedirs("clips", exist_ok=True)
            base = os.path.splitext(os.path.basename(latest))[0]

            for i in range(num_clips):
                start = i * 30
                clip_name = f"{base}_part{i+1:03d}.mp4"
                clip_path = os.path.join("clips", clip_name)
                self.log(f"[{i+1}/{num_clips}] Creating {clip_name}")
                subprocess.run(
                    ["ffmpeg", "-y", "-i", latest, "-ss", str(start), "-t", "30", "-c", "copy", clip_path],
                    check=True, capture_output=True, text=True
                )

            self.log(f"\nDone! {num_clips} clip(s) saved in 'clips/'")
        except subprocess.CalledProcessError as e:
            self.log(f"ERROR: {e.stderr or e}")
        except Exception as e:
            self.log(f"ERROR: {e}")
        finally:
            self.dl_btn.config(state=tk.NORMAL)
            self.check_btn.config(state=tk.NORMAL)
            self.progress.stop()

    def start_process(self):
        url = self.url_entry.get().strip()
        if not url:
            self.log("Please enter a YouTube URL.")
            return
        self.dl_btn.config(state=tk.DISABLED)
        self.check_btn.config(state=tk.DISABLED)
        self.progress.start()
        threading.Thread(target=self.process, args=(url,), daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = YouTubeClipperGUI(root)
    root.mainloop()
