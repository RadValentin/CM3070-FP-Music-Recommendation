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
        kwargs = {"mbid": obj.musicbrainz_artistid}
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
        kwargs = {"mbid": obj.musicbrainz_albumid}
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
        kwargs = {"mbid": obj.musicbrainz_recordingid}
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
    """Serialized track data with an added similarity score"""
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


class RecommendFiltersSerializer(serializers.Serializer):
    exclude_artists = serializers.ListField(child=serializers.CharField(), required=False)
    same_genre = serializers.BooleanField(required=False)
    same_decade = serializers.BooleanField(required=False)
    genre_classification = serializers.ChoiceField(["rosamerica", "dortmund"], required=False)


class RecommendFeatureWeightsSerializer(serializers.Serializer):
    danceability = serializers.FloatField(required=False, min_value=0, max_value=1) 
    aggressiveness = serializers.FloatField(required=False, min_value=0, max_value=1) 
    happiness = serializers.FloatField(required=False, min_value=0, max_value=1) 
    sadness = serializers.FloatField(required=False, min_value=0, max_value=1) 
    relaxedness = serializers.FloatField(required=False, min_value=0, max_value=1) 
    partyness = serializers.FloatField(required=False, min_value=0, max_value=1) 
    acousticness = serializers.FloatField(required=False, min_value=0, max_value=1) 
    electronicness = serializers.FloatField(required=False, min_value=0, max_value=1) 
    instrumentalness = serializers.FloatField(required=False, min_value=0, max_value=1) 
    tonality = serializers.FloatField(required=False, min_value=0, max_value=1) 
    brightness = serializers.FloatField(required=False, min_value=0, max_value=1) 
    moods_mirex_1 = serializers.FloatField(required=False, min_value=0, max_value=1) 
    moods_mirex_2 = serializers.FloatField(required=False, min_value=0, max_value=1) 
    moods_mirex_3 = serializers.FloatField(required=False, min_value=0, max_value=1) 
    moods_mirex_4 = serializers.FloatField(required=False, min_value=0, max_value=1) 
    moods_mirex_5 = serializers.FloatField(required=False, min_value=0, max_value=1) 


class RecommendTotalWeightsSerializer(serializers.Serializer):
    similarity = serializers.FloatField(required=False, min_value=0, max_value=1)
    popularity = serializers.FloatField(required=False, min_value=0, max_value=1)


class RecommendRequestSerializer(serializers.Serializer):
    mbid = serializers.CharField(
        help_text="MusicBrainz recording ID of the target track"
    )
    listened_mbids = serializers.ListField(
        child=serializers.CharField(),
        help_text="IDs of tracks already listened to, won't show up in recommendations",
        required=False
    )
    filters = RecommendFiltersSerializer(required=False)
    feature_weights = RecommendFeatureWeightsSerializer(required=False)
    total_weights = RecommendTotalWeightsSerializer(required=False)
    limit = serializers.IntegerField(required=False)


class SearchResponseSerializer(serializers.Serializer):
    query = serializers.CharField()
    type = serializers.ChoiceField(["track", "artist", "album"])
    use_trigram = serializers.BooleanField()
    response_time = serializers.FloatField()
    count = serializers.IntegerField(min_value=0)
    results = serializers.ListField(
        child=serializers.DictField()
    )

