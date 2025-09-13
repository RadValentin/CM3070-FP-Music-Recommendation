# Data Processing for Music Recommendation System
import os, time, gc
import numpy as np
import pandas as pd
from . import track_processing_helpers as tph
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from django.db import transaction, connection
from dotenv import dotenv_values
from pathlib import Path
from sklearn.preprocessing import StandardScaler
from recommend_api.models import Track, Artist, TrackArtist, Album, AlbumArtist


def build_database(use_sample: bool, show_log: bool, num_parts: int = None, parts_list: list = None):
    WORKERS = max(8, (os.cpu_count() or 8))
    BASE_DIR = Path(__file__).resolve().parent.parent
    config = dotenv_values(BASE_DIR / ".env")
    # globals used to track how many records are skipped while processing
    duplicate_count = 0
    missing_artist_count = 0
    tph.mute_logs = not show_log

    ## NOTE: Phase 1 - Load JSON data about tracks into memory

    # Different directories where AcousticBrainz data is stored
    if use_sample:
        # 100k records
        dataset_path = config.get("AB_SAMPLE_ROOT")
    else:
        # 1M records
        dataset_path = config.get("AB_HIGHLEVEL_ROOT")

    # Clean old records
    print("Cleaning up old records", flush=True)
    AlbumArtist.objects.all().delete()
    Album.objects.all().delete()
    TrackArtist.objects.all().delete()
    Track.objects.all().delete()
    Artist.objects.all().delete()

    # If the user downloaded the AB dataset parts archives then store a list of the files,
    # we'll check and process later on, restrict based on param.
    archive_paths = [
        os.path.join(dataset_path, fname)
        for fname in os.listdir(dataset_path)
        if fname.lower().endswith(".tar.zst")
    ]
    if parts_list and len(archive_paths):
        archive_paths = [archive_paths[i] for i in parts_list]
    elif num_parts and len(archive_paths):
        archive_paths = archive_paths[:num_parts]    

    start = time.time()

    # If archive files were not found, search for extracted JSON files
    if len(archive_paths) < 1:
        # Dumps are split into parts of 1M, restrict how many we load
        parts_dirs = [
            os.path.join(dataset_path, fname)
            for fname in os.listdir(dataset_path)
            if os.path.isdir(os.path.join(dataset_path, fname))
        ]
        if parts_list:
            parts_dirs = [parts_dirs[i] for i in parts_list]
        elif num_parts:
            parts_dirs = parts_dirs[:num_parts]
        # paths to JSON files, each containing metadata and high-level features for one track
        json_paths = []

        for i, parts_dir in enumerate(parts_dirs):
            print(f"({i+1}/{len(parts_dirs)}) Building a list of JSON files in {parts_dir}", flush=True)
            # walks through a branch of the directory tree, it will look at all subfolders and files recursively
            for root, dirs, files in os.walk(parts_dir):
                for name in files:
                    if name.lower().endswith(".json"):
                        json_paths.append(os.path.join(root, name))
                    else:
                        print(f"Non-JSON file skipped: {name}")

        # json_paths = json_paths[0:1000] # use only a subset of the data, for debugging
        print(f"Will load {len(json_paths):,} records", end="", flush=True)
    else:
        print(f"Will load records from archives", flush=True)

    track_index = {}  # keep track of unique track data, indexed by MBID
    processing_counter = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        # Process file-by-file (individual JSONs)
        if len(archive_paths) < 1:
            futures = [executor.submit(tph.process_file, path) for path in json_paths]
        else:
            # Process archive-by-archive
            futures = [executor.submit(tph.process_archive, archive_path) for archive_path in archive_paths]

        for future in futures:
            try:
                future_results = future.result()
                if not isinstance(future_results, list):
                    future_results = [future_results]
            except Exception as e:
                print("parse error:", e, flush=True)
                continue

            for result in future_results:
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
        print("", flush=True)

    ## NOTE: Phase 2 - Merge duplicate entries for tracks by selecting the most common value for each field
    ## The goal is to have the most representative values for each feature among the duplicates of a track.

    print("Will merge duplicate tracks.", flush=True)

    merged_tracks = {}

    # Numeric fields for which we'll select the median value between duplicates
    NUM_FIELDS = [
        "duration",
        "danceability", "aggressiveness", "happiness", "sadness", "relaxedness", "partyness", 
        "acousticness", "electronicness", "instrumentalness", "tonality", "brightness"
    ]
    # Categorical fields for which we'll select the most common value between duplicates
    CAT_FIELDS = ["title", "genre_dortmund", "genre_rosamerica"]
    VEC_FIELDS = [("moods_mirex", tph.MIREX_ORDER)]
    VEC_FIELD_COLUMNS = [
        f"{field}_{i+1}" for field, order in VEC_FIELDS for i in range(len(order))
    ]

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
            values = [t.get(field) for t in tracks if t.get(field)]
            merged_track[field] = Counter(values).most_common(1)[0][0] if values else None

        # VECTOR: average values
        for field, order in VEC_FIELDS:
            merged_track[field] = tph.merge_distribution(tracks, field)

        # TUPLES: pick most common
        try:
            merged_track["artist_pairs"] = tph.merge_artist_pairs(tracks)
            merged_track["album_info"] = tph.merge_album_info(tracks)
        except Exception as e:
            tph.log(f"{e} {base_track['file_path']}")

        # Skip tracks that don't have an associated artist.
        if not merged_track["artist_pairs"]:
            missing_artist_count += 1
            continue

        # Use values from the base track + values selected by most common
        merged_track = base_track | merged_track
        merged_track["submissions"] = len(tracks)
        merged_tracks[mbid] = merged_track

    track_index = merged_tracks
    del merged_tracks
    gc.collect()

    ## NOTE: Phase 3 - Build the DB models

    print("Will build DB models.")

    album_index = {}  # keep track of unique album names, indexed by MBID
    artist_index = defaultdict(list)  # keep track of unique artist names, indexed by MBID
    trackartist_set = set() # set of all Track-Artist M2M pairings, to avoid duplication
    albumartist_set = set()  # set of all Album-Artist M2M pairings
    track_features_list = []  # list of feature values for each track
    track_list = []
    FEATURE_FIELDS = [
        "danceability", "aggressiveness", "happiness", "sadness", "relaxedness", "partyness", 
        "acousticness", "electronicness", "instrumentalness", "tonality", "brightness",
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
            submissions=track["submissions"],
            file_path=track["file_path"],
        )
        track_list.append(track_obj)

        # Associate artists, albums and tracks
        for artist_id, artist_name in artist_pairs:
            # Store artist data in a separate hashmap and associate it with the track
            artist_index[artist_id].append(artist_name)
            trackartist_set.add((track_id, artist_id))

            # Associate track with album, album with artist
            if not album_info:
                continue
            album_id, album_name, date = album_info

            # create Album object only if we have BOTH id and name
            if (album_id and album_name):
                if (album_id not in album_index) or (album_index[album_id] is None):
                    album_index[album_id] = Album(
                        musicbrainz_albumid=album_id, name=album_name, date=date
                    )

                # Link track to album
                track_obj.album = album_index[album_id]
                # Link album to artist
                albumartist_set.add((album_id, artist_id))

        # Store the track MBID + metadata + audio features, will be exported and used by recommendation
        # logic.
        track_features = [track.get(field) for field in FEATURE_FIELDS]
        # Get vector features
        vec_features = []
        for field, order in VEC_FIELDS:
            vec = track.get(field, [0.0]*len(order))
            vec_features.extend(vec)

        # If a track doesn't have album info (thus missing release year), default the year to 0
        year = 0
        if album_info and len(album_info) >= 3 and album_info[2]:
            try:
                year = album_info[2].year
            except Exception:
                year = 0

        track_features_list.append(
            [
                track["musicbrainz_recordingid"],
                track["genre_dortmund"],
                track["genre_rosamerica"],
                year # release year
            ]
            + track_features
            + vec_features
        )
    del track_index
    gc.collect()
    end = time.time()

    print(
        f"Finished loading records into memory in {end - start:.2f}s, now running the ORM inserts."
    )
    print(f"Found {duplicate_count:,} duplicate submissions.")
    print(f"Found {tph.invalid_date_count:,} submissions with invalid dates.")
    print(f"Found {tph.missing_data_count:,} submissions with missing data.")
    print(f"Dropped {missing_artist_count:,} tracks with no artist.")
    zero_year_count = sum(row[3] == 0 for row in track_features_list)
    print(f"Tracks with year=0: {zero_year_count} / {len(track_features_list)}")

    ## NOTE: Phase 4 - Insert data into DB

    with transaction.atomic():
        with connection.cursor() as c:
            c.execute("SET LOCAL synchronous_commit = OFF;")

        start = time.time()
        BATCH_SIZE = 20000

        # For artists that appear under different names, merge by selecting most common one
        merged_artist_index = {}
        for artist_id, artist_names in artist_index.items():
            merged_name = Counter(artist_names).most_common(1)[0][0]
            merged_artist_index[artist_id] = Artist(
                musicbrainz_artistid=artist_id, name=merged_name
            )
        Album.objects.bulk_create(album_index.values(), batch_size=BATCH_SIZE)
        Artist.objects.bulk_create(merged_artist_index.values(), batch_size=BATCH_SIZE)
        end = time.time()
        print(f"Inserted artists and albums in {end - start:.2f} seconds")

        start = time.time()
        print("Will insert records in DB", end="", flush=True)

        for i in range(0, len(track_list), BATCH_SIZE):
            Track.objects.bulk_create(
                track_list[i : i + BATCH_SIZE], batch_size=BATCH_SIZE
            )
            print(".", end="", flush=True)

        end = time.time()
        print(f"\nInserted {len(track_list)} records in {end - start:.2f} seconds")

        start = time.time()
        # M2M pairing were stored as sets to avoid duplication, convert them to lists and create objects.
        trackartist_list = []
        for track_id, artist_id in trackartist_set:
            trackartist_list.append(
                TrackArtist(artist=merged_artist_index[artist_id], track_id=track_id)
            )

        albumartist_list = []
        for album_id, artist_id in albumartist_set:
            album = album_index.get(album_id)
            if not album:
                continue
            albumartist_list.append(
                AlbumArtist(artist=merged_artist_index[artist_id], album=album)
            )

        for i in range(0, len(trackartist_list), BATCH_SIZE):
            TrackArtist.objects.bulk_create(trackartist_list[i:i+BATCH_SIZE], batch_size=BATCH_SIZE)

        for i in range(0, len(albumartist_list), BATCH_SIZE):
            AlbumArtist.objects.bulk_create(albumartist_list[i:i+BATCH_SIZE], batch_size=BATCH_SIZE)

        end = time.time()
        print(f"Inserted M2M pairings for TrackArtist and AlbumArtist in {end - start:.2f} seconds")

    ## NOTE: Phase 5 - Save data about audio features into vector files

    start = time.time()
    # Load the track audio features into a DataFrame and then export, keeping track
    # of how MBIS map to indexes in the feature matrix.
    DF_FEATURE_FIELDS = FEATURE_FIELDS + VEC_FIELD_COLUMNS

    df = pd.DataFrame(
        track_features_list,
        columns=["mbid", "genre_dortmund", "genre_rosamerica", "year", *DF_FEATURE_FIELDS],
    )
    df[DF_FEATURE_FIELDS] = df[DF_FEATURE_FIELDS].astype(np.float32)

    # separate indexes from features
    # feature_ids = df["mbid"].to_numpy()
    feature_matrix_raw = df[DF_FEATURE_FIELDS].to_numpy(dtype=np.float32)

    # Scale values so they're more spread out, fixes skewed distribution
    scaler = StandardScaler(with_mean=True, with_std=True).fit(feature_matrix_raw)
    feature_matrix_scaled = scaler.transform(feature_matrix_raw).astype(np.float32)

    # L2 normalize each row for cosine similarity later on
    feature_matrix_scaled /= (
        np.linalg.norm(feature_matrix_scaled, axis=1, keepdims=True) + 1e-8
    )

    filename = os.path.join(os.path.dirname(__file__), "..", "features_and_index.npz")
    np.savez_compressed(
        filename,
        # save vectors with values for audio features of tracks
        feature_matrix=feature_matrix_scaled,
        # keep the raw matrix for future re-weighting experiments
        feature_matrix_raw=feature_matrix_raw,
        feature_names=np.array(DF_FEATURE_FIELDS, dtype=object),
        # save mapping from MusicBrainz ID to indexes in feature matrix
        mbids=df["mbid"].to_numpy(),
        years=df["year"].to_numpy(np.int16),
        genre_dortmund=df["genre_dortmund"].to_numpy(),
        genre_rosamerica=df["genre_rosamerica"].to_numpy(),
    )

    end = time.time()
    print(f"Exported feature matrix and indexes in {end - start:.2f} seconds")
