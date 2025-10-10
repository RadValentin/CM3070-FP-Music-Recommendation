import logging
from django.http import HttpResponseRedirect
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response
from recommend_api.models import *
from recommend_api.serializers import *

log = logging.getLogger(__name__)


class AlbumViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AlbumSerializer
    queryset = Album.objects.prefetch_related("artists")
    lookup_field = "musicbrainz_albumid"
    lookup_url_kwarg = "mbid"
    filter_backends = [OrderingFilter]
    ordering_fields = ["name", "date"]
    ordering = ["pk"]

    @extend_schema(
        responses=AlbumResponseSerializer,
        description="Get album metadata and list of tracks"
    )
    def retrieve(self, request, *args, **kwargs):
        album = self.get_object()
        album_data = self.get_serializer(album).data

        # Get all tracks in this album
        tracks = Track.objects.filter(album=album).prefetch_related("artists")
        tracks_data = TrackSerializer(tracks, many=True).data

        # Remove 'album' key from each track dict as it's redundant
        for track in tracks_data:
            track.pop("album", None)

        # Add tracks to the response
        album_data["tracks"] = tracks_data
        serializer = AlbumResponseSerializer(album_data)
        return Response(serializer.data)
    
    @extend_schema(
        responses={302: None},
        description="Redirects to the album cover art image (250px) from the Cover Art Archive for the given MusicBrainz Album ID."
    )
    @action(detail=True, methods=["get"], url_path="art")
    def art(self, request, *args, **kwargs):
        mbid = self.get_object().musicbrainz_albumid
        response = HttpResponseRedirect(f"https://coverartarchive.org/release/{mbid}/front-250")
        response["Cache-Control"] = "public, max-age=2592000, immutable"
        return response
