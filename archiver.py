import os
import pickle
import subprocess
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request

SOURCE_CHANNEL_ID = "UCXy9KvLa5VyndfpX7zsgeAQ"  # chris-pg1
TRACKER_FILE = "archived_videos.txt"

# Load credentials
with open("token.pickle", "rb") as token_file:
    creds = pickle.load(token_file)
if creds and creds.expired and creds.refresh_token:
    creds.refresh(Request())

youtube = build("youtube", "v3", credentials=creds)

# Load tracker
uploaded = set()
if os.path.exists(TRACKER_FILE):
    with open(TRACKER_FILE, "r") as f:
        uploaded = set(line.strip() for line in f)

# Fetch latest videos from source channel
response = youtube.search().list(
    part="id",
    channelId=SOURCE_CHANNEL_ID,
    maxResults=10,
    order="date",
    type="video"
).execute()

new_video_ids = [
    item["id"]["videoId"]
    for item in response["items"]
    if item["id"]["videoId"] not in uploaded
]

for video_id in new_video_ids:
    print(f"⬇️ Downloading: {video_id}")
    filename = f"{video_id}.mp4"
    subprocess.run([
        "yt-dlp",
        f"https://www.youtube.com/watch?v={video_id}",
        "-o", filename,
        "-f", "bestvideo+bestaudio"
    ], check=True)

    print(f"📤 Uploading: {filename}")
    request_body = {
        "snippet": {
            "title": f"Mirror of {video_id}",
            "description": f"Archived from source channel {SOURCE_CHANNEL_ID}",
            "tags": ["mirror", "archive"],
            "categoryId": "22"
        },
        "status": {
            "privacyStatus": "private"
        }
    }

    media = MediaFileUpload(filename, chunksize=-1, resumable=True, mimetype="video/*")
    upload_request = youtube.videos().insert(
        part="snippet,status",
        body=request_body,
        media_body=media
    )
    response = upload_request.execute()
    print(f"✅ Uploaded: https://www.youtube.com/watch?v={response['id']}")

    with open(TRACKER_FILE, "a") as f:
        f.write(video_id + "\n")

    os.remove(filename)
