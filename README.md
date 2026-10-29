# YouTube Channel Insights

A small ETL pipeline that pulls my own YouTube channel's public data through the **YouTube Data API v3**, loads it into SQLite, and analyzes which kinds of videos actually get watched.

Channel: [CHAO的遊戲頻道 (@quirkychao)](https://www.youtube.com/@quirkychao) — a Mandarin Chinese console gaming channel (PS5 and Nintendo Switch 2). Snapshot taken October 28, 2026: 74 public videos.

## Pipeline

```
fetch.py      channels.list → playlistItems.list → videos.list → data/raw/videos.json
load.py       videos.json → transforms → SQLite (youtube.db)
analysis.sql  three queries on the videos table
```

**Extract (`fetch.py`)**
- Looks up the channel by handle and gets its uploads playlist.
- Pages through the playlist with `nextPageToken` (74 videos → 2 pages of up to 50).
- Batches video IDs 50 at a time into `videos.list` for stats, duration and live-stream details (74 IDs → 2 calls instead of 74).
- Saves the raw response to disk, so transforms can be rerun without spending quota.
- A full run costs 5 quota units out of the default 10,000 per day.

**Transform + Load (`load.py`)**
- Casts counts from strings to integers; keeps hidden like/comment counts as `NULL`, not 0.
- Parses ISO 8601 durations (`PT1H37M34S`, `PT9H18M`, `PT27S`) with a regex where every part is optional; unknown formats raise an error.
- Converts UTC timestamps to `America/Toronto`, so daylight saving is handled.
- **Content type:** `Live` if the API returns `liveStreamingDetails`; otherwise `Short` (< 2 min) or `Long`.
- **Topic:** an ordered keyword map (Traditional and Simplified Chinese, English, abbreviations; first match wins), plus a small override table keyed by video ID for edge cases the keywords get wrong.
- Upserts with `INSERT OR REPLACE`: view counts change, so a rerun refreshes them without duplicating rows.

## Findings

| Content type | Videos | Hours of content | Share of views | Median views |
|---|---|---|---|---|
| Long | 23 | 2.8 | 78.2% | 128 |
| Short | 14 | 0.3 | 20.5% | 131.5 |
| Live | 37 | 92.5 | 1.4% | 4 |

1. **Format matters more than the game.** Live streams are half the videos and 97% of the content hours, but bring in 1.4% of views. The weakest topics (Splatoon, Paper Mario, 007 First Light) are almost entirely streams.
2. **The channel is hit-driven.** The top video carries 37.7% of all views and the top five carry 67.8%. Long videos have a median of 128 but a mean of about 480.
3. **The hits were timely.** The top three are long videos on new releases or new hardware: Elden Ring on Switch 2, Pokémon Pokopia, and The Duskbloods.
4. **Unboxings are the most consistent.** Among topics with at least three videos, unboxings have the highest median (311.5).

## Data checks

- Video IDs: 74 from the playlist, 74 unique, matching the channel's `videoCount`.
- Each batch logs IDs requested vs. returned, since deleted or private videos can drop out silently.
- Live flag: the API marks 37 videos as live; my own count is 36, so one is likely a premiere.
- Keyword rules were checked against every title before use. "Any title with amiibo is an unboxing" was wrong for two videos, and two unboxings never mention amiibo; those four are in the override table. One of them was only caught during analysis: it had been inflating a game's numbers.

## Limitations

- One small channel with low engagement, so these are observations, not general conclusions. Likes and comments are too sparse to analyze.
- "Hours of content" understates the effort behind an edited video (script, voiceover, editing), so views per hour flatters edits.
- Recent videos have had less time to collect views.
- An API key only sees public data. Watch time, traffic sources and audience geography need the YouTube Analytics API with OAuth.

## Run it

```bash
python3.12 -m venv .venv && source .venv/bin/activate
python -m pip install -r requirements.txt
echo "YOUTUBE_API_KEY=" > .env    # then add your key in an editor
python fetch.py
python load.py
sqlite3 youtube.db < analysis.sql
```

The API key is read from a git-ignored `.env` file and sent in the `X-Goog-Api-Key` header, never in the URL.

## Next steps

- Add the YouTube Analytics API with OAuth for watch time and retention.
- Add retries with exponential backoff to `api_get`.
- Hand-label whether each video has voiceover, to test whether it drives views.
