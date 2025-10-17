from django.urls import reverse
from rest_framework.test import APITestCase
from unittest.mock import patch
from recommend_api.models import Album, Artist, Track
from recommend_api.tests.factories import ArtistFactory, AlbumFactory, TrackFactory


class SearchAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tracks: list[Track] = []
        cls.albums: list[Album] = []
        cls.artists: list[Artist] = []
        for i in range(10):
            new_album = AlbumFactory.create(
                name=f"Album {'odd' if i % 2 == 1 else 'even'} {i}"
            )
            cls.albums.append(new_album)
            cls.tracks.append(TrackFactory.create(
                title=f"Track {'odd' if i % 2 == 1 else 'even'} {i}",
                album=new_album
            ))
            cls.artists.append(ArtistFactory.create(
                name=f"Artist {'odd' if i % 2 == 1 else 'even'} {i}"
            ))

    def test_400_on_missing_query(self):
        url = reverse("api:search")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 400)

    def test_400_on_invalid_type(self):
        url = reverse("api:search")
        resp = self.client.get(url, {"q": "tes", "type": "badtype"})
        self.assertEqual(resp.status_code, 400)

    def test_response_format(self):
        url = reverse("api:search")
        resp = self.client.get(url, {"q": "eve"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["query"], "eve")
        self.assertEqual(resp.data["type"], "track")
        self.assertEqual(resp.data["use_trigram"], False)
        self.assertIn("response_time", resp.data)
        self.assertEqual(resp.data["count"], 5)
        self.assertEqual(len(resp.data["results"]), 5)

    def test_search_for_track(self):
        url = reverse("api:search")
        resp = self.client.get(url, {"q": "eve", "type": "track"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], 5)
        self.assertContains(resp, "Track even", 5)

    def test_search_defaults_to_tracks(self):
        url = reverse("api:search")
        resp = self.client.get(url, {"q": "eve"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], 5)
        self.assertContains(resp, "Track even", 5)

    def test_search_for_artist(self):
        url = reverse("api:search")
        resp = self.client.get(url, {"q": "eve", "type": "artist"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], 5)
        self.assertContains(resp, "Artist even", 5)

    def test_search_for_album(self):
        url = reverse("api:search")
        resp = self.client.get(url, {"q": "eve", "type": "album"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], 5)
        self.assertContains(resp, "Album even", 5)

    def test_limit(self):
        url = reverse("api:search")
        resp = self.client.get(url, {"q": "odd", "limit": 0})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], 5)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        AlbumFactory.reset_sequence(0)
        ArtistFactory.reset_sequence(0)
        TrackFactory.reset_sequence(0)