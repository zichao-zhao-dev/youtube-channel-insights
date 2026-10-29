import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

RAW_FILE = Path("data/raw/videos.json")
DB_FILE = "youtube.db"
LOCAL_TZ = ZoneInfo("America/Toronto")
SHORT_MAX_SEC = 120

TOPIC_KEYWORDS = [
    ("Unboxing", ["amiibo"]),
    ("Animal Crossing", ["動物森友會", "動森", "acnh", "animalcrossing"]),
    ("Elden Ring", ["艾爾登法環", "艾尔登法环", "elden ring", "eldenring", "法環", "交界地", "黃金樹幽影", "黄金树幽影"]),
    ("Splatoon", ["斯普拉遁", "斯普拉頓", "splatoon"]),
    ("007 First Light", ["007"]),
    ("Paper Mario", ["紙片瑪利歐"]),
    ("Onimusha", ["鬼武者"]),
    ("Resident Evil", ["resident evil", "生化危机", "生化危機"]),
    ("Metroid", ["密特羅德", "密特罗德"]),
    ("Kirby", ["卡比"]),
    ("Zelda", ["zelda", "薩爾達"]),
    ("The Duskbloods", ["duskbloods"]),
]

TOPIC_OVERRIDES = {
    "4oII6YIDeK0": "Unboxing",          # RE Generation Pack short: unboxing, no "amiibo" in title
    "Z2tZL4R_qiw": "Metroid",           # Metroid Prime 4 review that mentions amiibo rewards
    "DSR9QucJTH0": "Animal Crossing",   # ACNH 3.0 update video that mentions amiibo
    "0ga5mpNErDY": "Unboxing",
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS videos (
    video_id        TEXT PRIMARY KEY,
    title           TEXT NOT NULL,
    published_utc   TEXT NOT NULL,
    published_local TEXT NOT NULL,
    weekday         TEXT NOT NULL,
    hour_local      INTEGER NOT NULL,
    duration_sec    INTEGER NOT NULL,
    is_live         INTEGER NOT NULL,
    content_type    TEXT NOT NULL,
    topic           TEXT NOT NULL,
    views           INTEGER NOT NULL,
    likes           INTEGER,
    comments        INTEGER
)
"""

DURATION_RE = re.compile(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")


def parse_duration(iso):
    m = DURATION_RE.fullmatch(iso)
    if not m:
        raise ValueError(f"Unexpected duration format: {iso}")
    hours, minutes, seconds = (int(g) if g else 0 for g in m.groups())
    return hours * 3600 + minutes * 60 + seconds


def to_local(utc_str):
    return datetime.fromisoformat(utc_str).astimezone(LOCAL_TZ)


def classify_topic(video_id, title):
    if video_id in TOPIC_OVERRIDES:
        return TOPIC_OVERRIDES[video_id]
    t = title.lower()
    for topic, keywords in TOPIC_KEYWORDS:
        if any(k in t for k in keywords):
            return topic
    return "Other"


def content_type(is_live, duration_sec):
    if is_live:
        return "Live"
    if duration_sec < SHORT_MAX_SEC:
        return "Short"
    return "Long"


def to_int(value):
    return int(value) if value is not None else None


def transform(item):
    stats = item["statistics"]
    local = to_local(item["snippet"]["publishedAt"])
    duration = parse_duration(item["contentDetails"]["duration"])
    is_live = "liveStreamingDetails" in item
    return (
        item["id"],
        item["snippet"]["title"],
        item["snippet"]["publishedAt"],
        local.isoformat(),
        local.strftime("%a"),
        local.hour,
        duration,
        int(is_live),
        content_type(is_live, duration),
        classify_topic(item["id"], item["snippet"]["title"]),
        int(stats["viewCount"]),
        to_int(stats.get("likeCount")),
        to_int(stats.get("commentCount")),
    )


def main():
    videos = json.loads(RAW_FILE.read_text(encoding="utf-8"))
    rows = [transform(v) for v in videos]

    conn = sqlite3.connect(DB_FILE)
    conn.execute(SCHEMA)
    conn.executemany(
        "INSERT OR REPLACE INTO videos VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", rows
    )
    conn.commit()

    total = conn.execute("SELECT COUNT(*) FROM videos").fetchone()[0]
    print(f"Loaded {len(rows)} videos, table now has {total}")

    print("\nBy content type:")
    for row in conn.execute("SELECT content_type, COUNT(*) FROM videos GROUP BY content_type"):
        print(" ", row)

    print("\nBy topic:")
    for row in conn.execute("SELECT topic, COUNT(*) FROM videos GROUP BY topic ORDER BY COUNT(*) DESC"):
        print(" ", row)

    print("\nClassified as Other (review these):")
    for (title,) in conn.execute("SELECT title FROM videos WHERE topic = 'Other'"):
        print(" ", title)

    conn.close()


if __name__ == "__main__":
    main()