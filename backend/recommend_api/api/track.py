import logging
import numpy as np
from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response
from recommend_api.models import *
from recommend_api.serializers import *
from recommend_api.services.youtube_sources import get_youtube_source
import recommend_api.services.recommender as rec

log = logging.getLogger(__name__)


class TrackViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TrackSerializer
    queryset = Track.objects.select_related("album").prefetch_related("artists")
    lookup_field = "musicbrainz_recordingid"
    lookup_url_kwarg = "mbid"
    filter_backends = [OrderingFilter]
    ordering_fields = ["title", "album__date", "submissions"] # fields that may be ordered against
    ordering = ["pk"] # default ordering

    @extend_schema(
        responses=TrackFeaturesResponseSerializer,
        description="Get track metadata along with audio features (scaled and unscaled)"
    )
    @action(detail=True, methods=["get"], url_path="features")
    def features(self, request, *args, **kwargs):
        track: Track = self.get_object()
        mbid = track.musicbrainz_recordingid
        index = np.where(rec.STORE.mbid_to_idx == mbid)[0]
        features = rec.STORE.feature_matrix[index][0]
        raw_features = rec.STORE.feature_matrix_raw[index][0]

        features_dict = {}
        raw_features_dict = {}
        for i, feature in enumerate(features):
            features_dict[rec.STORE.feature_names[i]] = feature
            raw_features_dict[rec.STORE.feature_names[i]] = raw_features[i]

        serializer = TrackFeaturesResponseSerializer({
            "track": track,
            "features": features_dict,
            "raw_features": raw_features_dict
        })
        return Response(serializer.data)

    @extend_schema(
        description="Get a list of sources for a track (Youtube)"
    )
    @action(detail=True)
    def sources(self, request, *args, **kwargs):
        track = self.get_object()

        try:
            source = get_youtube_source(track)
        except Exception as e:
            log.exception(f"YouTube lookup failed, {e}")
            payload = {"track": TrackSerializer(track).data, "sources": []}
            if settings.DEBUG:
                payload["debug"] = {"error": str(e)}
            return Response(payload, status=200)

        if not source:
            payload = {"track": TrackSerializer(track).data, "sources": []}
            return Response(payload, status=200)

        data = [{
            "provider": "youtube",
            "id": source.video_id,
            "title": source.title,
            "channel": source.channel,
            "thumbnail": source.thumbnail,
            "url": source.url,
        }]

        return Response({
            "track": TrackSerializer(track).data,
            "sources": data
        })
