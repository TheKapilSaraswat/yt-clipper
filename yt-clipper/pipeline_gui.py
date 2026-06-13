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
    find_suitable_videos,
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

    def set_dashboard(self, info, video_url="", checks=None):
        self.current_video_info = info
        title = info.get("title", "\u2013")
        channel = info.get("channel", "\u2013")
        views = info.get("view_count", 0)

        level, issues = check_video(info)
        risk_colors = {"LOW": "#00e676", "MEDIUM": "#ffab00", "HIGH": "#ff1744"}
        risk_color = risk_colors.get(level, "#aaa")
        issue_text = " | ".join(issues) if issues else "No issues detected"
        issue_color = "#ff1744" if issues else "#00e676"
        url_text = f"URL: {video_url}" if video_url else "URL: \u2013"

        caption = generate_caption(1, CLIPS_PER_DAY, info)

        if checks:
            passed = sum(1 for c in checks if c["passed"])
            total = len(checks)
            detail_lines = "\n".join(
                f"{'\u2713' if c['passed'] else '\u2717'} {c['test']}: {c['detail']}"
                for c in checks[:10]
            )
            if total > 10:
                detail_lines += f"\n... and {total - 10} more"
            display_text = f"Risk: {level} | Checks: {passed}/{total} passed\n{detail_lines}"
        else:
            display_text = issue_text

        self.root.after(0, lambda: (
            self.dash_url.config(text=url_text),
            self.dash_title.config(text=title[:80]),
            self.dash_views.config(text=f"Views: {views:,}"),
            self.dash_risk.config(text=f"Risk: {level}", fg=risk_color),
            self.dash_channel.config(text=f"Channel: {channel}"),
            self.dash_issues.config(text=display_text, fg=issue_color),
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
            need = CLIPS_PER_DAY - len(uploaded_today)
            self.log(f"Need {need} more clips today")

            if need <= 0:
                self.log("Already done for today!", "#00e5ff")
                return

            # Reuse any existing clips
            clips = []
            if os.path.exists("clips"):
                already = set(u["file"] for u in used)
                for f in sorted(os.listdir("clips")):
                    fp = os.path.join("clips", f)
                    if f.endswith(".mp4") and fp not in already:
                        clips.append(fp)
            clips = clips[:need]
            self.log(f"Existing clips to upload: {len(clips)}")
            remaining = need - len(clips)

            # Find suitable trending videos upfront (one batch)
            videos = []
            if remaining > 0:
                self.log(f"\nScanning trending for {remaining} clean videos...")
                videos = find_suitable_videos(remaining, used_source_urls, self.log)
                if not videos:
                    self.log("No suitable video found!", "#ff1744")

            if not clips and not videos:
                self.log("Nothing to process.", "#ff1744")
                return

            youtube = authenticate_youtube()
            clip_index = len(clips)

            for video in videos:
                chosen_url = video["url"]
                chosen_info = video["info"]
                video_id = chosen_url.split("v=")[-1]

                # Show detailed check results on dashboard
                self.set_dashboard(chosen_info, chosen_url, video.get("checks"))
                used_source_urls.add(chosen_url)

                clip_index += 1
                self.log(f"\n[{clip_index}/{need}] Downloading: {chosen_info.get('title', '')[:60]}...")
                vp = download_video(chosen_url)
                ext = os.path.splitext(vp)[1]
                renamed = os.path.join(os.path.dirname(vp), f"{video_id}{ext}")
                if os.path.exists(vp) and not os.path.exists(renamed):
                    os.rename(vp, renamed)
                    vp = renamed

                self.log("Clipping into short segment...")
                nc = clip_video(vp)  # limit=1 by default → 1 clip
                if not nc:
                    self.log("  No clips created, skipping", "#ff1744")
                    continue
                cp = nc[0]
                self.log("Created 30s clip", "#00e676")

                clips.append(cp)

                # SEO caption
                cap = generate_caption(clip_index, need, chosen_info)
                desc = f"{cap}\n\n#shorts #trending #viral"
                tags = ["shorts", "trending", "viral"] + (chosen_info.get("tags", []) or [])[:5]
                self.log(f"Caption: {cap[:60]}...")

                # Upload immediately
                if youtube:
                    try:
                        self.log(f"Uploading to YouTube...")
                        upload_short(youtube, cp, cap, desc, tags)
                        used.append({"date": today, "file": cp, "title": cap, "source_url": chosen_url})
                        save_json(DAILY_LOG, used)
                        self.log(f"\u2713 Uploaded! https://youtube.com/watch?v={video_id}", "#00e676")
                    except Exception as e:
                        self.log(f"  Upload failed: {e}", "#ff1744")
                else:
                    self.log("Clip saved locally (no YouTube auth)", "#ffab00")

            self.log(f"\nDone! Processed {len(clips)} clips today.", "#00e5ff")

            # Cleanup
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
