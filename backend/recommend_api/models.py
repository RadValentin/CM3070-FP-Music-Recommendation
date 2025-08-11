from django.db import models


class Artist(models.Model):
    musicbrainz_artistid = models.UUIDField(primary_key=True) 
    name = models.CharField(max_length=255)


class Track(models.Model):
    musicbrainz_recordingid = models.UUIDField(primary_key=True)
    album = models.CharField(blank=True, null=True, max_length=255)
    title = models.CharField(max_length=255)
    release_date = models.DateField()
    duration = models.FloatField()
    country = models.CharField(blank=True, null=True, max_length=255)
    genre = models.CharField(max_length=255)
    danceability = models.FloatField()
    aggressiveness = models.FloatField()
    happiness = models.FloatField()
    sadness = models.FloatField()
    relaxedness = models.FloatField()
    partyness = models.FloatField()
    acousticness = models.FloatField()
    electronicness = models.FloatField()
    instrumentalness = models.FloatField()
    tonality = models.FloatField()
    brightness = models.FloatField()
    artists = models.ManyToManyField(Artist, through="TrackArtist")    


class TrackArtist(models.Model):
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE)
    track = models.ForeignKey(Track, on_delete=models.CASCADE)

    def special_save(self):
        pass