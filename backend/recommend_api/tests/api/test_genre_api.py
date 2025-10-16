from django.urls import reverse
from rest_framework.test import APITestCase
from recommend_api.models import Artist, Track, Album
from recommend_api.tests.factories import TrackFactory, ArtistFactory, AlbumFactory


class GenreAPITests(APITestCase):
    @classmethod
    def setUpClass(self):
        self.dortmund = ["rock", "pop", "metal", "pop", "metal", "rock", "metal"]
        self.rosamerica = ["pop", "roc", "rhy", "roc", "rhy", "rhy", "pop"]
        self.tracks = []
        for i in range(len(self.dortmund)):
            self.tracks.append(
                TrackFactory.create(
                    genre_dortmund=self.dortmund[i], genre_rosamerica=self.rosamerica[i]
                )
            )

    def test_get(self):
        url = reverse("api:genre-list")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertCountEqual(resp.data["genre_dortmund"], set(self.dortmund))
        self.assertCountEqual(resp.data["genre_rosamerica"], set(self.rosamerica))

    @classmethod
    def tearDownClass(self):
        pass
