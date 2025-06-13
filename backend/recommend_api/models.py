from django.db import models

class Song(models.Model):
    artist = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    lyrics = models.TextField()
    tfidf = models.JSONField()
