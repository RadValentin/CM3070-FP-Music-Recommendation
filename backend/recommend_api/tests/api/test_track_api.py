import numpy as np
from unittest.mock import patch
from django.urls import reverse
from rest_framework.test import APITestCase
from recommend_api.services.youtube_sources import YTSource
from recommend_api.models import Album, Track
from recommend_api.tests.factories import TrackFactory, AlbumFactory


class TrackAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.track_tuples = [("A", "Song A"), ("B", "Song B"), ("C", "Song C"), ("D", "Song D")]
        cls.tracks: list[Track] = []
        for mbid, title in cls.track_tuples:
            cls.tracks.append(TrackFactory.create(musicbrainz_recordingid=mbid, title=title))

    def test_get_list(self):
        url = reverse("api:track-list")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], len(self.tracks))
        self.assertEqual(len(resp.data["results"]), len(self.tracks))
        self.assertCountEqual(
            [r["mbid"] for r in resp.data["results"]],
            [mbid for mbid, _ in self.track_tuples]
        )

    def test_get_detail(self):
        track_tuple = self.track_tuples[0]
        url = reverse("api:track-detail", kwargs={"mbid": track_tuple[0]})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["mbid"], track_tuple[0])
        self.assertEqual(resp.data["title"], track_tuple[1])

    def test_get_features(self):
        mbid = self.track_tuples[0][0]
        with patch("recommend_api.api.track.rec") as mock_rec:
            features = np.array([0.5, 0.2])
            features_raw = np.array([50.0, 20.0])  
            mock_rec.mbid_to_idx = np.array([mbid for mbid, _ in self.track_tuples])
            mock_rec.feature_names = ["danceability", "aggressiveness"]
            mock_rec.feature_matrix = np.array([features], dtype=object)
            mock_rec.feature_matrix_raw = np.array([features_raw], dtype=object)

            url = reverse("api:track-features", kwargs={"mbid": mbid})
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.data["track"]["mbid"], mbid)
            self.assertDictEqual(resp.data["features"], {
                "danceability": features[0], "aggressiveness": features[1]
            })
            self.assertDictEqual(resp.data["raw_features"], {
                "danceability": features_raw[0], "aggressiveness": features_raw[1]
            })

    def test_get_sources(self):
        mbid = self.track_tuples[0][0]
        with patch("recommend_api.api.track.get_youtube_source") as mock_source:
            source = YTSource(
                video_id="foo-id",
                title="I Fooed 1000 Bars",
                channel="Mr. Foo",
                thumbnail="foo.png",
                url="http://foo.com",
            )
            mock_source.return_value = source
            url = reverse("api:track-sources", kwargs={"mbid": mbid})
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.data["track"]["mbid"], mbid)
            self.assertEqual(resp.data["sources"][0], {
                "provider": "youtube",
                "id": source.video_id,
                "title": source.title,
                "channel": source.channel,
                "thumbnail": source.thumbnail,
                "url": source.url,
            })
    
    def test_get_sources_not_found(self):
        mbid = self.track_tuples[0][0]
        with patch("recommend_api.api.track.get_youtube_source") as mock_source:
            mock_source.return_value = None
            url = reverse("api:track-sources", kwargs={"mbid": mbid})
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.data["track"]["mbid"], mbid)
            self.assertEqual(resp.data["sources"], [])

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        AlbumFactory.reset_sequence(0)
        TrackFactory.reset_sequence(0)
