import os
import sys
import subprocess
import json
import re
import math
import pickle
import threading
from datetime import datetime

from kivy.config import Config
Config.set('kivy', 'log_level', 'warning')
Config.set('graphics', 'width', '420')
Config.set('graphics', 'height', '780')

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.clock import Clock
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp

# ─── LOGIC ──────────────────────────────────────────────────────────────

TRENDING_SEARCHES = [
    "ytsearch15:today's trending videos",
    "ytsearch15:viral videos today",
]

RED_FLAG_TITLE_KW = ["lyrics","cover","remix","mashup","full movie","full episode","movie clip","scene from","official video","music video","audio"]
RED_FLAG_DESC_KW = [r"no copyright",r"copyright (disclaimer|notice|free)",r"fair use",r"all rights belong",r"i do not own",r"no infringement",r"for entertainment purposes only"]

DAILY_LOG = "upload_log.json"
SECRET_FILE = "client_secret.json"
TOKEN_FILE = "yt_token.pickle"

def load_json(p, d):
    return json.load(open(p)) if os.path.exists(p) else d
def save_json(p, data):
    with open(p, 'w') as f: json.dump(data, f, indent=2)

def vi(url):
    r = subprocess.run(["yt-dlp","--dump-json","--no-download","--skip-download",url], capture_output=True, text=True, check=True)
    return json.loads(r.stdout)

def official(i):
    t=i.get("title","").lower(); c=i.get("channel","").lower(); f=i.get("channel_follower_count") or 0; v=i.get("channel_is_verified",False)
    return v and f>50000 and bool(set(c.split())&set(t.split()))

def check(i):
    issues=[]
    t,d,ch,fol,ver,cat,dur,off=i.get("title",""),i.get("description","") or "",i.get("channel",""),i.get("channel_follower_count") or 0,i.get("channel_is_verified",False),i.get("categories",[]) or [],i.get("duration",0),official(i)
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
    return level,issues

def trending():
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

def dl(url):
    os.makedirs("original",exist_ok=True)
    tpl=os.path.join("original","%(title)s.%(ext)s")
    subprocess.run(["yt-dlp","-f","bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best","-o",tpl,url],check=True,capture_output=True,text=True)
    files=[f for f in os.listdir("original") if f.endswith(".mp4")]
    return max((os.path.join("original",f) for f in files), key=os.path.getmtime)

def dur(path):
    r=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",path],capture_output=True,text=True,check=True)
    return float(r.stdout.strip())

def clip(path,seg=30):
    os.makedirs("clips",exist_ok=True)
    d=dur(path); n=math.ceil(d/seg); base=os.path.splitext(os.path.basename(path))[0]; paths=[]
    for i in range(n):
        name=f"{base}_part{i+1:03d}.mp4"; p=os.path.join("clips",name)
        subprocess.run(["ffmpeg","-y","-i",path,"-ss",str(i*seg),"-t",str(seg),"-c","copy",p],check=True,capture_output=True,text=True)
        paths.append(p)
    return paths

def gen_cap(idx,total,info):
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

def auth():
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    if not os.path.exists(SECRET_FILE): return None
    creds=None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE,"rb") as f: creds=pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token: creds.refresh(Request())
        else:
            flow=InstalledAppFlow.from_client_secrets_file(SECRET_FILE,["https://www.googleapis.com/auth/youtube.upload"])
            creds=flow.run_localServer(port=0)
        with open(TOKEN_FILE,"wb") as f: pickle.dump(creds,f)
    return build("youtube","v3",credentials=creds)

def upload(youtube,filepath,title,desc,tags):
    from googleapiclient.http import MediaFileUpload
    body={"snippet":{"title":title[:100],"description":desc[:5000],"tags":tags[:500],"categoryId":"22"},"status":{"privacyStatus":"public","selfDeclaredMadeForKids":False}}
    media=MediaFileUpload(filepath,chunksize=-1,resumable=True)
    request=youtube.videos().insert(part="snippet,status",body=body,media_body=media)
    return request.execute()["id"]

# ─── UI ─────────────────────────────────────────────────────────────────

class PipelineThread(threading.Thread):
    def __init__(self, app):
        super().__init__(daemon=True)
        self.app = app
    def run(self):
        self.app.run_pipeline()

class YTApp(App):
    def build(self):
        self.logs = []
        self.running = False
        root = BoxLayout(orientation='vertical', padding=20, spacing=15)
        with root.canvas.before:
            Color(0.06, 0.06, 0.06, 1)
            self.bg = RoundedRectangle(size=root.size, pos=root.pos)
        root.bind(size=lambda w,s: setattr(self.bg, 'size', s), pos=lambda w,p: setattr(self.bg, 'pos', p))

        title = Label(text="[b]YouTube Clipper[/b]", markup=True, font_size=24, color=(1,0,0.27,1), size_hint=(1,None), height=dp(50))
        root.add_widget(title)

        self.count_label = Label(text="Today: 0 / 6", font_size=16, color=(0.5,0.5,0.5,1), size_hint=(1,None), height=dp(30))
        root.add_widget(self.count_label)

        self.btn = Button(
            text="▶ START", font_size=28, bold=True,
            size_hint=(None,None), size=(dp(180),dp(180)),
            pos_hint={'center_x': 0.5},
            background_normal='',
            background_color=(1,0,0.27,1),
            color=(1,1,1,1)
        )
        self.btn.bind(on_press=self.start_pipeline)
        with self.btn.canvas.before:
            Color(1,0,0.27,0.15)
            RoundedRectangle(pos=self.btn.pos, size=self.btn.size, radius=[dp(90)])
        self.btn.bind(pos=lambda w,p: self.update_btn_bg())
        root.add_widget(self.btn)

        scroll = ScrollView(size_hint=(1,1))
        self.log_grid = GridLayout(cols=1, size_hint_y=None, spacing=2)
        self.log_grid.bind(minimum_height=self.log_grid.setter('height'))
        scroll.add_widget(self.log_grid)
        root.add_widget(scroll)

        Clock.schedule_interval(self.update_ui, 1)
        return root

    def update_btn_bg(self):
        pass

    def add_log_ui(self, msg, typ='info'):
        color = (0.7,0.7,0.7,1) if typ=='info' else (0,0.9,0.46,1) if typ=='ok' else (1,0.53,0,1) if typ=='warn' else (1,0.09,0.27,1)
        lbl = Label(text=msg, font_size=12, color=color, size_hint_y=None, height=dp(22), text_size=(dp(380),None), halign='left')
        lbl.bind(texture_size=lambda l,v: setattr(l, 'height', max(dp(22), v[1])))
        self.log_grid.add_widget(lbl)

    def update_ui(self, dt):
        used = load_json(DAILY_LOG, [])
        today = datetime.now().strftime("%Y-%m-%d")
        count = len([u for u in used if u["date"] == today])
        self.count_label.text = f"Today: {count} / 6"
        if not self.running:
            self.btn.text = "▶ START"
            self.btn.disabled = False

    def start_pipeline(self, inst):
        if self.running: return
        self.running = True
        self.btn.text = "⏳ WORKING"
        self.btn.disabled = True
        self.log_grid.clear_widgets()
        PipelineThread(self).start()

    def run_pipeline(self):
        def log(msg, typ='info'):
            Clock.schedule_once(lambda dt: self.add_log_ui(msg, typ))

        used = load_json(DAILY_LOG, [])
        today = datetime.now().strftime("%Y-%m-%d")
        uploaded_today = [u for u in used if u["date"] == today]
        already = set(u["file"] for u in used)
        need = 6 - len(uploaded_today)

        log(f"Need {need} more clips today")
        if need <= 0:
            log("Already done for today!", 'ok')
            self.running = False; return

        available = []
        if os.path.exists("clips"):
            for f in sorted(os.listdir("clips")):
                fp = os.path.join("clips", f)
                if f.endswith(".mp4") and fp not in already:
                    available.append(fp)
        clips = available[:need]
        remaining = need - len(clips)

        while remaining > 0:
            log("Scanning trending videos...")
            candidates = trending()
            found = False
            for c in candidates:
                url = f"https://youtube.com/watch?v={c.get('id','')}"
                try:
                    info = vi(url)
                    level, issues = check(info)
                    cc = math.ceil(info.get("duration",0)/30)
                    log(f"{c['title'][:50]} -> {level} ({cc} clips)")
                    if level == "HIGH":
                        log("  Skipped", 'warn'); continue
                    if cc < 1: continue
                    log(f"Selected: {info['title'][:60]}", 'ok')
                    found = True; break
                except: continue
            if not found:
                log("No suitable video found!", 'err'); break

            log("Downloading...")
            vp = dl(url)
            log("Clipping into 30s segments...")
            nc = clip(vp)
            log(f"Created {len(nc)} clips", 'ok')
            for cp in nc:
                if cp not in already and cp not in clips:
                    clips.append(cp); already.add(cp); remaining -= 1
                    if remaining <= 0: break

        if not clips:
            log("No clips to upload.", 'err'); self.running = False; return

        log("Connecting to YouTube...")
        yt = auth()
        if not yt:
            log("ERROR: client_secret.json missing!", 'err'); self.running = False; return

        for idx, cp in enumerate(clips[:6]):
            info = {"title": os.path.basename(cp).replace("_part"," - Part "), "tags":[], "description":""}
            cap = gen_cap(idx+1, len(clips), info)
            desc = f"{cap}\n\n#shorts #trending #viral"
            tags = ["shorts","trending","viral"]
            try:
                upload(yt, cp, cap, desc, tags)
                used.append({"date":today,"file":cp,"title":cap})
                save_json(DAILY_LOG, used)
                log(f"Uploaded: {cap[:50]}...", 'ok')
            except Exception as e:
                log(f"Upload failed: {e}", 'err')

        log("Done! 6 shorts uploaded today.", 'done')
        self.running = False

if __name__ == "__main__":
    YTApp().run()
