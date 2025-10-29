import logging, time
from django.contrib.postgres.search import TrigramDistance, TrigramWordDistance, SearchQuery, SearchRank
from django.db.models import F, Func, FloatField, ExpressionWrapper
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from recommend_api.models import *
from recommend_api.serializers import *

log = logging.getLogger(__name__)


class SearchView(APIView):
    """Search endpoint for tracks, albums and artists.

    This view accepts a free-text query via the `q` query parameter and returns
    a list of matching objects (`track`, `artist` or `album`). For short
    queries the endpoint falls back to case-insensitive substring matching
    (`icontains`); for longer queries it uses PostgreSQL full-text / trigram
    ranking against a `search_vector` on `Track` and a combined rank that
    mixes textual relevance with a popularity score.

    Query parameters:
    - q (required): search string
    - type (optional): one of "track", "artist", "album" (defaults to "track")
    - limit (optional): max number of results (default 100, clamped to 1..500)

    Returns a serialized JSON response with `query`, `type`, `use_trigram`,
    `response_time`, `count` and `results` keys.
    """
    @extend_schema(
        responses=SearchResponseSerializer,
        description="Search for tracks, albums or artists",
        parameters=[
            OpenApiParameter(name="q", type=str, location=OpenApiParameter.QUERY, required=True, description="The string to search for"),
            OpenApiParameter(name="type", type=str, location=OpenApiParameter.QUERY, required=False, description="What type of objects to return: track, album, or artist"),
        ]
    )
    def get(self, request):
        start_time = time.perf_counter()
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
                search_query = SearchQuery(query, search_type="websearch", config="simple")
                results = (
                    Track.objects.alias(
                        search_rank=SearchRank(F("search_vector"), search_query),
                        popularity=ExpressionWrapper(
                            Func(F("submissions") + 1, function="ln"),
                            output_field=FloatField(),
                        ),
                        combined_rank=ExpressionWrapper(
                            0.4 * F("search_rank") + 0.6 * F("popularity"),
                            output_field=FloatField(),
                        ),
                    )
                    .annotate(qs_order=models.Value(0, models.IntegerField()))
                    .filter(search_vector=search_query)
                    .order_by("-combined_rank")[:limit]
                    .select_related("album")
                    .prefetch_related("artists")
                )

                # FTS may not return enough results, fill in the rest using fuzzy trigram matching
                if len(results) < limit:
                    fts_ids = list(results.values_list("pk", flat=True))
                    fill_limit = limit - len(results)
                    if is_one_word:
                        distance_expr = TrigramWordDistance(query, "title")
                    else:
                        distance_expr = TrigramDistance("title", query)

                    trgm_results = (
                        Track.objects.filter(title__trigram_similar=query)
                        .alias(distance=distance_expr)
                        .annotate(qs_order=models.Value(1, models.IntegerField()))
                        .exclude(pk__in=fts_ids)
                        .order_by("distance", "-submissions")[:fill_limit]
                        .select_related("album")
                        .prefetch_related("artists")
                    )
                    # merge results while preserving order
                    results = results.union(trgm_results).order_by("qs_order")

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
        # print(str(results.query))
        # print(results.query.explain(using="default", format="text"))

        # materialize results BEFORE calculating response time for accurate timings
        results = serializer.data
        end_time = time.perf_counter()
        response_serializer = SearchResponseSerializer({
            "query": query,
            "type": search_type,
            "use_trigram": use_trigram,
            "response_time": end_time - start_time,
            "count": len(results),
            "results": results
        })
        return Response(response_serializer.data)
