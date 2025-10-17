from django.urls import reverse
from rest_framework.test import APITestCase
from recommend_api.models import Artist, Track, Album
from recommend_api.tests.factories import TrackFactory, ArtistFactory, AlbumFactory


class ArtistAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.artist_a: Artist = ArtistFactory.create()
        cls.artist_b: Artist = ArtistFactory.create()
        
        cls.album: Album = AlbumFactory.create()
        cls.album.artists.add(cls.artist_a)
        
        cls.tracks: list[Track] = []
        for mbid, title, subs in [
            ("A", "Song A", 1), ("B", "Song B", 2), ("C", "Song C", 3), ("D", "Song D", 4)
        ]:
            new_track: Track = TrackFactory.create(
                musicbrainz_recordingid=mbid, title=title, submissions=subs
            )
            if mbid == "A" or mbid == "B":
                new_track.artists.add(cls.artist_a)
            else:
                new_track.artists.add(cls.artist_b)
            cls.tracks.append(new_track)

    def test_get_list(self):
        url = reverse("api:artist-list")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        returned_mbids = [r["mbid"] for r in resp.data["results"]]
        self.assertCountEqual(
            returned_mbids,
            [self.artist_a.musicbrainz_artistid, self.artist_b.musicbrainz_artistid],
        )

    def test_get_detail(self):
        artist_id = self.artist_a.musicbrainz_artistid
        url = reverse("api:artist-detail", kwargs={"mbid": artist_id})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["mbid"], artist_id)
    
    def test_get_tracks(self):
        artist_id = self.artist_a.musicbrainz_artistid
        url = reverse("api:artist-tracks", kwargs={"mbid": artist_id})
        resp = self.client.get(url)
        track_mbids = [r["mbid"] for r in resp.data["results"]]
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(track_mbids, ["A", "B"])

    def test_get_top_tracks(self):
        artist_id = self.artist_a.musicbrainz_artistid
        url = reverse("api:artist-top-tracks", kwargs={"mbid": artist_id})
        resp = self.client.get(url)
        track_mbids = [r["mbid"] for r in resp.data["results"]]
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(track_mbids, ["B", "A"])

    def test_get_albums(self):
        artist_id = self.artist_a.musicbrainz_artistid
        url = reverse("api:artist-albums", kwargs={"mbid": artist_id})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["results"][0]["mbid"], self.album.musicbrainz_albumid)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        AlbumFactory.reset_sequence(0)
        ArtistFactory.reset_sequence(0)
        TrackFactory.reset_sequence(0)