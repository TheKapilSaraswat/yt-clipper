import os
import json
import pickle
import sys
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_FILE = "yt_token.pickle"
SECRET_FILE = "client_secret.json"

def authenticate():
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(SECRET_FILE):
                print(f"ERROR: {SECRET_FILE} not found.")
                print("Get it from https://console.cloud.google.com -> APIs & Services -> Credentials -> OAuth 2.0 Client IDs")
                print("Download JSON and save as client_secret.json")
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)
    return build("youtube", "v3", credentials=creds)

def upload_clip(youtube, filepath, title, description="", tags=None, category_id="22"):
    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": (tags or [])[:500],
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
        },
    }
    media = MediaFileUpload(filepath, chunksize=-1, resumable=True)
    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )
    print(f"  Uploading: {title}")
    response = request.execute()
    print(f"  Uploaded: https://youtube.com/watch?v={response['id']}")
    return response["id"]

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python youtube_uploader.py <clip.mp4> [title]")
        sys.exit(1)

    filepath = sys.argv[1]
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        sys.exit(1)

    title = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(os.path.basename(filepath))[0]
    youtube = authenticate()
    upload_clip(youtube, filepath, title)
