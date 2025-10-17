import logging, time
from django.contrib.postgres.search import TrigramDistance, TrigramWordDistance
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from recommend_api.models import *
from recommend_api.serializers import *

log = logging.getLogger(__name__)


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
        query = request.GET.get("q", "").strip()
        search_type = request.GET.get("type", "track").strip().lower()
        # parse the limit as an int, set an upper bound for it, default to a value for any errors
        try:
            limit = int(request.GET.get("limit", 100))
            if limit < 1 or limit > 500:
                limit = 100
        except (ValueError, TypeError):
            limit = 100

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

        is_one_word = len(query.split()) == 1
        use_trigram = len(query) > 3
        if use_trigram:
            if search_type == "track":
                if is_one_word:
                    distance_expr = TrigramWordDistance(query, "title")
                else:
                    distance_expr = TrigramDistance("title", query)
                results = (
                    Track.objects.filter(title__trigram_similar=query)
                    .annotate(distance=distance_expr)
                    .order_by("distance", "-submissions")[:limit]
                    .select_related("album")
                    .prefetch_related("artists")
                )
                serializer = TrackSerializer(results, many=True)
            if search_type == "artist":
                results = (
                    Artist.objects.filter(name__trigram_similar=query)
                    .annotate(distance=TrigramDistance("name", query))
                    .order_by("distance")[:limit]
                )
                serializer = ArtistSerializer(results, many=True)
            if search_type == "album":
                results = (
                    Album.objects.filter(name__trigram_similar=query)
                    .annotate(distance=TrigramDistance("name", query))
                    .order_by("distance")[:limit]
                    .prefetch_related("artists")
                )
                serializer = AlbumSerializer(results, many=True)
        else:
            if search_type == "track": 
                results = (
                    Track.objects.filter(title__icontains=query)[:limit]
                    .select_related("album")
                    .prefetch_related("artists")
                )
                serializer = TrackSerializer(results, many=True)
            if search_type == "artist":
                results = Artist.objects.filter(name__icontains=query)[:limit]
                serializer = ArtistSerializer(results, many=True)
            if search_type == "album":
                results = (
                    Album.objects.filter(name__icontains=query)[:limit]
                    .prefetch_related("artists")
                )
                serializer = AlbumSerializer(results, many=True)

        # for debugging SQL query
        #print(str(results.query))
        #print(results.query.explain(using="default", format="text"))

        response_serializer = SearchResponseSerializer({
            "query": query,
            "type": search_type,
            "use_trigram": use_trigram,
            "response_time": round(time.time() - start_time, 3),
            "count": len(serializer.data),
            "results": serializer.data
        })
        return Response(response_serializer.data)
