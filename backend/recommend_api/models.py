from django.db import models

class Song(models.Model):
    id = models.IntegerField(primary_key=True)
    artist = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    lyrics = models.TextField()

class Track(models.Model):
    musicbrainz_recordingid = models.CharField(null=True, blank=True, max_length=255)
    artist = models.CharField(null=True, blank=True, max_length=255)
    album = models.CharField(null=True, blank=True, max_length=255)
    title = models.CharField(null=True, blank=True, max_length=255)
    release_date = models.DateField(null=True, blank=True)
    duration = models.FloatField(null=True, blank=True)
    genre = models.CharField(null=True, blank=True, max_length=255)
    danceability = models.FloatField(null=True, blank=True)
    aggressiveness = models.FloatField(null=True, blank=True)
    happiness = models.FloatField(null=True, blank=True)
    sadness = models.FloatField(null=True, blank=True)
    relaxedness = models.FloatField(null=True, blank=True)
    partyness = models.FloatField(null=True, blank=True)
    acousticness = models.FloatField(null=True, blank=True)
    electronicness = models.FloatField(null=True, blank=True)
    instrumentalness = models.FloatField(null=True, blank=True)
    tonality = models.FloatField(null=True, blank=True)
    brightness = models.FloatField(null=True, blank=True)