import sys
import os
import threading
import queue
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')
import tkinter as tk
from tkinter import ttk, scrolledtext

import config
from clipper_shared import (
    get_video_info,
    check_video,
    generate_caption,
    get_trending,
    find_best_trending,
    download_video,
    clip_video,
    authenticate_youtube,
    upload_short,
    load_json,
    save_json,
)

DAILY_LOG = config.cfg["daily_log"]
CLIPS_PER_DAY = config.cfg["clips_per_day"]
CLIP_DURATION = config.cfg["clip_duration"]


class PipelineGUI:
    def __init__(self, root):
        self.root = root
        root.title("YouTube Daily Clipper")
        root.geometry("780x680")
        root.resizable(False, False)
        root.configure(bg='#0f0f0f')

        main = tk.Frame(root, bg='#0f0f0f', padx=16, pady=14)
        main.pack(fill=tk.BOTH, expand=True)

        header = tk.Frame(main, bg='#0f0f0f')
        header.pack(fill=tk.X)

        tk.Label(header, text="YouTube Clipper", font=("Segoe UI", 20, "bold"),
                 fg="#ff0044", bg='#0f0f0f').pack(side=tk.LEFT)

        self.count_label = tk.Label(header, text="Today: 0 / 6", font=("Segoe UI", 13),
                                    fg="#aaa", bg='#0f0f0f')
        self.count_label.pack(side=tk.RIGHT, pady=8)

        tk.Label(main, text="Find trending → check safety → clip 6 shorts → upload",
                 font=("Segoe UI", 9), fg="#666", bg='#0f0f0f', anchor='w').pack(fill=tk.X, pady=(0, 8))

        card = tk.Frame(main, bg='#1a1a1a', bd=1, relief='solid', highlightbackground='#333', highlightthickness=1)
        card.pack(fill=tk.X, pady=(0, 8))

        self.dash_url = tk.Label(card, text="\u2013", font=("Segoe UI", 9), fg="#888", bg='#1a1a1a', anchor='w', wraplength=720)
        self.dash_url.pack(fill=tk.X, padx=10, pady=(8, 0))

        self.dash_title = tk.Label(card, text="No video selected", font=("Segoe UI", 10, "bold"), fg="#ccc", bg='#1a1a1a', anchor='w', wraplength=720)
        self.dash_title.pack(fill=tk.X, padx=10, pady=(2, 0))

        stats_row = tk.Frame(card, bg='#1a1a1a')
        stats_row.pack(fill=tk.X, padx=10, pady=(4, 2))

        self.dash_views = tk.Label(stats_row, text="Views: \u2013", font=("Segoe UI", 9), fg="#aaa", bg='#1a1a1a')
        self.dash_views.pack(side=tk.LEFT, padx=(0, 16))

        self.dash_risk = tk.Label(stats_row, text="Risk: \u2013", font=("Segoe UI", 9, "bold"), fg="#aaa", bg='#1a1a1a')
        self.dash_risk.pack(side=tk.LEFT, padx=(0, 16))

        self.dash_channel = tk.Label(stats_row, text="Channel: \u2013", font=("Segoe UI", 9), fg="#aaa", bg='#1a1a1a')
        self.dash_channel.pack(side=tk.LEFT)

        self.dash_issues = tk.Label(card, text="", font=("Segoe UI", 8), fg="#ffab00", bg='#1a1a1a', anchor='w', wraplength=720)
        self.dash_issues.pack(fill=tk.X, padx=10, pady=(0, 2))

        self.dash_caption_label = tk.Label(card, text="SEO Caption:", font=("Segoe UI", 8, "bold"), fg="#666", bg='#1a1a1a', anchor='w')
        self.dash_caption_label.pack(fill=tk.X, padx=10, pady=(0, 0))

        self.dash_caption = tk.Label(card, text="\u2013", font=("Consolas", 8), fg="#00e676", bg='#1a1a1a', anchor='w', wraplength=720, justify=tk.LEFT)
        self.dash_caption.pack(fill=tk.X, padx=10, pady=(0, 8))

        self.btn = tk.Button(main, text="\u25b6 START", font=("Segoe UI", 16, "bold"),
                             fg="white", bg="#ff0044", activebackground="#cc0033",
                             activeforeground="white", bd=0, cursor="hand2",
                             width=10, height=1, command=self.start)
        self.btn.pack(pady=(0, 8))

        self.status = scrolledtext.ScrolledText(main, height=14, font=("Consolas", 9),
                                                bg="#1a1a1a", fg="#ccc",
                                                insertbackground="#ccc", state=tk.DISABLED)
        self.status.pack(fill=tk.BOTH, expand=True)

        self.log_queue = queue.Queue()
        self.process_log_queue()

        self.update_count()
        self.running = False
        self.current_video_info = None
        threading.Thread(target=self.preview_trending, daemon=True).start()

    def process_log_queue(self):
        try:
            while True:
                msg, color = self.log_queue.get_nowait()
                self.status.config(state=tk.NORMAL)
                self.status.insert(tk.END, msg + "\n")
                self.status.see(tk.END)
                self.status.config(state=tk.DISABLED)
        except queue.Empty:
            pass
        self.root.after(100, self.process_log_queue)

    def log(self, msg, color="#aaa"):
        self.log_queue.put((msg, color))

    def update_count(self):
        used = load_json(DAILY_LOG, [])
        today = datetime.now().strftime("%Y-%m-%d")
        count = len([u for u in used if u["date"] == today])
        self.count_label.config(text=f"Today: {count} / {CLIPS_PER_DAY}")
        self.root.after(5000, self.update_count)

    def set_dashboard(self, info, video_url=""):
        self.current_video_info = info
        title = info.get("title", "\u2013")
        channel = info.get("channel", "\u2013")
        views = info.get("view_count", 0)
        verified = info.get("channel_is_verified", False)
        followers = info.get("channel_follower_count") or 0

        level, issues = check_video(info)
        risk_colors = {"LOW": "#00e676", "MEDIUM": "#ffab00", "HIGH": "#ff1744"}
        risk_color = risk_colors.get(level, "#aaa")
        issue_text = " | ".join(issues) if issues else "No issues detected"
        issue_color = "#ff1744" if issues else "#00e676"
        url_text = f"URL: {video_url}" if video_url else "URL: \u2013"
        caption = generate_caption(1, CLIPS_PER_DAY, info)

        self.root.after(0, lambda: (
            self.dash_url.config(text=url_text),
            self.dash_title.config(text=title[:80]),
            self.dash_views.config(text=f"Views: {views:,}"),
            self.dash_risk.config(text=f"Risk: {level}", fg=risk_color),
            self.dash_channel.config(text=f"Channel: {channel}"),
            self.dash_issues.config(text=issue_text, fg=issue_color),
            self.dash_caption.config(text=caption[:150]),
        ))

    def preview_trending(self):
        try:
            candidates = get_trending()
            for c in candidates:
                vid_url = f"https://youtube.com/watch?v={c.get('id','')}"
                try:
                    info = get_video_info(vid_url)
                    level, issues = check_video(info)
                    if level == "HIGH":
                        continue
                    self.set_dashboard(info, vid_url)
                    self.log(f"Preview: {c['title'][:60]} \u2014 {level} risk", "#888")
                    break
                except Exception:
                    continue
        except Exception:
            pass

    def run_pipeline(self):
        try:
            used = load_json(DAILY_LOG, [])
            today = datetime.now().strftime("%Y-%m-%d")
            used_source_urls = set(u.get("source_url", "") for u in used if u.get("source_url"))
            uploaded_today = [u for u in used if u["date"] == today]
            already = set(u["file"] for u in used)
            need = CLIPS_PER_DAY - len(uploaded_today)
            self.log(f"Need {need} more clips today")

            if need <= 0:
                self.log("Already done for today!", "#00e5ff")
                return

            available = []
            if os.path.exists("clips"):
                for f in sorted(os.listdir("clips")):
                    fp = os.path.join("clips", f)
                    if f.endswith(".mp4") and fp not in already:
                        available.append(fp)
            self.log(f"Unused clips found: {len(available)}")
            clips = available[:need]
            remaining = need - len(clips)
            source_videos_info = {}
            source_url_by_video_id = {}

            while remaining > 0:
                self.log("Scanning trending videos...")
                chosen_url, chosen_info = find_best_trending(used_source_urls, self.log)
                if not chosen_url:
                    self.log("No suitable video found!", "#ff1744")
                    break

                self.set_dashboard(chosen_info, chosen_url)
                used_source_urls.add(chosen_url)
                video_id = chosen_url.split("v=")[-1]

                self.log("Downloading...")
                vp = download_video(chosen_url)
                ext = os.path.splitext(vp)[1]
                renamed = os.path.join(os.path.dirname(vp), f"{video_id}{ext}")
                if os.path.exists(vp) and not os.path.exists(renamed):
                    os.rename(vp, renamed)
                    vp = renamed

                self.log("Clipping into 30s segments...")
                nc = clip_video(vp)
                self.log(f"Created {len(nc)} clips", "#00e676")

                source_videos_info[chosen_url] = chosen_info
                source_url_by_video_id[video_id] = chosen_url

                cp = nc[0]
                if cp not in already and cp not in clips:
                    clips.append(cp)
                    already.add(cp)
                    remaining -= 1

            if not clips:
                self.log("No clips to process.", "#ff1744")
                return

            self.log(f"\nClips ready: {len(clips[:CLIPS_PER_DAY])}")
            youtube = authenticate_youtube()
            if not youtube:
                self.log(f"\nDone! {len(clips)} clips saved in 'clips/' folder.", "#00e5ff")
                if os.path.exists("original"):
                    for f in os.listdir("original"):
                        fp = os.path.join("original", f)
                        if os.path.isfile(fp):
                            os.remove(fp)
                return

            for idx, cp in enumerate(clips[:CLIPS_PER_DAY]):
                clip_name = os.path.basename(cp)
                clip_video_id = clip_name.split("_")[0]
                src_url = source_url_by_video_id.get(clip_video_id)
                info = source_videos_info.get(src_url) if src_url else None
                if not info:
                    info = {"title": clip_name.replace("_part", " - Part "), "tags": [], "description": "", "channel": "Trending", "view_count": 0, "duration": 30}
                cap = generate_caption(idx + 1, len(clips), info)
                desc = f"{cap}\n\n#shorts #trending #viral"
                tags = ["shorts", "trending", "viral"] + (info.get("tags", []) or [])[:5]
                self.log(f"[{idx+1}/{len(clips[:CLIPS_PER_DAY])}] {cap[:60]}...")
                try:
                    upload_short(youtube, cp, cap, desc, tags)
                    used.append({"date": today, "file": cp, "title": cap, "source_url": src_url or ""})
                    save_json(DAILY_LOG, used)
                except Exception as e:
                    self.log(f"  Failed: {e}", "#ff1744")

            self.log("\nDone! Shorts uploaded today.", "#00e5ff")

            for folder in ("clips", "original"):
                if os.path.exists(folder):
                    for f in os.listdir(folder):
                        fp = os.path.join(folder, f)
                        if os.path.isfile(fp):
                            os.remove(fp)
        except Exception as e:
            self.log(f"Error: {e}", "#ff1744")
        finally:
            self.running = False
            self.root.after(0, lambda: self.btn.config(text="\u25b6 START", state=tk.NORMAL))

    def start(self):
        if self.running:
            return
        self.running = True
        self.btn.config(text="\u23f3 WORKING", state=tk.DISABLED)
        self.status.config(state=tk.NORMAL)
        self.status.delete("1.0", tk.END)
        self.status.config(state=tk.DISABLED)
        threading.Thread(target=self.run_pipeline, daemon=True).start()


if __name__ == "__main__":
    root = tk.Tk()
    PipelineGUI(root)
    root.mainloop()
