from rest_framework import serializers
from .models import *

# Model serializers (display all fields)
class ArtistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Artist
        fields = '__all__'


class AlbumSerializer(serializers.ModelSerializer):
    class Meta:
        model = Album
        fields = '__all__'


class TrackSerializer(serializers.ModelSerializer):
    artists = ArtistSerializer(many=True)
    album = AlbumSerializer(many=False, required=False)

    class Meta:
        model = Track
        fields = '__all__'

# Model serializers for similar/ endpoint (display minimal subset of fields)
class SimilarAlbumSerializer(serializers.ModelSerializer):
    class Meta:
        model = Album
        fields = ['musicbrainz_albumid', 'name', 'date']


class SimilarTrackSerializer(serializers.ModelSerializer):
    artists = ArtistSerializer(many=True)
    album = SimilarAlbumSerializer(many=False, required=False)

    class Meta:
        model = Track
        fields = [
            'musicbrainz_recordingid', 'title', 'artists', 'album','genre_dortmund', 'genre_rosamerica'
        ]


# Recommender serializers
class RecommendStatsSerializer(serializers.Serializer):
    candidate_count = serializers.IntegerField()
    search_time = serializers.FloatField()
    mean = serializers.FloatField(allow_null=True)
    std = serializers.FloatField(allow_null=True)
    p95 = serializers.FloatField(allow_null=True)
    max = serializers.FloatField(allow_null=True)