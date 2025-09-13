import requests
from dataclasses import dataclass
from dotenv import dotenv_values
from music_recommendation.settings import BASE_DIR
from recommend_api.models import Track

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"


@dataclass
class YTSource:
    video_id: str
    title: str
    channel: str
    thumbnail: str
    url: str


def get_youtube_source(track: Track) -> YTSource:
    config = dotenv_values(BASE_DIR / ".env")
    YOUTUBE_API_KEY = config.get("YOUTUBE_API_KEY")

    if not YOUTUBE_API_KEY:
        raise RuntimeError("Missing YOUTUBE_API_KEY")

    artist = track.artists.first()
    artist_name = getattr(artist, "name", "") or ""
    query = f"{track.title} {artist_name}".strip()

    request = requests.get(YOUTUBE_SEARCH_URL, params={
        "part": "snippet",
        "q": query,
        "videoEmbeddable": "true",
        "type": "video",
        "maxResults": 10,
        "key": YOUTUBE_API_KEY
    }, timeout=8)
    request.raise_for_status()
    
    items = request.json().get("items", [])
    
    # meta = {
    #     "query": query,
    #     "request_url": request.url, 
    #     "status": request.status_code, 
    #     "items_count": len(items)
    # }
    # print(meta)

    if not items:
        return None

    source = items[0]
    video_id = source["id"]["videoId"]
    return YTSource(
        video_id=video_id,
        title=source["snippet"]["title"],
        channel=source["snippet"]["channelTitle"],
        thumbnail=source["snippet"]["thumbnails"]["medium"]["url"],
        url=f"https://www.youtube.com/watch?v={video_id}",
    )