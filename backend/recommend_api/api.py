import logging
from django.urls import reverse
import numpy as np
from django.db.models import F
from django.http import HttpResponseRedirect
from rest_framework import mixins, viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import *
from .serializers import *
import recommend_api.recommender as rec

log = logging.getLogger(__name__)


class GenreView(APIView):
    def get(self, request):
        genres_dortmund = Track.objects.values_list("genre_dortmund", flat=True).distinct()
        genres_rosamerica = Track.objects.values_list("genre_rosamerica", flat=True).distinct()
        
        return Response({
            "genre_dortmund": sorted(set(genres_dortmund)),
            "genre_rosamerica": sorted(set(genres_rosamerica)),
        })


class TrackViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TrackSerializer
    queryset = Track.objects.all()

    @action(detail=True)
    def features(self, request, *args, **kwargs):
        track = self.get_object()
        track_data = self.get_serializer(track).data
        mbid = track.musicbrainz_recordingid
        index = np.where(rec.mbid_to_idx == mbid)[0]
        features = rec.feature_matrix[index][0]
        raw_features = rec.feature_matrix_raw[index][0]

        features_dict = {}
        raw_features_dict = {}
        for i, feature in enumerate(features):
            features_dict[rec.feature_names[i]] = feature
            raw_features_dict[rec.feature_names[i]] = raw_features[i]

        return Response({
            "track": track_data,
            "features": features_dict,
            "raw_features": raw_features_dict
        })
    
    @action(detail=True)
    def sources(self, request, *args, **kwargs):
        pass


class AlbumViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AlbumSerializer
    queryset = Album.objects.all()

    def retrieve(self, request, *args, **kwargs):
        album = self.get_object()
        album_data = self.get_serializer(album).data

        # Get all tracks in this album
        tracks = Track.objects.filter(album=album).prefetch_related("artists")
        tracks_data = TrackSerializer(tracks, many=True).data

        # Remove 'album' key from each track dict
        for track in tracks_data:
            track.pop("album", None)

        # Add tracks to the response
        album_data["tracks"] = tracks_data
        return Response(album_data)
    
    @action(detail=True)
    def art(self, request, *args, **kwargs):
        mbid = self.get_object().musicbrainz_albumid
        return HttpResponseRedirect(f"https://coverartarchive.org/release/{mbid}/front-250")

class ArtistViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ArtistSerializer
    queryset = Artist.objects.all()

    def get_data(self, Model, Serializer, order_by: str = None):
        artist = self.get_object()
        if order_by is not None:
            tracks = Model.objects.filter(artists=artist).order_by(
                F(order_by).desc(nulls_last=True)
            )
        else:
            tracks = Model.objects.filter(artists=artist)

        page = self.paginate_queryset(tracks)
        if page is not None:
            serializer = Serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = Serializer(tracks, many=True)
        return Response(serializer.data)

    @action(detail=True)
    def tracks(self, request, *args, **kwargs):
        return self.get_data(Track, TrackSerializer, order_by=None)

    @action(detail=True)
    def top_tracks(self, request, *args, **kwargs):
        return self.get_data(Track, TrackSerializer, order_by="submissions")

    @action(detail=True)
    def albums(self, request, *args, **kwargs):
        return self.get_data(Album, AlbumSerializer, order_by="date")


class RecommendView(APIView):
    def post(self, request):
        target_mbid = request.data.get("musicbrainz_recordingid")
        if not target_mbid:
            return Response(
                {"detail": "Missing 'musicbrainz_recordingid' parameter."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            target_track = Track.objects.get(musicbrainz_recordingid=target_mbid)
            target_artist = target_track.artists.first()
        except Track.DoesNotExist:
            return Response(
                {"detail": "Target track not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Get the recommendations dict, ask for a large number of similar tracks (50)
        # so we can have a buffer in case we need to filter the data
        # (e.g. same artist shows up multiple times)
        try:
            recommendations = rec.recommend(target_mbid, 50, True)
            top_tracks = recommendations["top_tracks"]
        except ValueError as e:
            # MBID not found in feature matrix
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except FileNotFoundError as e:
            # Feature matrix data couldn't be loaded from disk
            return Response(
                {"detail": str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception as e:
            # Any other error
            log.exception("Unexpected error in similar_tracks")
            return Response(
                {"detail": "Unexpected error."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Build the QuerySet for the similar track data and create an index based on MBID
        top_mbids = [t["mbid"] for t in top_tracks]
        track_map = {
            t.musicbrainz_recordingid: t
            for t in Track.objects.filter(
                musicbrainz_recordingid__in=top_mbids
            ).prefetch_related("artists")
        }

        # Go through the similar tracks and extract a subset by filtering for
        # artist name, track title, etc.
        similar_list = []
        for track in top_tracks:
            # Skip is target track is encountered again somehow
            if track["mbid"] == target_mbid:
                continue

            track_obj = track_map.get(track["mbid"])
            if not track_obj:
                continue

            artist = track_obj.artists.first()
            artist_name = artist.name if artist else "Unknown Artist"

            # Skip if it's the same song by the same artist as the target track
            if (
                artist_name == target_artist.name
                and track_obj.title == target_track.title
            ):
                continue

            # Include similarity score for the track
            similar_list.append((track_obj, track["similarity"]))

            # Limit the subset
            if len(similar_list) >= 5:
                break

        target_serializer = SimilarTrackSerializer(target_track)
        stats_serializer = RecommendStatsSerializer(recommendations["stats"])

        # Keep similarity in payload
        similar_payload = [
            {**SimilarTrackSerializer(obj).data, "similarity": sim}
            for (obj, sim) in similar_list
        ]

        return Response(
            {
                "target_track": target_serializer.data,
                "similar_list": similar_payload,
                "stats": stats_serializer.data,
            }
        )
