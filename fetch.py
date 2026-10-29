import os
import json
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.environ["YOUTUBE_API_KEY"]
BASE_URL = "https://www.googleapis.com/youtube/v3"
HANDLE = "@quirkychao"
RAW_DIR = Path("data/raw")


def api_get(endpoint, params):
    r = requests.get(
        f"{BASE_URL}/{endpoint}",
        params=params,
        headers={"X-Goog-Api-Key": API_KEY},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def get_uploads_playlist(handle):
    data = api_get("channels", {"part": "contentDetails", "forHandle": handle})
    items = data.get("items", [])
    if not items:
        raise SystemExit(f"Channel not found: {handle}")
    return items[0]["contentDetails"]["relatedPlaylists"]["uploads"]


def get_video_ids(playlist_id):
    video_ids = []
    page_token = None
    page = 0
    while True:
        params = {"part": "contentDetails", "playlistId": playlist_id, "maxResults": 50}
        if page_token:
            params["pageToken"] = page_token
        data = api_get("playlistItems", params)
        page += 1
        for item in data["items"]:
            video_ids.append(item["contentDetails"]["videoId"])
        print(f"Page {page}: {len(data['items'])} videos")
        page_token = data.get("nextPageToken")
        if not page_token:
            break
    return video_ids


def get_video_details(video_ids):
    videos = []
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i:i + 50]
        data = api_get("videos", {
            "part": "snippet,statistics,contentDetails,liveStreamingDetails",
            "id": ",".join(chunk),
        })
        videos.extend(data["items"])
        print(f"Batch {i // 50 + 1}: requested {len(chunk)}, got {len(data['items'])}")
    return videos


if __name__ == "__main__":
    playlist_id = get_uploads_playlist(HANDLE)
    video_ids = get_video_ids(playlist_id)
    print("Total video IDs:", len(video_ids))
    print("Unique:", len(set(video_ids)))

    videos = get_video_details(video_ids)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out = RAW_DIR / "videos.json"
    out.write_text(json.dumps(videos, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {len(videos)} videos to {out}")