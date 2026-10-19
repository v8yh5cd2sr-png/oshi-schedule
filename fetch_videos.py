import json, os, re, urllib.request, urllib.parse
from datetime import datetime, timedelta

API_KEY = os.environ["YOUTUBE_API_KEY"]
CHANNEL_ID = "UClNdVSK1uy2xFHTaXZYXopw"
PLAYLIST_ID = "UU" + CHANNEL_ID[2:]  # チャンネルの全アップロード一覧
MAX_PAGES = 100  # 50本 x 100ページ = 最大5000本（安全のための上限）

def vid_id(url):
    m = re.search(r"(?:v=|youtu\.be/)([\w-]{11})", url)
    return m.group(1) if m else url

# 今ある記録を読み込む（手で書いた分も残す）
try:
    with open("videos.json", encoding="utf-8") as f:
        videos = json.load(f)
except FileNotFoundError:
    videos = []
known = {vid_id(v["url"]) for v in videos}

added = 0
page_token = None
for page in range(MAX_PAGES):
    params = {
        "part": "snippet",
        "playlistId": PLAYLIST_ID,
        "maxResults": 50,
        "key": API_KEY,
    }
    if page_token:
        params["pageToken"] = page_token
    url = "https://www.googleapis.com/youtube/v3/playlistItems?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url) as res:
        data = json.load(res)

    for item in data["items"]:
        s = item["snippet"]
        vid = s["resourceId"]["videoId"]
        if vid in known:
            continue
        if s["title"] in ("Private video", "Deleted video"):
            continue
        utc = datetime.strptime(s["publishedAt"], "%Y-%m-%dT%H:%M:%SZ")
        jst = utc + timedelta(hours=9)
        videos.append({
            "title": s["title"],
            "date": jst.strftime("%Y-%m-%d"),
            "url": "https://www.youtube.com/watch?v=" + vid,
            "type": "動画",
        })
        known.add(vid)
        added += 1

    page_token = data.get("nextPageToken")
    if not page_token:
        break

videos.sort(key=lambda v: v["date"], reverse=True)
with open("videos.json", "w", encoding="utf-8") as f:
    json.dump(videos, f, ensure_ascii=False, indent=2)
print(f"{added}本追加しました")
