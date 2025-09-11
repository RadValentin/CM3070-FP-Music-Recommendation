from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework.reverse import reverse
from .models import *


# Model serializers (display all fields)
class ArtistSerializer(serializers.ModelSerializer):
    mbid = serializers.CharField(source="musicbrainz_artistid")
    links = serializers.SerializerMethodField()

    class Meta:
        model = Artist
        fields = ["mbid", "name", "links"]

    @extend_schema_field(serializers.DictField(child=serializers.CharField()))
    def get_links(self, obj):
        kwargs = {"musicbrainz_artistid": obj.musicbrainz_artistid}
        return {
            "self": reverse("api:artist-detail", kwargs=kwargs),
            "tracks": reverse("api:artist-tracks", kwargs=kwargs),
            "top-tracks": reverse("api:artist-top-tracks", kwargs=kwargs),
            "albums": reverse("api:artist-albums", kwargs=kwargs),
        }


class AlbumSerializer(serializers.ModelSerializer):
    mbid = serializers.CharField(source="musicbrainz_albumid")
    artists = ArtistSerializer(many=True)
    links = serializers.SerializerMethodField()

    class Meta:
        model = Album
        fields = ["mbid", "name", "artists", "date", "links"]

    @extend_schema_field(serializers.DictField(child=serializers.CharField()))
    def get_links(self, obj):
        kwargs = {"musicbrainz_albumid": obj.musicbrainz_albumid}
        return {
            "self": reverse("api:album-detail", kwargs=kwargs),
            "art": reverse("api:album-art", kwargs=kwargs),
        }


class TrackSerializer(serializers.ModelSerializer):
    mbid = serializers.CharField(source="musicbrainz_recordingid")
    artists = ArtistSerializer(many=True)
    album = AlbumSerializer(many=False, required=False, allow_null=True)
    links = serializers.SerializerMethodField()

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
            "submissions",
            "links"
        ]

    @extend_schema_field(serializers.DictField(child=serializers.CharField()))
    def get_links(self, obj):
        kwargs = {"musicbrainz_recordingid": obj.musicbrainz_recordingid}
        return {
            "self": reverse("api:track-detail", kwargs=kwargs),
            "features": reverse("api:track-features", kwargs=kwargs),
            "sources": reverse("api:track-sources", kwargs=kwargs),
        }


# API response serializers
class GenreResponseSerializer(serializers.Serializer):
    genre_dortmund = serializers.ListField(child=serializers.CharField())
    genre_rosamerica = serializers.ListField(child=serializers.CharField())


class TrackFeaturesResponseSerializer(serializers.Serializer):
    track = TrackSerializer()
    features = serializers.DictField()
    raw_features = serializers.DictField()


class AlbumResponseSerializer(AlbumSerializer):
    tracks = TrackSerializer(many=True)

    class Meta(AlbumSerializer.Meta):
        fields = AlbumSerializer.Meta.fields + ["tracks"]


class SimilarTrackSerializer(TrackSerializer):
    similarity = serializers.FloatField()
    
    class Meta(TrackSerializer.Meta):
        fields = TrackSerializer.Meta.fields + ["similarity"]


class RecommendStatsSerializer(serializers.Serializer):
    candidate_count = serializers.IntegerField()
    search_time = serializers.FloatField()
    mean = serializers.FloatField(allow_null=True)
    std = serializers.FloatField(allow_null=True)
    p95 = serializers.FloatField(allow_null=True)
    max = serializers.FloatField(allow_null=True)


class RecommendResponseSerializer(serializers.Serializer):
    target_track = TrackSerializer()
    similar_list = SimilarTrackSerializer(many=True)
    stats = RecommendStatsSerializer()


class RecommendRequestSerializer(serializers.Serializer):
    mbid = serializers.CharField(
        help_text="MusicBrainz recording ID of the target track"
    )


class SearchResponseSerializer(serializers.Serializer):
    query = serializers.CharField()
    type = serializers.ChoiceField(["track", "artist", "album"])
    use_trigram = serializers.BooleanField(),
    response_time = serializers.FloatField(),
    count = serializers.IntegerField(min_value=0),
    results = serializers.ListField(
        child=serializers.DictField()
    )

