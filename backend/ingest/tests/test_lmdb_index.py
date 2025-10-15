import os, shutil, uuid
import numpy as np
from django.test import SimpleTestCase
from ingest.lmdb_index import LMDBTrackIndex


class LMDBTrackIndexTests(SimpleTestCase):
    def setUp(self):
        self.store_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                       "test_store_data")
        if os.path.exists(self.store_path):
            shutil.rmtree(self.store_path)
        else:
            os.makedirs(self.store_path, exist_ok=True)
        
        self.store = LMDBTrackIndex(self.store_path, map_size=20 * 1024**2)
        self.key_a = "9a7f8913-7a6f-4708-9017-cf4d0c857756"
        self.key_b = "bc237111-3ae4-4b92-9f51-8c12d6435ff8"
        self.value_a =  {"value": "foo"}
        self.value_b = {"value": "bar"}

    def test_append(self):
        self.store.append(self.key_a, self.value_a)
        self.store.append(self.key_b, self.value_b)
        self.store.flush()
        self.assertDictEqual(self.store.get(self.key_a)[0], self.value_a)
        self.assertDictEqual(self.store.get(self.key_b)[0], self.value_b)

    def test_append_duplicates(self):
        # both values inserted under same key
        self.store.append(self.key_a, self.value_a)
        self.store.append(self.key_a, self.value_b)
        self.store.flush()
        self.assertEqual(self.store.get(self.key_a), [self.value_a, self.value_b])
        self.assertEqual(self.store.stats["duplicates"], 1)

    def test_append_invalid_mbid_raises(self):
        self.assertRaises(ValueError, self.store.append, "not-an-uuid", self.value_a)
    
    def test_set_item(self):
        self.store[self.key_a] = [self.value_a]
        self.store[self.key_b] = [self.value_b]
        self.store.flush()
        self.assertDictEqual(self.store.get(self.key_a)[0], self.value_a)
        self.assertDictEqual(self.store.get(self.key_b)[0], self.value_b)
    
    def test_get_item(self):
        self.store[self.key_a] = [self.value_a]
        self.store[self.key_b] = [self.value_b]
        self.store.flush()
        self.assertDictEqual(self.store[self.key_a][0], self.value_a)
        self.assertDictEqual(self.store[self.key_b][0], self.value_b)

    def test_delete(self):
        self.store[self.key_a] = [self.value_a]
        self.store[self.key_b] = [self.value_b]
        self.store[self.key_a] = None
        self.store.flush()
        self.assertIsNone(self.store[self.key_a])

    def test_items(self):
        keys = [str(uuid.uuid4()) for _ in range(10)]
        for i, key in enumerate(keys):
            self.store.append(key, {"value": i})
        self.store.flush()

        for key, values in self.store.items():
            i = keys.index(key)
            self.assertEqual(values, [{"value": i}])
    
    def test_keys(self):
        keys = [str(uuid.uuid4()) for _ in range(10)]
        for i, key in enumerate(keys):
            self.store.append(key, {"value": i})
        self.store.flush()
        self.assertEqual(self.store.keys(), set(keys))
    
    def test_keys_np(self):
        keys = [str(uuid.uuid4()) for _ in range(10)]
        for i, key in enumerate(keys):
            self.store.append(key, {"value": i})
        self.store.flush()

        result = {str(uuid.UUID(bytes=key.tobytes())) for key in self.store.keys_np()}
        self.assertEqual(result, set(keys))

    def test_first_key(self):
        keys = [str(uuid.uuid4()) for _ in range(10)]
        for i, key in enumerate(keys):
            self.store.append(key, {"value": i})
        self.store.flush()
        self.assertIn(self.store.first_key(), keys)

    def test_values(self):
        self.store[self.key_a] = [self.value_a]
        self.store[self.key_b] = [self.value_b]
        self.store.flush()
        for value in self.store.values():
            self.assertIn(value, [[self.value_a], [self.value_b]])

    def test_first_value(self):
        self.store[self.key_a] = [self.value_a]
        self.store[self.key_b] = [self.value_b]
        self.store.flush()
        self.assertIn(self.store.first_value(), [[self.value_a], [self.value_b]])

    def test_persistence(self):
        self.store[self.key_a] = [self.value_a]
        self.store.flush()

        tmp_store = LMDBTrackIndex(self.store_path)
        self.assertEqual(tmp_store.get(self.key_a), [self.value_a])
        tmp_store.close()

    def tearDown(self):
        self.store.close()
        if os.path.exists(self.store_path):
            shutil.rmtree(self.store_path)
    