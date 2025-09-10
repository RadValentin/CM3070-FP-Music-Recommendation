from rest_framework import serializers
from .models import *


# Model serializers (display all fields)
class ArtistSerializer(serializers.ModelSerializer):
    mbid = serializers.CharField(source="musicbrainz_artistid")

    class Meta:
        model = Artist
        fields = ["mbid", "name"]


class AlbumSerializer(serializers.ModelSerializer):
    mbid = serializers.CharField(source="musicbrainz_albumid")
    artists = ArtistSerializer(many=True)

    class Meta:
        model = Album
        fields = ["mbid", "name", "artists", "date"]


class TrackSerializer(serializers.ModelSerializer):
    mbid = serializers.CharField(source="musicbrainz_recordingid")
    artists = ArtistSerializer(many=True)
    album = AlbumSerializer(many=False, required=False)

    class Meta:
        model = Track
        fields = [
            "mbid",
            "title",
            "artists",
            "album",
            "duration",
            "genre_dortmund",
            "genre_rosamerica",
            "submissions"
        ]

# Recommender serializers
class RecommendStatsSerializer(serializers.Serializer):
    candidate_count = serializers.IntegerField()
    search_time = serializers.FloatField()
    mean = serializers.FloatField(allow_null=True)
    std = serializers.FloatField(allow_null=True)
    p95 = serializers.FloatField(allow_null=True)
    max = serializers.FloatField(allow_null=True)
