# Generate recommendations based on a given MusicBrainzID using Cosine Similarity
# Note: This file loads the feature matrix into memory, make sure to import it only once
# Note: MBID - MusicBrainz unique IDs
import os, sys, time
import numpy as np
from dataclasses import dataclass
from sklearn.metrics.pairwise import cosine_similarity

filename = os.path.join(os.path.dirname(__file__), "../..", "features_and_index.npz")
try:
    data = np.load(filename, allow_pickle=True)
    # Load the audio features matrix and track metadata into memory
    feature_matrix = data["feature_matrix"]
    feature_matrix_raw = data["feature_matrix_raw"]
    feature_names = data["feature_names"]
    mbid_to_idx = data["mbids"]
    years = data["years"]  # release year
    genre_dortmund = data["genre_dortmund"]  # genre classification
    genre_rosamerica = data["genre_rosamerica"]  # genre classification
except FileNotFoundError as ex:
    print(f"Feature file not found at {filename}")

    
def recommend(target_mbid, options=None):
    """
    Returns k tracks that have similar features to a target track identified by MBID.

    Args:
        target_mbid (str): MusicBrainz ID of the target track.
        options (dict, optional): Dictionary of options to control recommendation behavior.
            - k (int): Number of similar tracks to return (default: 50).
            - use_ros (bool): Use Rosamerica genre classification for filtering, otherwise Dortmund (default: True).
            - exclude_mbids (list[str]): List of MBIDs to exclude from recommendations (default: []).
            - match_genre (bool): Whether to filter by genre (default: True).
            - match_decade (bool): Whether to filter by decade (default: True).

    Notes:
        The target_mbid is always excluded from the recommendations, even if not in exclude_mbids.

    Returns:
        dict: {
            "target_year": int,
            "target_genre_dortmund": str,
            "target_genre_rosamerica": str,
            "top_tracks": list[dict],  # Each dict: {mbid, similarity, year, genre_dortmund, genre_rosamerica}
            "stats": dict,  # {candidate_count, search_time, mean, std, p95, max}
        }
    """
    # Parse options
    if options is None:
        options = {}
    if not isinstance(options, dict):
        raise TypeError("options must be a dict")
    
    k = options.get("k", 50)
    use_ros = options.get("use_ros", True)
    exclude_mbids = options.get("exclude_mbids", [])
    match_genre = options.get("match_genre", True)
    match_decade = options.get("match_decade", True)

    # Identify the index, year and genre of the targeted track
    idxs = np.where(mbid_to_idx == target_mbid)[0]
    if idxs.size == 0:
        raise ValueError(f"Target MBID not found: {target_mbid}")
    target_index = int(idxs[0])

    target_year = int(years[target_index])
    target_genre_dortmund = genre_dortmund[target_index]
    target_genre_rosamerica = genre_rosamerica[target_index]

    # Filter the data to a subset of tracks which are in a += 10 year interval, same genre and
    # aren't excluded
    mask = np.ones_like(years, dtype=bool)
    if match_decade:
        target_decade = (target_year // 10) * 10
        mask &= (years >= target_decade) & (years < target_decade + 10)

    if match_genre:
        if use_ros:
            mask &= genre_rosamerica == target_genre_rosamerica
        else:
            mask &= genre_dortmund == target_genre_dortmund

    if exclude_mbids:
        # exclude list of provided mbids and target track
        mask &= ~np.isin(mbid_to_idx, exclude_mbids + [target_mbid])
    else:
        # always exclude the target
        mask &= ~np.isin(mbid_to_idx, [target_mbid])

    # the features we're comparing against, make sure to keep 2D shape
    query_vec = feature_matrix[target_index : target_index + 1]
    # filter EVERYTHING with the same mask, DO NOT rebind globals
    fm = feature_matrix[mask]
    mb = mbid_to_idx[mask]
    yrs = years[mask]
    gd = genre_dortmund[mask]
    gr = genre_rosamerica[mask]

    # Find similar tracks
    start = time.time()
    similarities = cosine_similarity(query_vec, fm).flatten()
    # `argsort` returns a list of indexes from the similarities array so that the values corresponding to
    # those indexes are sorted in ascending order.
    top_indexes = similarities.argsort()[::-1][:k]
    end = time.time()

    # build a list of the top most similar tracks and their metadata
    top_tracks = []
    for index in top_indexes:
        mbid = mb[index]

        top_tracks.append(
            {
                "mbid": mbid,
                "similarity": similarities[index],
                "year": yrs[index],
                "genre_dortmund": gd[index],
                "genre_rosamerica": gr[index],
            }
        )

    return {
        "target_year": target_year,
        "target_genre_dortmund": target_genre_dortmund,
        "target_genre_rosamerica": target_genre_rosamerica,
        "top_tracks": top_tracks,
        "stats": {
            "candidate_count": len(mb),
            "search_time": float(end - start),
            "mean": float(similarities.mean()),
            "std": float(similarities.std()),
            "p95": float(np.quantile(similarities, 0.95)),
            "max": float(similarities.max()),
        },
    }


def get_feature_stats():
    """
    Compute general stats about the audio features across all tracks.

    Returns:
        dict: A dictionary containing:
            - "unique_track_count" (int): Total number of tracks in the dataset.
            - "unique_vector_count" (int): Number of unique feature vectors.
            - "near_zero_col_count" (int): Number of feature columns with
              near-zero variance (< 1e-6 standard deviation).
            - "total_col_count" (int): Total number of feature columns.
    """
    # How many unique vectors exist, to check if multiple tracks have the same features
    rounded = np.round(feature_matrix, 4)
    _, unique_idx = np.unique(rounded, axis=0, return_index=True)

    # Column-wise variance (near-zero variance columns kill discrimination)
    col_std = feature_matrix.std(axis=0)
    zero_var_cols = (col_std < 1e-6).sum()

    return {
        "unique_track_count": len(mbid_to_idx),
        "unique_vector_count": unique_idx.size,
        "near_zero_col_count": int(zero_var_cols),
        "total_col_count": col_std.size,
    }
