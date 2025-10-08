from django.test import SimpleTestCase
from ingest.track_processing_helpers import extract_artist_info


class ExtractArtistInfoTests(SimpleTestCase):
    def setUp(self):
        self.artists = [
            ("53b106e7-0cc6-42cc-ac95-ed8d30a3a98e", "John Williams"),
            ("0383dadf-2a4e-4d10-a46a-e9e041da8eb3", "Queen")
        ]

        self.mock_tags = {
            "musicbrainz_artistid": [id for id, _ in self.artists],
            "artist": [name for _, name in self.artists],
            "artists": [name for _, name in self.artists]
        }
    
    def test_return_empty_for_missing_artist_ids(self):
        del self.mock_tags["musicbrainz_artistid"]
        self.assertEqual(extract_artist_info(self.mock_tags), [])

    def test_return_empty_for_id_name_count_mismatch(self):
        # remove last id
        self.mock_tags["musicbrainz_artistid"].pop()
        self.assertEqual(extract_artist_info(self.mock_tags), [])

    def test_return_empty_for_invalid_mbids(self):
        self.mock_tags["musicbrainz_artistid"] = [f"foo-{id}" for id, _ in self.artists]
        self.assertEqual(extract_artist_info(self.mock_tags), [])

    def test_return_valid_from_artist_tag(self):
        # artists is missing, should pull info from artist key
        del self.mock_tags["artists"]
        self.assertEqual(extract_artist_info(self.mock_tags), self.artists)

    def test_return_valid_from_artists_tag(self):
        # artist is missing, should pull info from artists key
        del self.mock_tags["artist"]
        self.assertEqual(extract_artist_info(self.mock_tags), self.artists)