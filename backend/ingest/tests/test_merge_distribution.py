from django.test import SimpleTestCase
from ingest.track_processing_helpers import merge_distribution


class MergeDistributionTests(SimpleTestCase):
    def setUp(self):
        self.tracks = [
            {"moods_mirex": [1, 2, 3]},
            {"moods_mirex": [4, 5, 6]},
            {"moods_mirex": [7, 8, 9]},
        ]
    
    def test_returns_empty_dist(self):
        self.assertEqual(merge_distribution({}, "moods_mirex"), [])
    
    def test_returns_merged_dist(self):
        self.assertEqual(
            merge_distribution(self.tracks, "moods_mirex"), 
            [0.26666666666666666, 0.3333333333333333, 0.4]
        )

    def test_output_sums_up_to_1(self):
        result = merge_distribution(self.tracks, "moods_mirex")
        self.assertEqual(sum(result), 1)