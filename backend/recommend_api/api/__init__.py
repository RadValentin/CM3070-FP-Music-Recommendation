from .album import AlbumViewSet
from .artist import ArtistViewSet
from .genre import GenreView
from .recommend import RecommendView
from .search import SearchView
from .track import TrackViewSet

__all__ = [
    "AlbumViewSet",
    "ArtistViewSet",
    "GenreView",
    "RecommendView",
    "SearchView",
    "TrackViewSet",
]
