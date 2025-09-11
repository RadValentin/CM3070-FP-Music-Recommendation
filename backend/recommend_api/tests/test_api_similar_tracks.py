import json
from django.test import TestCase
from django.urls import reverse, reverse_lazy
from rest_framework.test import APIRequestFactory, APITestCase
from unittest.mock import patch
from recommend_api.models import Album, Artist, Track
from recommend_api.tests.factories import ArtistFactory, AlbumFactory, TrackFactory


class SimilarTracksAPITests(APITestCase):
    def setUp(self):
        target_artist = ArtistFactory(musicbrainz_artistid="AR1")
        
        tracks = []
        for mbid, title in [("A", "Song A"), ("B", "Song B"), ("C", "Song C")]:
            new_track = TrackFactory(musicbrainz_recordingid=mbid, title=title)
            new_track.artists.add(target_artist)
            tracks.append(new_track)

        self.target_track = tracks[0]
        self.similar_tracks = tracks[1:]
        # Mock data returned by recommender.recommend
        self.recommend_response = {
            "target_year": 1991,
            "target_genre_dortmund": "rock",
            "target_genre_rosamerica": "roc",
            "top_tracks": [
                {"mbid": "B", "similarity": 0.9, "year": 1991, "genre_dortmund": "rock", "genre_rosamerica": "metal"},
                {"mbid": "C", "similarity": 0.88, "year": 1991, "genre_dortmund": "rock", "genre_rosamerica": "metal"},
            ],
            "stats": {"candidate_count": 3, "search_time": 0.01, "mean": 0.5, "std": 0.1, "p95": 0.9, "max": 0.92},
        }

    def tearDown(self):
        Album.objects.all().delete()
        Artist.objects.all().delete()
        Track.objects.all().delete()
        AlbumFactory.reset_sequence(0)
        ArtistFactory.reset_sequence(0)
        TrackFactory.reset_sequence(0)

    @patch("recommend_api.api.rec.recommend")
    def test_response_signature(self, mock_rec):
        mock_rec.return_value = self.recommend_response
        url = reverse("api:recommend")
        resp = self.client.post(url, {"mbid": "A"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("target_track", resp.data)
        self.assertIn("similar_list", resp.data)
        self.assertIn("stats", resp.data)
