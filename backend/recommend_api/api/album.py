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
        serializer = AlbumResponseSerializer(album, context={"request": request})
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
