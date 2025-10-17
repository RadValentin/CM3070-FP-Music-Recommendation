from django.urls import reverse
from rest_framework.test import APITestCase
from recommend_api.models import Album, Track
from recommend_api.tests.factories import TrackFactory, AlbumFactory


class AlbumAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.album_a: Album = AlbumFactory.create()
        cls.album_b: Album = AlbumFactory.create()
        cls.tracks: list[Track] = []
        for mbid, title in [("A", "Song A"), ("B", "Song B"), ("C", "Song C"), ("D", "Song D")]:
            if mbid == "A" or mbid == "B":
                new_track: Track = TrackFactory.create(
                    musicbrainz_recordingid=mbid, title=title, album=cls.album_a
                )
            else:
                new_track: Track = TrackFactory.create(
                    musicbrainz_recordingid=mbid, title=title, album=cls.album_b
                )
            cls.tracks.append(new_track)

    def test_get_list(self):
        url = reverse("api:album-list")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        returned_mbids = [r["mbid"] for r in resp.data["results"]]
        self.assertCountEqual(
            returned_mbids,
            [self.album_a.musicbrainz_albumid, self.album_b.musicbrainz_albumid],
        )

    def test_get_detail(self):
        album_id = self.album_a.musicbrainz_albumid
        url = reverse("api:album-detail", kwargs={"mbid": album_id})
        resp = self.client.get(url)
        track_mbids = [r["mbid"] for r in resp.data["tracks"]]
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["mbid"], album_id)
        self.assertCountEqual(track_mbids, ["A", "B"])

    def test_get_art(self):
        album_id = self.album_a.musicbrainz_albumid
        url = reverse("api:album-art", kwargs={"mbid": album_id})
        resp = self.client.get(url)
        self.assertRedirects(
            resp,
            f"https://coverartarchive.org/release/{album_id}/front-250",
            fetch_redirect_response=False,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        AlbumFactory.reset_sequence(0)
        TrackFactory.reset_sequence(0)
