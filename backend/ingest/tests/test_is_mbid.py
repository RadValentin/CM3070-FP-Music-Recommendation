from django.test import SimpleTestCase
from ingest.track_processing_helpers import is_mbid


class IsMbidTests(SimpleTestCase):
    def test_return_false_for_non_strings(self):
        self.assertFalse(is_mbid(42))
        self.assertFalse(is_mbid([]))
        self.assertFalse(is_mbid(None))
        self.assertFalse(is_mbid({}))
        self.assertFalse(is_mbid(True))

    def test_return_false_for_invalid_uuid(self):
        self.assertFalse(is_mbid("foo"))
        self.assertFalse(is_mbid("foo-bar"))

    def test_return_true_for_valid_uuid(self):
        self.assertTrue(is_mbid("9c5b94b1-35ad-49bb-b118-8e8fc24abf80"))
        self.assertTrue(is_mbid("53b106e7-0cc6-42cc-ac95-ed8d30a3a98e"))
        self.assertTrue(is_mbid("b1a9c0e9-d987-4042-ae91-78d6a3267d69"))