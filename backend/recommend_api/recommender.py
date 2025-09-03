# Generate recommendations based on a given MusicBrainzID using Cosine Similarity
# Note: This file loads the feature matrix into memory, make sure to import it only once
# Note: MBID - MusicBrainz unique IDs
import os, sys, time
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

filename = os.path.join(os.path.dirname(__file__), '..', 'features_and_index.npz')
try:
    data = np.load(filename, allow_pickle=True)
    # Load the audio features matrix and track metadata into memory
    feature_matrix = data['feature_matrix']
    mbid_to_idx = data['mbids']
    years = data['years'] # release year
    genre_dortmund = data['genre_dortmund'] # genre classification
    genre_rosamerica = data['genre_rosamerica'] # genre classification
except FileNotFoundError as ex:
    print(f"Feature file not found at {filename}")


def recommend(target_mbid, k=50, use_ros=True):
    '''
    Returns k tracks that have similar features to a target track identified by MBID.

    Args:
        target_mbid (str): MusicBrainz ID of target track 
        k (int, optional): Number of similar tracks to return
        use_ros (bool, optional): If Rosamerica classification should be used to match genre (default), 
                        otherwise Dortmund is used.

    Returns:
        dict: A dictionary containing:
        "target_year": int,
          "target_genre_dortmund": str,
          "target_genre_rosamerica": str,
        - "top_tracks" (list[dict]): List of most similar tracks, each: {mbid, similarity, year, genre_dortmund, genre_rosamerica}.
        - "stats": Statistics about search {candidate_count, search_time, mean, std, p95, max}
    '''

    # Identify the index, year and genre of the targeted track
    idxs = np.where(mbid_to_idx == target_mbid)[0]
    if idxs.size == 0:
        raise ValueError(f"Target MBID not found: {target_mbid}")
    target_index = int(idxs[0])
    
    target_year = int(years[target_index])
    target_genre_dortmund = genre_dortmund[target_index]
    target_genre_rosamerica = genre_rosamerica[target_index]

    # Filter the data to a subset of tracks which are in a += 10 year interval and same genre
    target_decade = (target_year // 10) * 10
    same_decade_mask = (years >= target_decade) & (years < target_decade + 10)
    if use_ros:
        same_genre_mask = (genre_rosamerica == target_genre_rosamerica)
    else:
        same_genre_mask = (genre_dortmund == target_genre_dortmund)
    target_mask = same_decade_mask & same_genre_mask

    # the features we're comparing against, make sure to keep 2D shape
    query_vec = feature_matrix[target_index:target_index+1]
    # filter EVERYTHING with the same mask, DO NOT rebind globals
    fm = feature_matrix[target_mask]
    mb = mbid_to_idx[target_mask]
    yrs = years[target_mask]
    gd = genre_dortmund[target_mask]
    gr = genre_rosamerica[target_mask]
    target_index = np.where(mb == target_mbid)[0][0]

    # Find similar tracks
    start = time.time()
    similarities = cosine_similarity(query_vec, fm).flatten()
    # exclude target track by setting its similarity value to -Infinity
    similarities[target_index] = -np.inf
    # `argsort` returns a list of indexes from the similarities array so that the values corresponding to 
    # those indexes are sorted in ascending order.
    top_indexes = similarities.argsort()[::-1][:k]
    end = time.time()

    # build a list of the top most similar tracks and their metadata
    top_tracks = []
    for index in top_indexes:
        mbid = mb[index]
        
        top_tracks.append({
            'mbid': mbid,
            'similarity': similarities[index],
            'year': yrs[index],
            'genre_dortmund': gd[index],
            'genre_rosamerica': gr[index]
        })

    # Exclude target track from similarities so we can compute basic statistics
    self_idx = np.argmin(similarities)  # find where sim=-Infinity
    others = np.delete(similarities, self_idx)

    return {
        'target_year': target_year,
        'target_genre_dortmund': target_genre_dortmund,
        'target_genre_rosamerica': target_genre_rosamerica,
        'top_tracks': top_tracks,
        'stats': {
            'candidate_count': len(mb),
            'search_time': float(end - start),
            'mean': float(others.mean()),
            'std': float(others.std()),
            'p95': float(np.quantile(others, 0.95)),
            'max': float(others.max())
        }
    }



def get_feature_stats():
    '''
    Compute general stats about the audio features across all tracks.
    
    Returns:
        dict: A dictionary containing:
            - "unique_track_count" (int): Total number of tracks in the dataset.
            - "unique_vector_count" (int): Number of unique feature vectors.
            - "near_zero_col_count" (int): Number of feature columns with
              near-zero variance (< 1e-6 standard deviation).
            - "total_col_count" (int): Total number of feature columns.
    '''
    # How many unique vectors exist, to check if multiple tracks have the same features
    rounded = np.round(feature_matrix, 4)
    _, unique_idx = np.unique(rounded, axis=0, return_index=True)

    # Column-wise variance (near-zero variance columns kill discrimination)
    col_std = feature_matrix.std(axis=0)
    zero_var_cols = (col_std < 1e-6).sum()

    return {
        'unique_track_count': len(mbid_to_idx),
        'unique_vector_count': unique_idx.size,
        'near_zero_col_count': int(zero_var_cols),
        'total_col_count': col_std.size
    }