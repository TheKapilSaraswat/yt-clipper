import subprocess
import json
import os
import sys
import math
import re
import pickle
import threading
from datetime import datetime
import tkinter as tk
from tkinter import ttk, scrolledtext

TRENDING_SEARCHES = [
    "ytsearch15:today's trending videos",
    "ytsearch15:viral videos today",
    "ytsearch15:trending on youtube today",
]
RED_FLAG_TITLE_KW = ["lyrics","cover","remix","mashup","full movie","full episode","movie clip","scene from","official video","music video","audio"]
RED_FLAG_DESC_KW = [r"no copyright",r"copyright (disclaimer|notice|free)",r"fair use",r"all rights belong",r"i do not own",r"no infringement",r"for entertainment purposes only"]
CLIPS_PER_DAY = 6
CLIP_DURATION = 30
DAILY_LOG = "upload_log.json"
SECRET_FILE = "client_secret.json"
TOKEN_FILE = "yt_token.pickle"

def load_json(p, d):
    return json.load(open(p)) if os.path.exists(p) else d
def save_json(p, data):
    with open(p, 'w') as f: json.dump(data, f, indent=2)

class PipelineGUI:
    def __init__(self, root):
        self.root = root
        root.title("YouTube Daily Clipper")
        root.geometry("700x560")
        root.resizable(False, False)
        root.configure(bg='#0f0f0f')

        main = tk.Frame(root, bg='#0f0f0f', padx=20, pady=20)
        main.pack(fill=tk.BOTH, expand=True)

        tk.Label(main, text="YouTube Clipper", font=("Segoe UI", 22, "bold"),
                 fg="#ff0044", bg='#0f0f0f').pack()

        tk.Label(main, text="Find trending → check safety → clip 6 shorts → upload",
                 font=("Segoe UI", 10), fg="#888", bg='#0f0f0f').pack(pady=(0, 15))

        self.count_label = tk.Label(main, text="Today: 0 / 6", font=("Segoe UI", 14),
                                    fg="#aaa", bg='#0f0f0f')
        self.count_label.pack()

        self.btn = tk.Button(main, text="▶ START", font=("Segoe UI", 18, "bold"),
                             fg="white", bg="#ff0044", activebackground="#cc0033",
                             activeforeground="white", bd=0, cursor="hand2",
                             width=12, height=2, command=self.start)
        self.btn.pack(pady=15)

        self.status = scrolledtext.ScrolledText(main, height=20, font=("Consolas", 9),
                                                bg="#1a1a1a", fg="#ccc",
                                                insertbackground="#ccc", state=tk.DISABLED)
        self.status.pack(fill=tk.BOTH, expand=True)

        self.update_count()
        self.running = False

    def log(self, msg, color="#aaa"):
        self.status.config(state=tk.NORMAL)
        self.status.insert(tk.END, msg + "\n")
        self.status.see(tk.END)
        self.status.config(state=tk.DISABLED)
        self.root.update()

    def update_count(self):
        used = load_json(DAILY_LOG, [])
        today = datetime.now().strftime("%Y-%m-%d")
        count = len([u for u in used if u["date"] == today])
        self.count_label.config(text=f"Today: {count} / 6")
        self.root.after(5000, self.update_count)

    def get_video_info(self, url):
        r = subprocess.run(["yt-dlp","--dump-json","--no-download","--skip-download",url], capture_output=True, text=True, check=True)
        return json.loads(r.stdout)

    def is_official(self, info):
        t=info.get("title","").lower(); c=info.get("channel","").lower(); f=info.get("channel_follower_count") or 0; v=info.get("channel_is_verified",False)
        return v and f>50000 and bool(set(c.split())&set(t.split()))

    def check_video(self, info):
        issues=[]
        t,d,ch,fol,ver,cat,dur,off=info.get("title",""),info.get("description","") or "",info.get("channel",""),info.get("channel_follower_count") or 0,info.get("channel_is_verified",False),info.get("categories",[]) or [],info.get("duration",0),self.is_official(info)
        tl=t.lower()
        rfk=[kw for kw in RED_FLAG_TITLE_KW if kw not in("official video","music video","audio")] if off else RED_FLAG_TITLE_KW
        fk=[kw for kw in rfk if kw in tl]
        if fk: issues.append(f"Title: {fk}")
        fd=[p for p in RED_FLAG_DESC_KW if re.search(p,d.lower())]
        if fd: issues.append("Has disclaimer patterns")
        if not ver: issues.append("Not verified")
        if fol<10000: issues.append(f"Only {fol:,} followers")
        if "music" in str(cat).lower() and not off: issues.append("Music from non-official")
        if dur>3600: issues.append("Very long")
        if not(set(ch.lower().split())&set(tl.split())): issues.append("Channel not in title")
        level="LOW"
        if len(issues)>=4: level="HIGH"
        elif len(issues)>=2: level="MEDIUM"
        return level, issues

    def get_trending(self):
        seen=set(); videos=[]
        for q in TRENDING_SEARCHES:
            try:
                r=subprocess.run(["yt-dlp","--flat-playlist","--dump-json","--no-download",q],capture_output=True,text=True,check=True)
                for line in r.stdout.strip().split("\n"):
                    if line:
                        try:
                            it=json.loads(line); vid=it.get("id","")
                            if vid not in seen: seen.add(vid); videos.append(it)
                        except: continue
            except: continue
        videos.sort(key=lambda v: v.get("view_count",0) or 0, reverse=True)
        return videos

    def download_video(self, url):
        os.makedirs("original",exist_ok=True)
        tpl=os.path.join("original","%(title)s.%(ext)s")
        subprocess.run(["yt-dlp","-f","bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best","-o",tpl,url],check=True,capture_output=True,text=True)
        files=[f for f in os.listdir("original") if f.endswith(".mp4")]
        return max((os.path.join("original",f) for f in files), key=os.path.getmtime)

    def get_duration(self, path):
        r=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",path],capture_output=True,text=True,check=True)
        return float(r.stdout.strip())

    def clip_video(self, path, seg=CLIP_DURATION):
        os.makedirs("clips",exist_ok=True)
        d=self.get_duration(path); n=math.ceil(d/seg); base=os.path.splitext(os.path.basename(path))[0]; paths=[]
        for i in range(n):
            name=f"{base}_part{i+1:03d}.mp4"; p=os.path.join("clips",name)
            subprocess.run(["ffmpeg","-y","-i",path,"-ss",str(i*seg),"-t",str(seg),"-c","copy",p],check=True,capture_output=True,text=True)
            paths.append(p)
        return paths

    def gen_caption(self, idx, total, info):
        title=info.get("title",""); tags=info.get("tags",[]) or []; desc=info.get("description","") or ""
        words=re.sub(r"[^a-z0-9\s]","",(title+" "+desc+" "+" ".join(tags[:10])).lower())
        wl=[w for w in words.split() if len(w)>3]; freq={}
        for w in wl: freq[w]=freq.get(w,0)+1
        kw=[w for w,c in sorted(freq.items(),key=lambda x:-x[1]) if c>1][:5]
        ks=" ".join(kw[:3]) if kw else (title.split()[0] if title else "trending")
        ht=["#shorts","#trending","#viral"]; ht.extend(["#"+k for k in kw[:3]])
        cap=f"{ks.title()} | {title[:50]} Part {idx}/{total} {' '.join(ht)}"
        if len(cap.split())>95: cap=" ".join(cap.split()[:95])
        return cap

    def auth(self):
        try:
            from google.auth.transport.requests import Request
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
        except ImportError:
            self.log("[!] google-api-python-client not installed. Run: pip install google-api-python-client google-auth-oauthlib", "#ff1744")
            return None
        if not os.path.exists(SECRET_FILE):
            self.log("[!] client_secret.json not found. Skipping upload.", "#ffab00")
            return None
        creds=None
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE,"rb") as f: creds=pickle.load(f)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow=InstalledAppFlow.from_client_secrets_file(SECRET_FILE,["https://www.googleapis.com/auth/youtube.upload"])
                creds=flow.run_local_server(port=0)
            with open(TOKEN_FILE,"wb") as f: pickle.dump(creds,f)
        return build("youtube","v3",credentials=creds)

    def upload_short(self, youtube, filepath, title, desc, tags):
        from googleapiclient.http import MediaFileUpload
        body={"snippet":{"title":title[:100],"description":desc[:5000],"tags":tags[:500],"categoryId":"22"},"status":{"privacyStatus":"public","selfDeclaredMadeForKids":False}}
        media=MediaFileUpload(filepath,chunksize=-1,resumable=True)
        request=youtube.videos().insert(part="snippet,status",body=body,media_body=media)
        self.log(f"  Uploading...")
        response=request.execute()
        self.log(f"  Uploaded: https://youtube.com/watch?v={response['id']}", "#00e676")
        return response["id"]

    def run_pipeline(self):
        try:
            used=load_json(DAILY_LOG,[])
            today=datetime.now().strftime("%Y-%m-%d")
            uploaded_today=[u for u in used if u["date"]==today]
            already=set(u["file"] for u in used)
            need=CLIPS_PER_DAY-len(uploaded_today)
            self.log(f"Need {need} more clips today")

            if need<=0:
                self.log("Already done for today!", "#00e5ff")
                return

            available=[]
            if os.path.exists("clips"):
                for f in sorted(os.listdir("clips")):
                    fp=os.path.join("clips",f)
                    if f.endswith(".mp4") and fp not in already: available.append(fp)
            self.log(f"Unused clips found: {len(available)}")
            clips=available[:need]
            remaining=need-len(clips)

            while remaining>0:
                self.log("Scanning trending videos...")
                candidates=self.get_trending()
                found=False
                for c in candidates:
                    vid_url=f"https://youtube.com/watch?v={c.get('id','')}"
                    try:
                        info=self.get_video_info(vid_url)
                        level,issues=self.check_video(info)
                        cc=math.ceil(info.get("duration",0)/CLIP_DURATION)
                        self.log(f"  {c['title'][:60]} -> {level} ({cc} clips)")
                        if level=="HIGH": continue
                        if cc<1: continue
                        self.log(f"  Selected!", "#00e676")
                        found=True; break
                    except: continue
                if not found:
                    self.log("No suitable video found!", "#ff1744"); break

                self.log("Downloading...")
                vp=self.download_video(vid_url)
                self.log("Clipping into 30s segments...")
                nc=self.clip_video(vp)
                self.log(f"Created {len(nc)} clips", "#00e676")
                for cp in nc:
                    if cp not in already and cp not in clips:
                        clips.append(cp); already.add(cp); remaining-=1
                        if remaining<=0: break

            if not clips:
                self.log("No clips to process.", "#ff1744"); return

            self.log(f"\nClips ready: {len(clips[:CLIPS_PER_DAY])}")
            youtube=self.auth()
            if not youtube:
                self.log(f"\nDone! {len(clips)} clips saved in 'clips/' folder.", "#00e5ff")
                return

            for idx, cp in enumerate(clips[:CLIPS_PER_DAY]):
                info={"title":os.path.basename(cp).replace("_part"," - Part "),"tags":[],"description":""}
                cap=self.gen_caption(idx+1,len(clips),info)
                desc=f"{cap}\n\n#shorts #trending #viral"
                tags=["shorts","trending","viral"]
                self.log(f"[{idx+1}/{len(clips[:CLIPS_PER_DAY])}] {cap[:60]}...")
                try:
                    self.upload_short(youtube,cp,cap,desc,tags)
                    used.append({"date":today,"file":cp,"title":cap})
                    save_json(DAILY_LOG,used)
                except Exception as e:
                    self.log(f"  Failed: {e}", "#ff1744")

            self.log("\nDone! 6 shorts uploaded today.", "#00e5ff")
        except Exception as e:
            self.log(f"Error: {e}", "#ff1744")
        finally:
            self.running=False
            self.btn.config(text="▶ START", state=tk.NORMAL)

    def start(self):
        if self.running: return
        self.running=True
        self.btn.config(text="⏳ WORKING", state=tk.DISABLED)
        self.status.config(state=tk.NORMAL)
        self.status.delete("1.0", tk.END)
        self.status.config(state=tk.DISABLED)
        threading.Thread(target=self.run_pipeline, daemon=True).start()

if __name__=="__main__":
    root=tk.Tk()
    PipelineGUI(root)
    root.mainloop()
