import json, os, re, urllib.request, urllib.parse
from datetime import datetime, timedelta

API_KEY = os.environ["YOUTUBE_API_KEY"]
CHANNEL_ID = "UClNdVSK1uy2xFHTaXZYXopw"
PLAYLIST_ID = "UU" + CHANNEL_ID[2:]
MAX_PAGES = 100
SHORT_SECONDS = 60  # この秒数以下ならショート扱い

def vid_id(url):
    m = re.search(r"(?:v=|youtu\.be/)([\w-]{11})", url)
    return m.group(1) if m else None

def api(endpoint, params):
    params["key"] = API_KEY
    url = "https://www.googleapis.com/youtube/v3/" + endpoint + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url) as res:
        return json.load(res)

def seconds(iso):
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso)
    d, h, mi, s = [int(x or 0) for x in m.groups()] if m else (0, 0, 0, 0)
    return d * 86400 + h * 3600 + mi * 60 + s

def game_name(title):
    m = re.search(r"【(.+?)】", title)
    return m.group(1).strip() if m else ""

# 今ある記録を読み込む
try:
    with open("videos.json", encoding="utf-8") as f:
        videos = json.load(f)
except FileNotFoundError:
    videos = []
known = {vid_id(v["url"]) for v in videos}

# 1) 新しい動画を追加（全ページ）
added = 0
page_token = None
for page in range(MAX_PAGES):
    params = {"part": "snippet", "playlistId": PLAYLIST_ID, "maxResults": 50}
    if page_token:
        params["pageToken"] = page_token
    data = api("playlistItems", params)
    for item in data["items"]:
        s = item["snippet"]
        vid = s["resourceId"]["videoId"]
        if vid in known or s["title"] in ("Private video", "Deleted video"):
            continue
        jst = datetime.strptime(s["publishedAt"], "%Y-%m-%dT%H:%M:%SZ") + timedelta(hours=9)
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

# 2) 種類を判定（50本ずつ詳細を取得）
by_id = {vid_id(v["url"]): v for v in videos if vid_id(v["url"])}
ids = list(by_id)
for i in range(0, len(ids), 50):
    chunk = ids[i:i + 50]
    data = api("videos", {
        "part": "contentDetails,liveStreamingDetails",
        "id": ",".join(chunk),
    })
    for item in data["items"]:
        v = by_id[item["id"]]
        if "liveStreamingDetails" in item:
            v["type"] = "配信"
        elif seconds(item["contentDetails"]["duration"]) <= SHORT_SECONDS or "#shorts" in v["title"].lower():
            v["type"] = "ショート"
        else:
            v["type"] = "動画"

# 3) ゲーム名（【】の中）を保存。手で直した分は上書きしない
for v in videos:
    if "game" not in v:
        v["game"] = game_name(v["title"])

videos.sort(key=lambda v: v["date"], reverse=True)
with open("videos.json", "w", encoding="utf-8") as f:
    json.dump(videos, f, ensure_ascii=False, indent=2)
print(f"{added}本追加、全{len(videos)}本を判定しました")
