from django.test import TestCase
import ingest.track_processing_helpers as tph
import orjson

class ExtractDataFromJsonStrTests(TestCase):
    @classmethod
    def setUpClass(cls):
        tph.mute_logs = True
        return super().setUpClass()

    def setUp(self):
        # Minimal valid JSON structure
        self.valid_json = orjson.dumps({
            "highlevel": {
                "genre_dortmund": {"value": "rock"},
                "genre_rosamerica": {"value": "roc"},
                "danceability": {"all": {"danceable": 0.5}},
                "mood_aggressive": {"all": {"aggressive": 0.2}},
                "mood_happy": {"all": {"happy": 0.3}},
                "mood_sad": {"all": {"sad": 0.1}},
                "mood_relaxed": {"all": {"relaxed": 0.4}},
                "mood_party": {"all": {"party": 0.6}},
                "mood_acoustic": {"all": {"acoustic": 0.7}},
                "mood_electronic": {"all": {"electronic": 0.8}},
                "voice_instrumental": {"all": {"instrumental": 0.9}},
                "tonal_atonal": {"all": {"tonal": 0.5}},
                "timbre": {"all": {"bright": 0.6}},
            },
            "metadata": {
                "audio_properties": {"length": 123},
                "tags": {
                    "musicbrainz_recordingid": ["12345678-1234-1234-1234-123456789abc"],
                    "title": ["Test Song"],
                    "musicbrainz_artistid": ["87654321-4321-4321-4321-cba987654321"],
                    "artist": ["Test Artist"],
                    "musicbrainz_albumid": ["11223344-5566-7788-99aa-bbccddeeff00"],
                    "album": ["Test Album"],
                    "date": ["2005-07-14"],
                    "originaldate": ["2005-07-14"],
                }
            }
        })

    def test_valid_json(self):
        result = tph.extract_data_from_json_str(self.valid_json)
        self.assertIsInstance(result, dict)
        self.assertEqual(result["title"], "Test Song")
        self.assertEqual(result["genre_dortmund"], "rock")
        self.assertEqual(result["duration"], 123)
        self.assertIn("artist_pairs", result)
        self.assertIn("album_info", result)

    def test_invalid_mbid(self):
        data = orjson.loads(self.valid_json)
        data["metadata"]["tags"]["musicbrainz_recordingid"] = ["BADMBID"]
        modified_json = orjson.dumps(data)
        result = tph.extract_data_from_json_str(modified_json)
        self.assertIsNone(result)

    def test_missing_field(self):
        data = orjson.loads(self.valid_json)
        data["metadata"]["tags"].pop("title", None)
        modified_json = orjson.dumps(data)
        result = tph.extract_data_from_json_str(modified_json)
        self.assertIsNone(result)

    def test_invalid_date(self):
        data = orjson.loads(self.valid_json)
        data["metadata"]["tags"]["date"] = ["0000-00-00"]
        data["metadata"]["tags"]["originaldate"] = ["0000-00-00"]
        modified_json = orjson.dumps(data)
        result = tph.extract_data_from_json_str(modified_json)
        self.assertIsNone(result)

    def test_empty_album(self):
        data = orjson.loads(self.valid_json)
        data["metadata"]["tags"]["album"] = [""]
        modified_json = orjson.dumps(data)
        result = tph.extract_data_from_json_str(modified_json)
        self.assertIsNone(result)
    
    def test_empty_title(self):
        data = orjson.loads(self.valid_json)
        data["metadata"]["tags"]["title"] = [""]
        modified_json = orjson.dumps(data)
        result = tph.extract_data_from_json_str(modified_json)
        self.assertIsNone(result)