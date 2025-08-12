from django.db import models


class Artist(models.Model):
    musicbrainz_artistid = models.UUIDField(primary_key=True) 
    name = models.CharField(max_length=255)


class Album(models.Model):
    musicbrainz_albumid = models.UUIDField(primary_key=True) 
    name = models.CharField(max_length=255)
    artists = models.ManyToManyField(Artist, through="AlbumArtist")    
    date = models.DateField()
    #label = models.CharField(max_length=255)
    #asin = models.CharField(max_length=255) # Amazon product code
    #barcode = models.CharField(max_length=255) # album barcode


class AlbumArtist(models.Model):
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE)
    album = models.ForeignKey(Album, on_delete=models.CASCADE)
    #releasecountry = models.CharField(blank=True, null=True, max_length=255)

    class Meta:
        unique_together = [('artist', 'album')]

class Track(models.Model):
    musicbrainz_recordingid = models.UUIDField(primary_key=True)
    album = models.ForeignKey(Album, on_delete=models.CASCADE, null=True, blank=True)
    artists = models.ManyToManyField(Artist, through="TrackArtist")
    title = models.CharField(max_length=255)
    duration = models.FloatField()
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
     

class TrackArtist(models.Model):
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE)
    track = models.ForeignKey(Track, on_delete=models.CASCADE)

    class Meta:
        unique_together = [('track', 'artist')]