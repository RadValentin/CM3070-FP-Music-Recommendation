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
import track_processing_helpers as tph
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
tph.mute_logs = True

# Phase 1 - Load JSON data about tracks into memory

# Different directories where AcousticBrainz data is stored
#dataset_path = 'highlevel-full/' # 30M records
dataset_path = 'highlevel-partial/' # 1M records
#dataset_path = 'sample/' # 100k records

# Clean old records
print("Cleaning up old records", flush=True)
AlbumArtist.objects.all().delete()
Album.objects.all().delete()
TrackArtist.objects.all().delete()
Track.objects.all().delete()
Artist.objects.all().delete()

# paths to JSON files, each containting metadata and high-level features for one track
json_paths = [] 

print("Building a list of JSON files", flush=True)

# walks through a branch of the directory tree, it will look at all subfolders and files recursively
for root, dirs, files in os.walk(dataset_path):
    for name in files:
        if name.lower().endswith(".json"):
            json_paths.append(os.path.join(root, name))
        else:
            print(f"Non-JSON file skipped: {name}")


start = time.time()

#json_paths = json_paths[0:1000] # use only a subset of the data, for debugging
print(f"Will load {len(json_paths):,} records", end="", flush=True)

album_index = {} # keep track of unique album names, indexed by MBID
artist_index = {} # keep track of unique artist names, indexed by MBID
track_index = {} # keep track of unique track data, indexed by MBID
trackartist_set = set() # set of all Track-Artist M2M pairings, to avoid duplication
albumartist_set = set() # set of all Album-Artist M2M pairings
track_features_list = [] # list of feature values for each track

processing_counter = 0
with ThreadPoolExecutor() as executor:
    # TODO: To safely process the full 30M dataset on 16GB RAM, break JSON loading and inserts into smaller chunks
    # e.g. process 5–10 million files at a time to avoid memory exhaustion.
    futures = [executor.submit(tph.process_file, path) for path in json_paths]
    for future in futures:
        try:
            result = future.result()
        except Exception as e:
            print("parse error:", e)
            continue

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
        
        # print a dot every 1000 files
        processing_counter += 1
        if processing_counter % 1000 == 0:
            print(".", end="", flush=True)
    print("")

## Phase 2 - Merge duplicate entries for tracks by selecting the most common value for each field

print("Will merge duplicate tracks.")

merged_tracks = {}

# Numeric fields for which we'll select the median value between duplicates
NUM_FIELDS = [
    "danceability", "aggressiveness", "happiness", "sadness",
    "relaxedness", "partyness", "acousticness", "electronicness",
    "instrumentalness", "tonality", "brightness",
]
# Categorical fields for which we'll select the most common value between duplicates
CAT_FIELDS = ["genre_dortmund", "genre_rosamerica"]

for mbid, tracks in track_index.items():
    if not tracks:
        continue
    
    # Use a track as a base for fields that won't be selected
    base_track = tracks[0].copy()
    
    merged_track = {}    
    # NUMERIC: aggregate with median (robust)
    for field in NUM_FIELDS:
        values = [t[field] for t in tracks if t.get(field) is not None]
        merged_track[field] = float(np.median(values)) if values else None
    
    # CATEGORICAL (single-label fallback): pick most common non-empty
    for field in CAT_FIELDS:
        vals = [t.get(field) for t in tracks if t.get(field)]
        merged_track[field] = Counter(vals).most_common(1)[0][0] if vals else None
    
    # Use values from the base track + values selected by most common
    merged_track = base_track | merged_track
    merged_tracks[mbid] = merged_track
    # TODO: Add a popularity field proportional to the number of duplicates

track_index = merged_tracks


## Phase 3 - Build the DB models

print("Will build DB models.")

track_list = []
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
    
    # Store the track MBID + metadata + audio features, will be exported and used by recommendation 
    # logic.
    track_features = [track.get(field) for field in FEATURE_FIELDS]
    track_features_list.append([
        track["musicbrainz_recordingid"],
        track["genre_dortmund"],
        track["genre_rosamerica"],
        track["album_info"][2].year, # release year
    ] + track_features)    
end = time.time()

print(f"Finished loading records into memory in {end - start:.2f}s, now running the ORM inserts.")
print(f"Found {duplicate_count:,} duplicate submissions.")
print(f"Found {tph.invalid_date_count:,} submissions with invalid dates.")
print(f"Found {tph.missing_data_count:,} submissions with missing data.")

start = time.time()
Album.objects.bulk_create(album_index.values())
Artist.objects.bulk_create(artist_index.values())
end = time.time()
print(f"Inserted artists and albums in {end - start:.2f} seconds")

start = time.time()
batch_size = 2000
print("Will insert records in DB", end="", flush=True)

for i in range(0, len(track_list), batch_size):
    #print(f'{i}/{len(track_list)} processed')
    start_batch = time.time()
    Track.objects.bulk_create(track_list[i:i+batch_size])
    #print(f'Batch took {time.time() - start_batch:.2f} seconds')
    print(".", end="", flush=True)

end = time.time()
print(f"\nInserted {len(track_list)} records in {end - start:.2f} seconds")

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
end = time.time()
print(f"Inserted M2M pairings for TrackArtist and AlbumArtist in {end - start:.2f} seconds")

# Phase 4 - Save data about audio features into vector files

start = time.time()
# Load the track audio features into a DataFrame and then export, keeping track 
# of how MBIS map to indexes in the feature matrix.
df = pd.DataFrame(track_features_list, columns=[
    "mbid", "genre_dortmund", "genre_rosamerica", "year", *FEATURE_FIELDS
])
df[FEATURE_FIELDS] = df[FEATURE_FIELDS].astype(np.float32)

# separate indexes from features
#feature_ids = df["mbid"].to_numpy()
feature_matrix = df[FEATURE_FIELDS].to_numpy(dtype=np.float32)

# Scale values so they're more spread out, fixes skewed distribution
scaler = StandardScaler(with_mean=True, with_std=True).fit(feature_matrix)
feature_matrix_scaled = scaler.transform(feature_matrix).astype(np.float32)

# L2 normalize each row for cosine similarity later on
feature_matrix_scaled /= (np.linalg.norm(feature_matrix_scaled, axis=1, keepdims=True) + 1e-8)

filename = os.path.join(os.path.dirname(__file__), "../..", "features_and_index.npz")
np.savez_compressed(
    filename,
    # save vectors with values for audio features of tracks
    feature_matrix=feature_matrix_scaled,
    # save mapping from MusicBrainz ID to indexes in feature matrix
    mbids=df["mbid"].to_numpy(),
    years=df["year"].to_numpy(np.int16),
    genre_dortmund=df["genre_dortmund"].to_numpy(),
    genre_rosamerica=df["genre_rosamerica"].to_numpy(),
)

end = time.time()
print(f"Exported feature matrix and indexes in {end - start:.2f} seconds")


print("DONE")


