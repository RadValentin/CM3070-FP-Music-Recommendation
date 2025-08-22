import numpy as np
from django.test import SimpleTestCase
import recommend_api.recommender as rec

class RecommenderTests(SimpleTestCase):
    responseKeys = [
        'target_year', 'target_genre_dortmund', 'target_genre_rosamerica', 'top_tracks', 'stats'
    ]

    def setUp(self):
        # Override the local variables of the module, removes the need to load feature matrix 
        # and metadata from disk

        # 4 tracks, 3-dim features
        rec.feature_matrix = np.array([
            [1.0, 0.0, 0.0],  # A
            [0.9, 0.1, 0.0],  # B  (most similar to A)
            [0.0, 1.0, 0.0],  # C
            [0.0, 0.0, 1.0],  # D
        ], dtype=float)

        rec.mbid_to_idx = np.array(['A', 'B', 'C', 'D'])
        # A,B,C in 1990s decade; D in 1980s
        rec.years = np.array([1991, 1992, 1994, 1983])  
        # Put A,B,C in same Rosamerica genre, D different
        rec.genre_rosamerica = np.array(['alt', 'alt', 'alt', 'roc'])
        rec.genre_dortmund = np.array(['metal', 'jazz', 'metal', 'metal'])
    
    def test_recommend_rosamerica(self):
        out = rec.recommend('A', k=2, use_ros=True)

        self.assertListEqual(list(out.keys()), self.responseKeys)
        # Candidates are A,B,C (same decade + same ros genre)
        self.assertEqual(out['stats']['candidate_count'], 3)
         # A is the target track, so expect B then C
        self.assertEqual(out['top_tracks'][0]['mbid'], 'B')
        self.assertEqual(out['top_tracks'][1]['mbid'], 'C')
    
    def test_recommend_dortmund(self):
        out = rec.recommend('A', k=2, use_ros=False)

        self.assertListEqual(list(out.keys()), self.responseKeys)
        self.assertEqual(out['stats']['candidate_count'], 2)
        self.assertEqual(out['top_tracks'][0]['mbid'], 'C')

    def test_feature_stats(self):
        # Make one column near-constant to trigger near_zero_col_count
        fm = rec.feature_matrix.copy()
        fm[:, 2] = 0.000001 
        rec.feature_matrix = fm

        stats = rec.get_feature_stats()
        assert stats['unique_track_count'] == 4
        assert stats['total_col_count'] == 3
        assert stats['near_zero_col_count'] >= 1
