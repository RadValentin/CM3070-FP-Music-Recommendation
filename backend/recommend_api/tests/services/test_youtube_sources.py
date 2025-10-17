from django.test import TestCase
from unittest.mock import patch, MagicMock
from recommend_api.tests.factories import TrackFactory, ArtistFactory
from recommend_api.services.youtube_sources import YTSource, get_youtube_source, YOUTUBE_SEARCH_URL


class YoutubeSourcesTests(TestCase):
    def setUp(self):
        # Test data
        self.artist = ArtistFactory()
        self.track = TrackFactory()
        self.track.artists.add(self.artist)
        self.mock_yt_api_key = "foo-bar-key"
        self.search_response = {
            "items": [{
                "id": {"videoId": "vid123"},
                "snippet": {
                    "title": "Track Title",
                    "channelTitle": "Channel X",
                    "thumbnails": {"medium": {"url": "http://thumb"}},
                },
            }]
        }
        
        # Mocks
        self.patched_dotenv = patch("recommend_api.services.youtube_sources.dotenv_values", 
                                 return_value={"YOUTUBE_API_KEY": self.mock_yt_api_key})
        self.mock_dotenv = self.patched_dotenv.start()
        
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = self.search_response
        self.patched_requests = patch("recommend_api.services.youtube_sources.requests.get", 
                                 return_value = response)
        self.mock_get = self.patched_requests.start()

    def test_raises_for_missing_api_key(self):
        self.mock_dotenv.return_value = {}
        self.assertRaises(RuntimeError, get_youtube_source, self.track)
    
    def test_makes_request_to_youtube_search(self):
        get_youtube_source(self.track)
        self.assertTrue(self.mock_get.called)
        self.mock_get.assert_called_once_with(YOUTUBE_SEARCH_URL, params={
            "part": "snippet",
            "q": f"{self.track.title} {self.artist.name}".strip(),
            "videoEmbeddable": "true",
            "type": "video",
            "maxResults": 10,
            "key": self.mock_yt_api_key
        }, timeout=8)
        self.assertIsInstance(self.artist.name, str)
    
    def test_returns_no_items_for_empty_response(self):
        empty_response = MagicMock()
        empty_response.json.return_value = {}
        self.mock_get.return_value = empty_response
        self.assertIsNone(get_youtube_source(self.track))
    
    def test_returns_youtube_sources(self):
        result: YTSource = get_youtube_source(self.track)
        json_source = self.search_response["items"][0]

        self.assertIsInstance(result, YTSource)
        self.assertEqual(result.video_id, json_source["id"]["videoId"])
        self.assertEqual(result.title, json_source["snippet"]["title"])
        self.assertEqual(result.channel, json_source["snippet"]["channelTitle"])
        self.assertEqual(result.thumbnail, json_source["snippet"]["thumbnails"]["medium"]["url"])
        self.assertIn(json_source["id"]["videoId"], result.url)

    def tearDown(self):
        self.patched_dotenv.stop()
        self.patched_requests.stop()
