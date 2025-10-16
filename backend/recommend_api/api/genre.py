import logging
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView
from recommend_api.models import *
from recommend_api.serializers import *

log = logging.getLogger(__name__)


class GenreView(APIView):
    @extend_schema(
        responses=GenreResponseSerializer,
        description="Get unique names of music genres in DB grouped by classifier.",
    )
    def get(self, request, *args, **kwargs):
        genres_dortmund = (
            Track.objects.exclude(genre_dortmund__isnull=True)
            .exclude(genre_dortmund="")
            .values_list("genre_dortmund", flat=True)
            .distinct()
            .order_by("genre_dortmund")
        )
        genres_rosamerica = (
            Track.objects.exclude(genre_rosamerica__isnull=True)
            .exclude(genre_rosamerica="")
            .values_list("genre_rosamerica", flat=True)
            .distinct()
            .order_by("genre_rosamerica")
        )
        data = {
            "genre_dortmund": sorted(set(genres_dortmund)),
            "genre_rosamerica": sorted(set(genres_rosamerica)),
        }
        serializer = GenreResponseSerializer(data)
        return Response(serializer.data)
