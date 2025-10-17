from django.urls import reverse
from rest_framework.test import APITestCase
from unittest.mock import patch
from recommend_api.models import Album, Artist, Track
from recommend_api.tests.factories import ArtistFactory, AlbumFactory, TrackFactory


class RecommendAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        target_artist: Artist = ArtistFactory.create(musicbrainz_artistid="AR1")

        tracks: list[Track] = []
        for mbid, title in [("A", "Song A"), ("B", "Song B"), ("C", "Song C")]:
            new_track: Track = TrackFactory.create(
                musicbrainz_recordingid=mbid, title=title
            )
            new_track.artists.add(target_artist)
            tracks.append(new_track)

        cls.target_track: Track = tracks[0]
        cls.similar_tracks: Track = tracks[1:]

    def setUp(self):
        # Mock data returned by recommender.recommend
        self.recommend_response = {
            "target_year": 1991,
            "target_genre_dortmund": "rock",
            "target_genre_rosamerica": "roc",
            "top_tracks": [{
                "mbid": "B",
                "similarity": 0.9,
                "year": 1991,
                "genre_dortmund": "rock",
                "genre_rosamerica": "metal",
            }, {
                "mbid": "C",
                "similarity": 0.88,
                "year": 1991,
                "genre_dortmund": "rock",
                "genre_rosamerica": "metal",
            }],
            "stats": {
                "candidate_count": 3,
                "search_time": 0.01,
                "mean": 0.5,
                "std": 0.1,
                "p95": 0.9,
                "max": 0.92,
            },
        }
        self.patched_recommend = patch(
            "recommend_api.api.recommend.rec.recommend",
            return_value=self.recommend_response,
        )
        self.mock_recommend = self.patched_recommend.start()

    def test_response_signature(self):
        url = reverse("api:recommend")
        resp = self.client.post(url, {"mbid": "A"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("target_track", resp.data)
        self.assertIn("similar_list", resp.data)
        self.assertIn("stats", resp.data)

    def test_recommend_service_call_default_filters(self):
        url = reverse("api:recommend")
        self.client.post(url, {"mbid": "A"}, format="json")
        self.assertTrue(self.mock_recommend.called)
        self.mock_recommend.assert_called_once_with(
            target_mbid="A",
            options={
                "k": 100,
                "use_ros": True,
                "exclude_mbids": [],
                "match_genre": True,
                "match_decade": True,
                "feature_weights": {}
            },
        )

    def test_recommend_service_call_custom_filters(self):
        target_mbid = "A"
        listened_mbids = ["foo", "bar", "baz"]
        filters = {
            "same_genre": False,
            "same_decade": False,
            "genre_classification": "dortmund"
        }
        feature_weights = {
            "danceability": 0.9
        }
        url = reverse("api:recommend")
        self.client.post(url, {
            "mbid": target_mbid,
            "listened_mbids": listened_mbids,
            "filters": filters,
            "feature_weights": feature_weights,
            "limit": 30
        }, format="json")
        self.mock_recommend.assert_called_once_with(
            target_mbid=target_mbid,
            options={
                "k": 300,
                "use_ros": False,
                "exclude_mbids": listened_mbids,
                "match_genre": False,
                "match_decade": False,
                "feature_weights": feature_weights
            },
        )

    def test_400_on_missing_mbid(self):
        url = reverse("api:recommend")
        resp = self.client.post(url, {}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_404_on_invalid_mbid(self):
        url = reverse("api:recommend")
        resp = self.client.post(url, {"mbid": "BADMBID"}, format="json")
        self.assertEqual(resp.status_code, 404)

    def tearDown(self):
        self.patched_recommend.stop()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        AlbumFactory.reset_sequence(0)
        ArtistFactory.reset_sequence(0)
        TrackFactory.reset_sequence(0)
