# loads the TF-IDF matrix data into memory so it can be later accessed inside views
import sys
import os
import numpy as np

filename = os.path.join(os.path.dirname(__file__), '..', 'tfidf_matrix.npy')
TFIDF_MATRIX = np.load(filename)
