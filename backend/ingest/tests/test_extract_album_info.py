from django.test import SimpleTestCase
from ingest.track_processing_helpers import extract_album_info
from datetime import datetime, date



class ExtractalbumInfoTests(SimpleTestCase):
    def setUp(self):
        self.MBID = "53b106e7-0cc6-42cc-ac95-ed8d30a3a98e"

    def test_extracts_album_tuple(self):
        tags = {
            "musicbrainz_albumid": [self.MBID],
            "album": ["bar-name"],
            "date": ["2019"]
        }
        result = extract_album_info(tags)
        self.assertEqual(result, (self.MBID, "bar-name", date(2019, 1, 1)))
    
    def test_extracts_other_date(self):
        tags = {
            "musicbrainz_albumid": [self.MBID],
            "album": ["bar-name"],
            "originaldate": ["2019"]
        }
        result = extract_album_info(tags)
        self.assertEqual(result, (self.MBID, "bar-name", date(2019, 1, 1)))

    def test_returns_none_when_all_data_missing(self):
        tags = {}
        result = extract_album_info(tags)
        self.assertIsNone(result)

    def test_returns_none_when_all_data_invalid(self):
        tags = {
            "musicbrainz_albumid": ["WHOA"],
            "originaldate": ["YOLO"]
        }
        result = extract_album_info(tags)
        self.assertIsNone(result)

    def test_returns_partial_tuple_for_only_date(self):
        tags = {
            "originaldate": ["2019"]
        }
        result = extract_album_info(tags)
        self.assertEqual(result, (None, None, date(2019, 1, 1)))

    def test_returns_partial_tuple_for_only_name(self):
        tags = {
            "album": ["bar-name"],
        }
        result = extract_album_info(tags)
        self.assertEqual(result, (None, "bar-name", None))

    def test_returns_partial_tuple_for_only_id(self):
        tags = {
            "musicbrainz_albumid": [self.MBID],
        }
        result = extract_album_info(tags)
        self.assertEqual(result, (self.MBID, None, None))

    def test_returns_partial_tuple_for_bad_id(self):
        tags = {
            "musicbrainz_albumid": ["WHOA"],
            "album": ["bar-name"],
            "originaldate": ["2019"]
        }
        result = extract_album_info(tags)
        self.assertEqual(result, (None, "bar-name", date(2019, 1, 1)))