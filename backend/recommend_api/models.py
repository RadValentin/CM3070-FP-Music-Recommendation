from django.db import models

class Song(models.Model):
    id = models.IntegerField(primary_key=True)
    artist = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    lyrics = models.TextField()
