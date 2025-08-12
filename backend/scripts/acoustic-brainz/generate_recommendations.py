# Generate recommendations based on a given MusicBrainzID using Cosine Similarity
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


target_mbid = "62c2e20a-559e-422f-a44c-9afa7882f0c4" # Michael Jackson - Beat It

target_track = Track.objects.get(musicbrainz_recordingid=target_mbid)
target_artist = target_track.artists.first()



feature_matrix = np.load("feature_matrix.npy", mmap_mode="r")
mbid_to_idx = np.load("mbid_to_feature_index.npy", allow_pickle=True)

# find similar songs
start = time.time()
query_index = np.where(mbid_to_idx == target_mbid)
query_vec = feature_matrix[query_index]
similarities = cosine_similarity(query_vec, feature_matrix).flatten()
top_indexes = similarities.argsort()[::-1][1:10]  # Top 10, excluding itself
end = time.time()
print(f"Cosine similarity search took {end - start:.2f} seconds")

top_mbids = mbid_to_idx[top_indexes].tolist()
top_tracks = Track.objects.filter(musicbrainz_recordingid__in=top_mbids).prefetch_related("artists")

print(f"Tracks similar to: {target_artist.name} - {target_track.title}:")
for t in top_tracks:
    artist = t.artists.first()
    name = artist.name if artist else "Unknown Artist"
    print(f"- {name} — {t.title}  [{t.musicbrainz_recordingid}]")
