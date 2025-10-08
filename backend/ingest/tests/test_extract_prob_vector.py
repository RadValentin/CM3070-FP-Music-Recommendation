from django.test import SimpleTestCase
from ingest.track_processing_helpers import extract_prob_vector


class ExtractProbVectorTests(SimpleTestCase):
    def setUp(self):
        self.dist = [("Cluster1", 0.352815359831), ("Cluster2", 0.0591079592705), 
                     ("Cluster3", 0.0789495408535), ("Cluster4", 0.0582095906138),
                     ("Cluster5", 0.450917541981)]
        self.order = [name for name, _ in self.dist]
        self.highlevel = {
            "moods_mirex": {
                "all": {key: value for key, value in self.dist}
            }
        }

    def test_returns_prob_vector(self):
        result = extract_prob_vector(self.highlevel, "moods_mirex", self.order)
        expected = [value for _, value in self.dist]

        for i in range(len(result)):
            self.assertAlmostEqual(result[i], expected[i], places=7)
    
    def test_output_sums_up_to_1(self):
        result = extract_prob_vector(self.highlevel, "moods_mirex", self.order)
        self.assertEqual(sum(result), 1)