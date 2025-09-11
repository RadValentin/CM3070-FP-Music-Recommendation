import logging, time
import numpy as np
from django.db.models import F
from django.http import HttpResponseRedirect
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import *
from .serializers import *
import recommend_api.recommender as rec

log = logging.getLogger(__name__)


class GenreView(APIView):
    @extend_schema(
        responses=GenreResponseSerializer,
        description="Get unique names of music genres in DB grouped by classifier."
    )
    def get(self, request):
        genres_dortmund = Track.objects.values_list("genre_dortmund", flat=True).distinct()
        genres_rosamerica = Track.objects.values_list("genre_rosamerica", flat=True).distinct()

        data = {
            "genre_dortmund": sorted(set(genres_dortmund)),
            "genre_rosamerica": sorted(set(genres_rosamerica)),
        }
        serializer = GenreResponseSerializer(data)
        return Response(serializer.data)


class TrackViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TrackSerializer
    queryset = Track.objects.select_related("album").prefetch_related("artists")
    lookup_field = "musicbrainz_recordingid"
    filter_backends = [OrderingFilter]
    ordering_fields = ["title", "album__date"] # fields that may be ordered against
    ordering = ["title"] # default ordering

    @extend_schema(
        responses=TrackFeaturesResponseSerializer,
        description="Get track metadata along with audio features (scaled and unscaled)"
    )
    @action(detail=True, methods=["get"], url_path="features")
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

        serializer = TrackFeaturesResponseSerializer({
            "track": track_data,
            "features": features_dict,
            "raw_features": raw_features_dict
        })
        return Response(serializer.data)
    
    @extend_schema(
        description="Get a list of sources for a track (Youtube)"
    )
    @action(detail=True)
    def sources(self, request, *args, **kwargs):
        return Response({ "detail": "Under construction" })


class AlbumViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AlbumSerializer
    queryset = Album.objects.prefetch_related("artists")
    lookup_field = "musicbrainz_albumid"
    filter_backends = [OrderingFilter]
    ordering_fields = ["name", "date"]
    ordering = ["name"]

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


class ArtistViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ArtistSerializer
    queryset = Artist.objects.all()
    lookup_field = "musicbrainz_artistid"
    filter_backends = [OrderingFilter]
    ordering_fields = ["name"]
    ordering = ["name"]

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

    @extend_schema(
        responses=TrackSerializer,
        description="Get all tracks for the artist."
    )
    @action(detail=True, methods=["get"], url_path="tracks")
    def tracks(self, request, *args, **kwargs):
        return self.get_data(Track, TrackSerializer, order_by=None)

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


class RecommendView(APIView):
    serializer_class = RecommendResponseSerializer

    @extend_schema(
        request=RecommendRequestSerializer,
        responses=RecommendResponseSerializer,
        description="Recommend similar tracks for a given MusicBrainz recording ID. Returns the target track, a list of similar tracks (with similarity scores), and recommendation statistics."
    )
    def post(self, request):
        target_mbid = request.data.get("mbid")
        if not target_mbid:
            return Response(
                {"detail": "Missing 'mbid' parameter."},
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
            ).select_related("album").prefetch_related("artists")
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

        target_serializer = TrackSerializer(target_track)
        stats_serializer = RecommendStatsSerializer(recommendations["stats"])

        # Keep similarity in payload
        similar_serializer= SimilarTrackSerializer([
            {**TrackSerializer(obj).data, "similarity": sim}
            for (obj, sim) in similar_list
        ])

        data = {
            "target_track": target_serializer.data,
            "similar_list": similar_serializer.data,
            "stats": stats_serializer.data,
        }
        serializer = RecommendResponseSerializer(data)
        return Response(serializer.data)


class SearchView(APIView):
    @extend_schema(
        responses=SearchResponseSerializer,
        description="Search for tracks, albums or artists",
        parameters=[
            OpenApiParameter(name="q", type=str, location=OpenApiParameter.QUERY, required=True, description="The string to search for"),
            OpenApiParameter(name="type", type=str, location=OpenApiParameter.QUERY, required=False, description="What type of objects to return: track, album, or artist"),
        ]
    )
    def get(self, request):
        start_time = time.time()
        query = request.GET.get("q", "").strip().lower()
        search_type = request.GET.get("type", "track").strip().lower()

        if not query:
            return Response(
                {"error": {"code": "INVALID_SEARCH_PARAM", "message": "Missing 'q' parameter."}},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if search_type not in ["track", "artist", "album"]:
            return Response(
                {"error": {"code": "INVALID_SEARCH_PARAM", "message": "Invalid 'type' parameter."}},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        use_trigram = len(query) >= 3
        if use_trigram:
            if search_type == "track":
                results = Track.objects.filter(title__trigram_similar=query)[:100]
                serializer = TrackSerializer(results, many=True)
            if search_type == "artist":
                results = Artist.objects.filter(name__trigram_similar=query)[:100]
                serializer = ArtistSerializer(results, many=True)
            if search_type == "album":
                results = Album.objects.filter(name__trigram_similar=query)[:100]
                serializer = AlbumSerializer(results, many=True)
        else:
            if search_type == "track": 
                results = Track.objects.filter(title__icontains=query)[:100]
                serializer = TrackSerializer(results, many=True)
            if search_type == "artist":
                results = Artist.objects.filter(name__icontains=query)[:100]
                serializer = ArtistSerializer(results, many=True)
            if search_type == "album":
                results = Album.objects.filter(name__icontains=query)[:100]
                serializer = AlbumSerializer(results, many=True)
        
        # for debugging SQL query
        # print(str(results.query))
        
        serializer = SearchResponseSerializer({
            "query": query,
            "type": search_type,
            "use_trigram": use_trigram,
            "response_time": round(time.time() - start_time, 3),
            "count": len(serializer.data),
            "results": serializer.data
        })
        return Response(serializer.data)