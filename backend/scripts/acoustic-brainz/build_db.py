# Data Processing for Music Recommendation System
# 
# > The code assumes you have downloaded and unzipped the AcousticBrainz DB dumps in the same 
# directory, under `highlevel-full/`, `highlevel-partial/` or `sample/`. 
# They can be downloaded from here: https://acousticbrainz.org/download

import io
import os
import sys
import django
import time
import numpy as np
import pandas as pd
import track_processing_helpers
from collections import Counter
from sklearn.preprocessing import StandardScaler
from concurrent.futures import ThreadPoolExecutor

# Ensure print output is UTF-8 formatted so it can be logged to a file
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Django setup so we can access ORM models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(os.getcwd()))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "music_recommendation.settings")
django.setup()

from recommend_api.models import Track, Artist, TrackArtist, Album, AlbumArtist

# globals used to track how many records are skipped while processing
duplicate_count = 0

# Phase 1 - Load JSON data about tracks into memory

# Different directories where AcousticBrainz data is stored
#dataset_path = 'highlevel-full/' # 30M records
#dataset_path = 'highlevel-partial/' # 1M records
dataset_path = 'sample/' # 100k records

# Clean old records
AlbumArtist.objects.all().delete()
Album.objects.all().delete()
TrackArtist.objects.all().delete()
Track.objects.all().delete()
Artist.objects.all().delete()

# paths to JSON files, each containting metadata and high-level features for one track
json_paths = [] 

# walks through a branch of the directory tree, it will look at all subfolders and files recursively
for root, dirs, files in os.walk(dataset_path):
    for name in files:
        if name.lower().endswith(".json"):
            json_paths.append(os.path.join(root, name))
        else:
            print(f"Non-JSON file skipped: {name}")


start = time.time()

#json_paths = json_paths[0:1000] # use only a subset of the data, for debugging
print(f"Will load {len(json_paths)} records")

album_index = {} # keep track of unique album names, indexed by MBID
artist_index = {} # keep track of unique artist names, indexed by MBID
track_index = {} # keep track of unique track data, indexed by MBID
trackartist_set = set() # set of all Track-Artist M2M pairings, to avoid duplication
albumartist_set = set() # set of all Album-Artist M2M pairings
track_features_list = [] 

# cpu_threads = os.cpu_count() or 4
# max_workers = cpu_threads * 2
with ThreadPoolExecutor(max_workers=8) as executor:
    # TODO: To safely process the full 30M dataset on 16GB RAM, break JSON loading and inserts into smaller chunks
    # e.g. process 5–10 million files at a time to avoid memory exhaustion.

    futures = [executor.submit(track_processing_helpers.process_file, path) for path in json_paths]
    for future in futures:
        result = future.result()
        if not result:
            continue

        track_id = result["musicbrainz_recordingid"]
        # Use a hashmap to check if the track has been already added (from another submission), 
        # only load it if that submission failed (missing data)
        if track_id not in track_index or track_index[track_id] is None:
            track_index[track_id] = [result]
        else:
            duplicate_count += 1
            track_index[track_id].append(result)


## Phase 2 - Merge duplicate entries for tracks by selecting the most common value for each field
merged_tracks = {}

# On which fields to select the most common value
MERGE_FIELDS = [
    "genre_dortmund", "genre_rosamerica",
    "danceability", "aggressiveness", "happiness", "sadness",
    "relaxedness", "partyness", "acousticness", "electronicness",
    "instrumentalness", "tonality", "brightness"
]

for mbid, tracks in track_index.items():
    if not tracks:
        continue
    
    # Use a track as a base for fields that won't be selected
    base_track = tracks[0]
    
    merged_track = {}
    for field in MERGE_FIELDS:
        values = [t[field] for t in tracks if t.get(field) is not None]
        if values:
            merged_track[field] = Counter(values).most_common(1)[0][0]
        else:
            merged_track[field] = None
    
    # Use values from the base track + values selected by most common
    merged_track = base_track | merged_track
    merged_tracks[mbid] = merged_track

track_index = merged_tracks


## Phase 3 - Build the DB models
track_list = []

MODEL_FIELDS = ["musicbrainz_recordingid", "title", "duration", "genre_dortmund", "genre_rosamerica", "file_path"]
FEATURE_FIELDS = [
    "danceability", "aggressiveness", "happiness", "sadness",
    "relaxedness", "partyness", "acousticness", "electronicness",
    "instrumentalness", "tonality", "brightness"
]

for track_id, track in track_index.items():
    artist_pairs = track["artist_pairs"]
    album_info = track["album_info"]

    track_obj = Track(
        musicbrainz_recordingid=track["musicbrainz_recordingid"],
        title=track["title"],
        duration=track["duration"],
        genre_dortmund=track["genre_dortmund"],
        genre_rosamerica=track["genre_rosamerica"],
        file_path=track["file_path"]
    )
    track_list.append(track_obj)

    for artist_id, artist_name in artist_pairs:
        # Store artist data in a separate hashmap and associtate it with the track
        if artist_id not in artist_index or artist_index[artist_id] is None:
            artist_index[artist_id] = Artist(musicbrainz_artistid=artist_id, name=artist_name)
        trackartist_set.add((track_id, artist_id))

        # Associate track with album, album with artist
        if not album_info:
            continue
        album_id, album_name, date = album_info
        
        if album_id not in album_index or album_index[album_id] is None:
            album_index[album_id] = Album(musicbrainz_albumid=album_id, name=album_name, date=date)
        
        track_obj.album = album_index[album_id]
        albumartist_set.add((album_id, artist_id))
    
    # Store the track audio features along with the MBID of the track they're for
    track_features = [track.get(field) for field in FEATURE_FIELDS]
    track_features_list.append([track["musicbrainz_recordingid"]] + track_features)    
end = time.time()

print(f"Finished loading records into memory in {end - start:.2f}s, now running the ORM inserts.")
print(f"Found {duplicate_count} duplicate submissions.")
print(f"Found {track_processing_helpers.invalid_date_count} submissions with invalid dates.")
print(f"Found {track_processing_helpers.missing_data_count} submissions with missing data.")

start = time.time()
Album.objects.bulk_create(album_index.values())
Artist.objects.bulk_create(artist_index.values())
print(f"Inserted artists and albums in {end - start:.2f} seconds")
end = time.time()

start = time.time()
batch_size = 2000

for i in range(0, len(track_list), batch_size):
    print(f'{i}/{len(track_list)} processed')
    start_batch = time.time()
    Track.objects.bulk_create(track_list[i:i+batch_size])
    print(f'Batch took {time.time() - start_batch:.2f} seconds')

end = time.time()
print(f"Inserted {len(track_list)} records in {end - start:.2f} seconds")

start = time.time()
# M2M pairing were stored as sets to avoid dulication, convert them to lists and create objects.
trackartist_list = []
for track_id, artist_id in trackartist_set:
    trackartist_list.append(TrackArtist(artist=artist_index[artist_id], track_id=track_id))
TrackArtist.objects.bulk_create(trackartist_list)

albumartist_list = []
for album_id, artist_id in albumartist_set:
    albumartist_list.append(AlbumArtist(artist=artist_index[artist_id], album=album_index[album_id]))
AlbumArtist.objects.bulk_create(albumartist_list)
print(f"Inserted M2M pairings for TrackArtist and AlbumArtist in {end - start:.2f} seconds")
end = time.time()

# Phase 4 - Save data about audio features into vector files

start = time.time()
# Load the track audio features into a DataFrame and then export, keeping track 
# of how MBIS map to indexes in the feature matrix.
feature_cols = ["danceability","aggressiveness","happiness","sadness","relaxedness","partyness",
                "acousticness","electronicness","instrumentalness","tonality","brightness"]
df = pd.DataFrame(track_features_list, columns=["mbid", *feature_cols])
df[feature_cols] = df[feature_cols].astype(np.float32)

# separate indexes from features
feature_ids = df["mbid"].to_numpy()
feature_matrix = df[feature_cols].to_numpy(dtype=np.float32)

# Scale values so they're more spread out, fixes skewed distribution
scaler = StandardScaler(with_mean=True, with_std=True).fit(feature_matrix)
feature_matrix_scaled = scaler.transform(feature_matrix).astype(np.float32)

# L2 normalize each row for cosine similarity later on
feature_matrix_scaled /= (np.linalg.norm(feature_matrix_scaled, axis=1, keepdims=True) + 1e-8)

# save vectors with values for audio features of tracks
np.save("feature_matrix.npy", feature_matrix_scaled) 
# save mapping from MusicBrainz ID to indexes in feature matrix
np.save("mbid_to_feature_index.npy", feature_ids)
print(f"Exported feature matrix and indexes in {end - start:.2f} seconds")
end = time.time()

print("DONE")


