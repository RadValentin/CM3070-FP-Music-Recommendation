import requests
from requests import Response
from dataclasses import dataclass
from dotenv import dotenv_values
from music_recommendation.settings import BASE_DIR
from recommend_api.models import Track, Artist
from typing import Dict

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"


@dataclass
class YTSource:
    video_id: str
    title: str
    channel: str
    thumbnail: str
    url: str

    def __str__(self):
        title = (self.title or "").strip()
        channel = (self.channel or "").strip()
        return f"{title} - {channel} ({self.url})"

    def __repr__(self) -> str:
        return (
            f"YTSource(video_id={self.video_id!r}, title={self.title!r}, "
            f"channel={self.channel!r}, thumbnail={self.thumbnail!r}, url={self.url!r})"
        )


def get_youtube_source(track: Track) -> YTSource | None:
    config: Dict[str, str | None] = dotenv_values(BASE_DIR / ".env")
    YOUTUBE_API_KEY: str = config.get("YOUTUBE_API_KEY")

    if not YOUTUBE_API_KEY:
        raise RuntimeError("Missing YOUTUBE_API_KEY")

    artist: Artist = track.artists.first()
    artist_name: str = getattr(artist, "name", "") or ""
    query: str = f"{track.title} {artist_name}".strip()

    response: Response = requests.get(YOUTUBE_SEARCH_URL, params={
        "part": "snippet",
        "q": query,
        "videoEmbeddable": "true",
        "type": "video",
        "maxResults": 10,
        "key": YOUTUBE_API_KEY
    }, timeout=8)
    response.raise_for_status()
    
    items: list[dict] = response.json().get("items", [])
    
    # meta = {
    #     "query": query,
    #     "request_url": request.url, 
    #     "status": request.status_code, 
    #     "items_count": len(items)
    # }
    # print(meta)

    if not items:
        return None

    source: dict = items[0]
    video_id: str = source["id"]["videoId"]
    return YTSource(
        video_id=video_id,
        title=source["snippet"]["title"],
        channel=source["snippet"]["channelTitle"],
        thumbnail=source["snippet"]["thumbnails"]["medium"]["url"],
        url=f"https://www.youtube.com/watch?v={video_id}",
    )