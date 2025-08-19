# Generate recommendations based on a given MusicBrainzID using Cosine Similarity
# Note: MBID - MusicBrainz unique IDs
import io
import os
import sys
import time
import django
import numpy as np
from pprint import pprint
from sklearn.metrics.pairwise import cosine_similarity


# Ensure print output is UTF-8 formatted so it can be logged to a file
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Django setup so we can access ORM models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(os.getcwd()))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "music_recommendation.settings")
django.setup()

from recommend_api.models import Track



# Load the audio features matrix and track metadata
data = np.load("features_and_index.npz", allow_pickle=True)
feature_matrix = data["feature_matrix"]
mbid_to_idx = data["mbids"]
years = data["years"] # release year
genre_dortmund = data["genre_dortmund"] # genre classification
genre_rosamerica = data["genre_rosamerica"] # genre classification

#print(years, genre_dortmund, genre_rosamerica)

# Select a track from the database by its MBID
target_mbid = "62c2e20a-559e-422f-a44c-9afa7882f0c4" # Metallica - Enter Sandman
target_track = Track.objects.get(musicbrainz_recordingid=target_mbid)
target_artist = target_track.artists.first()
# Identify the index, year and genre of the targeted track
target_index = np.where(mbid_to_idx == target_mbid)[0][0]

# --- identify the query row
qi = np.where(mbid_to_idx == target_mbid)[0][0]
qv = feature_matrix[qi]

# (a) check row norms (cosine needs ~1.0 per row if you later do q @ X.T)
norms = np.linalg.norm(feature_matrix, axis=1)
print("norm min/max:", float(norms.min()), float(norms.max()))

# (b) are many rows almost identical to qv?
same_as_q = np.isclose(feature_matrix, qv, atol=1e-6).all(axis=1)
print("rows exactly ~equal to query:", int(same_as_q.sum()))

# (c) how many *unique* vectors (coarsely) exist?
rounded = np.round(feature_matrix, 4)
_, unique_idx = np.unique(rounded, axis=0, return_index=True)
print("unique rows (rounded 4dp):", unique_idx.size, " / ", feature_matrix.shape[0])

# (d) column-wise variance (near-zero variance columns kill discrimination)
col_std = feature_matrix.std(axis=0)
zero_var_cols = (col_std < 1e-6).sum()
print("near-zero-variance columns:", int(zero_var_cols), "of", col_std.size)

# (e) sanity on cosine: are your printed 0.99996 values actually <1.0?
s = cosine_similarity(qv[None, :], feature_matrix).ravel()
print("cos max (excl self):", float(np.partition(s, -2)[-2]))


target_year = years[target_index]
target_genre_dortmund = genre_dortmund[target_index]
target_genre_rosamerica = genre_rosamerica[target_index]

# Filter the data to a subset of tracks which are in a += 10 year interval and same genre
target_decade = (target_year // 10) * 10
same_decade_mask = (years >= target_decade) & (years < target_decade + 10)
same_genre_mask = (genre_rosamerica == target_genre_rosamerica)
target_mask = same_decade_mask & same_genre_mask

#print(feature_matrix[target_index])
#print(feature_matrix[np.where(mbid_to_idx == '78af6b52-8135-47b0-9bc2-a13f8c8cbc18')[0][0]])

# the features we're comparing against, make sure to keep 2D shape
query_vec = feature_matrix[target_index:target_index+1]
# filter EVERYTHING with the same mask
feature_matrix = feature_matrix[target_mask]
mbid_to_idx = mbid_to_idx[target_mask]
years = years[target_mask]
genre_dortmund = genre_dortmund[target_mask]
genre_rosamerica = genre_rosamerica[target_mask]
target_index = np.where(mbid_to_idx == target_mbid)[0][0]

# Find similar tracks
start = time.time()
similarities = cosine_similarity(query_vec, feature_matrix).flatten()
# exclude target track by setting its similarity value to -Infinity
similarities[target_index] = -np.inf
# `argsort` returns a list of indexes from the similarities array so that the values corresponding to 
# those indexes are sorted in ascending order.
top_indexes = similarities.argsort()[::-1][:50]
end = time.time()
print(f"Cosine similarity search took {end - start:.2f} seconds")

# extract the MBIDs for the top tracks and get data for them from the DB
top_mbids = mbid_to_idx[top_indexes].tolist()
top_tracks_qs = Track.objects.filter(musicbrainz_recordingid__in=top_mbids).prefetch_related("artists")

# Index the tracks by MBID in a dictionary
top_tracks = {}
for track in top_tracks_qs:
    top_tracks[track.musicbrainz_recordingid] = track


print(f"Tracks similar to: {target_artist.name} - {target_track.title} ({target_year}) [{target_genre_dortmund}] [{target_genre_rosamerica}] [{target_mbid}]:")

print("\nRecommendations:")
header = f"{'Artist':20} | {'Title':30} | {'Year':6} | {'Dortmund':10} | {'Rosamerica':10} | {'Sim':7} | {'MBID':10}"
print(header)
print("-" * len(header))

# Display the tracks in order by going through top_mbids list and extracting track data from a dict.
result_counter = 0
for mbid in top_mbids:
    track = top_tracks[mbid]
    artist = track.artists.first()
    artist_name = artist.name if artist else "Unknown Artist"
    
    if result_counter >= 10:
        break
    elif artist_name == target_artist.name and track.title == target_track.title:
        # Skip if it's the same song by the same artist as the target track
        continue
    else:
        result_counter += 1

    # Index of the track in the feature_matrix is needed so we can get its similarity score for display.
    track_index = np.where(mbid_to_idx == mbid)[0][0]
    sim = similarities[track_index]
    year = years[track_index]
    g_dor = genre_dortmund[track_index]
    g_ros = genre_rosamerica[track_index]

    print(f"{artist_name[:20]:20} | {track.title[:30]:30} | {str(year):6} | "
          f"{g_dor:10} | {g_ros:10} | {sim:6.5f} | {mbid}")

# Exclude target track from similarities and print basic statistics
self_idx = np.argmin(similarities)  # find where sim=-Infinity
others = np.delete(similarities, self_idx)
print("\nStats for similarities:")
print("mean:", float(others.mean()),
      "std:", float(others.std()),
      "p95:", float(np.quantile(others, 0.95)),
      "max:", float(others.max()))

end = time.time()
print(f"Script execution took {end - start:.2f} seconds")


