from django.test import SimpleTestCase
from datetime import date
from ingest.track_processing_helpers import merge_album_info


class MergeAlbumInfoTests(SimpleTestCase):
    def test_merges_to_most_common_id(self):
        tracks = [
            {"album_info": ("id1", "Album One", "2000-01-01")},
            {"album_info": ("id1", "Album One", "2000-01-01")},
            {"album_info": ("id1", "Album One", "2000-01-01")},
            {"album_info": ("id2", "Other Album", "2010-01-01")},
            {"album_info": ("id2", "Other Album", "2010-01-01")},
            {"album_info": ("id3", "Other Album 3", "2010-01-01")},
            {"album_info": ("id3", "Other Album 3", "2010-01-01")},
        ]
        merged = merge_album_info(tracks)
        self.assertEqual(merged[0], "id1")
        self.assertEqual(merged[1], "Album One")
        self.assertEqual(merged[2], "2000-01-01")

    def test_selects_most_common_name_by_id(self):
        tracks = [
            {"album_info": ("id1", "Album One", "1999-01-01")},
            {"album_info": ("id1", "Album One", "1999-01-01")},
            {"album_info": ("id1", "Album One", "1999-01-01")},
            {"album_info": ("id1", "Album Two", "2001-02-02")},
            {"album_info": ("id1", "Album Two", "2001-02-02")},
            {"album_info": ("id1", "Album Three", "2005-03-03")},
        ]
        merged = merge_album_info(tracks)
        self.assertEqual(merged[1], "Album One")

    def test_handles_median_date(self):    
        tracks = [
            {"album_info": ("id1", "Album One", "1999-01-01")},
            {"album_info": ("id1", "Album One", "1999-01-01")},
            {"album_info": ("id1", "Album One", "1999-01-01")},
            {"album_info": ("id1", "Album One", "2001-02-02")},
            {"album_info": ("id1", "Album One", "2001-02-02")},
            {"album_info": ("id1", "Album One", "2005-03-03")},
        ]
        merged = merge_album_info(tracks)
        self.assertEqual(merged[2], "1999-01-01")

    def test_returns_none_if_no_tracks(self):
        tracks = []
        merged = merge_album_info(tracks)
        self.assertIsNone(merged)
    
    def test_returns_none_if_no_album_info(self):
        tracks = [{"album_info": None}, {}]
        merged = merge_album_info(tracks)
        self.assertIsNone(merged)