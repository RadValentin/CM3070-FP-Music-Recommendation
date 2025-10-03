from django.test import SimpleTestCase
from ingest.track_processing_helpers import merge_artist_pairs


class MergeArtistPairsTests(SimpleTestCase):
    def test_picks_most_common_whole_config(self):
        A = [["a1", "Metallica"], ["a2", "Megadeth"]]
        B = [["a1", "Metallica"]]
        C = [["a2", "Megadeth"], ["a1", "Metallica"]]  # same as A after normalization

        tracks = [
            {"artist_pairs": A},
            {"artist_pairs": B},
            {"artist_pairs": A},
            {"artist_pairs": C},
        ]
        merged = merge_artist_pairs(tracks)
        self.assertEqual(merged, [("a1", "Metallica"), ("a2", "Megadeth")])

    def test_order_insensitive_same_config(self):
        # Two configs with same artists in different order should be treated as identical
        X = [("a2", "Megadeth"), ("a1", "Metallica")]
        Y = [("a1", "Metallica"), ("a2", "Megadeth")]

        tracks = [{"artist_pairs": X}, {"artist_pairs": Y}, {"artist_pairs": Y}]
        merged = merge_artist_pairs(tracks)
        self.assertEqual(merged, [("a1", "Metallica"), ("a2", "Megadeth")])

    def test_empty_when_no_pairs(self):
        tracks = [{"artist_pairs": []}, {"artist_pairs": None}, {}]
        merged = merge_artist_pairs(tracks)
        self.assertEqual(merged, [])  # consistent return type: list
