from rest_framework import serializers
from .models import *


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