from django.db import models


class Artist(models.Model):
    musicbrainz_artistid = models.CharField(primary_key=True, max_length=36) 
    name = models.CharField(max_length=255)


class Album(models.Model):
    musicbrainz_albumid = models.CharField(primary_key=True, max_length=36) 
    name = models.CharField(max_length=255)
    artists = models.ManyToManyField(Artist, through='AlbumArtist')    
    date = models.DateField(null=True, blank=True)


class AlbumArtist(models.Model):
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE)
    album = models.ForeignKey(Album, on_delete=models.CASCADE)
    #releasecountry = models.CharField(blank=True, null=True, max_length=255)

    class Meta:
        unique_together = [('artist', 'album')]


class Track(models.Model):
    musicbrainz_recordingid = models.CharField(primary_key=True, max_length=36)
    album = models.ForeignKey(Album, on_delete=models.CASCADE, null=True, blank=True)
    artists = models.ManyToManyField(Artist, through='TrackArtist', related_name='tracks')
    title = models.TextField()
    duration = models.FloatField()
    genre_dortmund = models.CharField(max_length=255)
    genre_rosamerica = models.CharField(max_length=255)
    submissions = models.IntegerField()
    file_path = models.CharField(max_length=1024, null=True, blank=True)
     

class TrackArtist(models.Model):
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE)
    track = models.ForeignKey(Track, on_delete=models.CASCADE)

    class Meta:
        unique_together = [('track', 'artist')]