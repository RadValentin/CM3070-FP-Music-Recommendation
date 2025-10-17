from django.urls import reverse
from rest_framework.test import APITestCase
from recommend_api.models import Artist, Track, Album
from recommend_api.tests.factories import TrackFactory, ArtistFactory, AlbumFactory


class GenreAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.dortmund = ["rock", "pop", "metal", "pop", "metal", "rock", "metal"]
        cls.rosamerica = ["pop", "roc", "rhy", "roc", "rhy", "rhy", "pop"]
        cls.tracks: list[Track] = []
        for i in range(len(cls.dortmund)):
            cls.tracks.append(
                TrackFactory.create(
                    genre_dortmund=cls.dortmund[i], genre_rosamerica=cls.rosamerica[i]
                )
            )

    def test_get(self):
        url = reverse("api:genre-list")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertCountEqual(resp.data["genre_dortmund"], set(self.dortmund))
        self.assertCountEqual(resp.data["genre_rosamerica"], set(self.rosamerica))

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        TrackFactory.reset_sequence(0)
