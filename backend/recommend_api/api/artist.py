import logging
from django.db.models import F
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response
from recommend_api.models import *
from recommend_api.serializers import *

log = logging.getLogger(__name__)


class ArtistViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ArtistSerializer
    queryset = Artist.objects.all()
    lookup_field = "musicbrainz_artistid"
    lookup_url_kwarg = "mbid"
    filter_backends = [OrderingFilter]
    ordering_fields = ["name"]
    ordering = ["pk"]

    def get_data(self, Model, Serializer, order_by: str = None, order: str = "desc"):
        artist = self.get_object()
        if order_by is not None:
            tracks = Model.objects.filter(artists=artist).order_by(
                F(order_by).desc(nulls_last=True)
                if order == "desc"
                else F(order_by).asc(nulls_last=True)
            )
        else:
            tracks = Model.objects.filter(artists=artist)

        page = self.paginate_queryset(tracks)
        if page is not None:
            serializer = Serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = Serializer(tracks, many=True)
        return Response(serializer.data)

    @extend_schema(
        responses=TrackSerializer,
        description="Get all tracks for the artist."
    )
    @action(detail=True, methods=["get"], url_path="tracks")
    def tracks(self, request, *args, **kwargs):
        return self.get_data(Track, TrackSerializer, order_by="title", order="asc")

    @extend_schema(
        responses=TrackSerializer,
        description="Get top tracks for the artist, ordered by submissions."
    )
    @action(detail=True, methods=["get"], url_path="top-tracks")
    def top_tracks(self, request, *args, **kwargs):
        return self.get_data(Track, TrackSerializer, order_by="submissions")

    @extend_schema(
        responses=AlbumSerializer,
        description="Get all albums for the artist, ordered by date."
    )
    @action(detail=True, methods=["get"], url_path="albums")
    def albums(self, request, *args, **kwargs):
        return self.get_data(Album, AlbumSerializer, order_by="date")
