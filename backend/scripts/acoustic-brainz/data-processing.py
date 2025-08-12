# %% [markdown]
# # AcousticBrainz High-Level Sample Data Processing for Music Recommendation System
# 
# > The code assumes you have downloaded and unzipped the AcousticBrainz DB dumps in the same 
# directory, under `/highlevel/` or `/sample/`. 
# They can be downloaded from here: https://acousticbrainz.org/download

# %%
import io
import os
import re
import sys
import json
import django
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pprint import pprint

# Ensure print output is UTF-8 formatted so it can be logged to a file
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(os.getcwd()))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "music_recommendation.settings")
django.setup()

from recommend_api.models import Track, Artist, TrackArtist, Album, AlbumArtist

# globals used to track how many records are skipped while processing
duplicate_count = 0
invalid_date_count = 0
missing_data_count = 0

# %%

def parse_flexible_date(date_str):
    """
    Given a date as a string, try to extract its information as a datetime object
    """
    if not date_str or not isinstance(date_str, str):
        return None

    date_str = date_str.strip().lower()

    # Clean common invalid formats
    if date_str.startswith("0000") or "00-00" in date_str:
        return None
    
    # Remove ordinal suffixes: 1st, 2nd, 3rd, 23rd, etc.
    date_str = re.sub(r'(\d{1,2})(st|nd|rd|th)', r'\1', date_str)

    # Remove "of" (e.g. "23 of February" to "23 February")
    date_str = re.sub(r'\bof\b', '', date_str)

    # Remove extra commas and fix spacing
    date_str = re.sub(r',', '', date_str)
    date_str = re.sub(r'\s+', ' ', date_str).strip()

    formats = [
        "%Y-%m-%d",           # "2005-07-14"
        "%Y-%m",              # "2005-07"
        "%Y",                 # "2005"
        "%Y.%m.%d",           # "2000.06.21"
        "%d %B %Y",           # "23 February 1998"
        "%d %b %Y",           # "23 Feb 1998"
        "%Y-%m-%dT%H:%M:%S",  # "2005-07-14T13:45:30"
        "%Y-%m-%dT%H:%M:%SZ", # "2005-07-14T13:45:30Z"
        "%Y-%m-%d %H:%M:%S"   # "2005-07-14 13:45:30"
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            # Fill in missing components manually
            if fmt == "%Y":
                return datetime(dt.year, 1, 1).date()
            elif fmt == "%Y-%m":
                return datetime(dt.year, dt.month, 1).date()
            else:
                return dt.date()
        except ValueError:
            continue

    # Fallback: try partial ISO dates like "1984-1"
    try:
        parts = re.split(r'[-./]', date_str)
        year = int(parts[0])
        month = int(parts[1]) if len(parts) > 1 else 1
        day = int(parts[2]) if len(parts) > 2 else 1
        return datetime(year, month, day).date()
    except Exception:
        return None

def extract_artist_info(tags):
    """
    Returns a list of tuples (artist_id, artist_name)
    """
    artist_ids = tags['musicbrainz_artistid']

    # Identify which key contains the artist name (might not all be present), 
    # we also need to be able to match it to an id.
    if 'artist' in tags and len(artist_ids) == len(tags['artist']):
        artist_key = 'artist'
    elif 'artists' in tags and len(artist_ids) == len(tags['artists']):
        artist_key = 'artists'
    elif 'albumartist' in tags and len(artist_ids) == len(tags['albumartist']):
        artist_key = 'albumartist'
    else:
        raise KeyError("No artist key found")
    
    artists = []

    # Keep track of all artists inside an index
    for idx, artist_id in enumerate(artist_ids):
        # Some tracks have artist ID given as "uuid1/uuid2", we don't need this level of detail
        artist_id = re.split(r'[;/,\s]+', artist_id)[0]

        artists.append((artist_id, tags[artist_key][idx]))
    
    return artists


def extract_album_info(tags):
    # Date parsing, look through multiple fields to increase chances of finding a valid date
    date = tags.get('date', [None])[0]
    originaldate = tags.get('originaldate', [None])[0]

    release_date = parse_flexible_date(originaldate)
    if not release_date:
        release_date = parse_flexible_date(date)

    if not release_date:
        global invalid_date_count
        invalid_date_count += 1
        raise ValueError(f"Missing or invalid date on track: {tags.get('artist', [None])[0]} - {tags.get('title', [None])[0]}, values: {date}, {originaldate}")
    
    # Return (album_id, album_name, release_date)
    return (tags['musicbrainz_albumid'][0], tags.get('album', [None])[0], release_date)

def extract_data_from_json(filepath):
    """
    Returns a dict with values for corresponding audio features from the AcousticBrainz dataset.
    """
    with open(filepath, 'r') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            print("Bad JSON:", filepath)
            return None

        highlevel = data.get('highlevel') or {}
        metadata = data.get('metadata') or {}
        tags = metadata.get('tags') or {}

        try:
            # Create a new track entry using the data from JSON
            track = Track(
                # Required metadata
                musicbrainz_recordingid=tags['musicbrainz_recordingid'][0],
                title=tags['title'][0],
                duration=metadata['audio_properties']['length'],
                # High-level features
                genre=highlevel['genre_dortmund']['value'],
                danceability=highlevel['danceability']['all']['danceable'],
                aggressiveness=highlevel['mood_aggressive']['all']['aggressive'],
                happiness=highlevel['mood_happy']['all']['happy'],
                sadness=highlevel['mood_sad']['all']['sad'],
                relaxedness=highlevel['mood_relaxed']['all']['relaxed'],
                partyness=highlevel['mood_party']['all']['party'],
                acousticness=highlevel['mood_acoustic']['all']['acoustic'],
                electronicness=highlevel['mood_electronic']['all']['electronic'],
                instrumentalness=highlevel['voice_instrumental']['all']['instrumental'],
                tonality=highlevel['tonal_atonal']['all']['tonal'],
                brightness=highlevel['timbre']['all']['bright'],
            )

            artist_pairs  = extract_artist_info(tags=tags)
            album_info = extract_album_info(tags=tags)
            # Return track info along with associated artists (id, name)
            return track, artist_pairs, album_info
    
        except (KeyError, IndexError, TypeError) as ex:
            print(f'Missing data in file ({ex}): {os.path.normpath(filepath)}')
            global missing_data_count
            missing_data_count += 1
            return None

def process_file(json_path):
    """
    Utility function for loading and parsing JSON files in parallel
    """
    try:
        return extract_data_from_json(json_path)
    except Exception as ex:
        print(f'Could not process file ({ex}): {os.path.normpath(json_path)}')
        return None

# %%
#highlevel_path = 'highlevel/'
highlevel_path = 'sample/'
#highlevel_path = 'sample/acousticbrainz-highlevel-sample-json-20220623-0/acousticbrainz-highlevel-sample-json-20220623/highlevel/00/0/'

json_paths = []

# walks through a branch of the directory tree, it will look at all subfolders and files recursively
for root, dirs, files in os.walk(highlevel_path):
    for name in files:
        if name.lower().endswith(".json"):
            json_paths.append(os.path.join(root, name))
        else:
            print(f"Non-JSON file skipped: {name}")

# Clean old records
AlbumArtist.objects.all().delete()
Album.objects.all().delete()
TrackArtist.objects.all().delete()
Track.objects.all().delete()
Artist.objects.all().delete()


# %%

start = time.time()

#json_paths = json_paths[0:1000]
print(f"Will load {len(json_paths)} records")

album_index = {} # keep track of unique album names, indexed by MBID
artist_index = {} # keep track of unique artist names, indexed by MBID
track_index = {} # keep track of unique track data, indexed by MBID
trackartist_set = set() # set of all Track-Artist M2M pairings, to avoid duplication
albumartist_set = set() # set of all Album-Artist M2M pairings

# cpu_threads = os.cpu_count() or 4
# max_workers = cpu_threads * 2
with ThreadPoolExecutor(max_workers=8) as executor:
    # TODO: To safely process the full 30M dataset on 16GB RAM, break JSON loading and inserts into smaller chunks
    # e.g. process 5–10 million files at a time to avoid memory exhaustion.

    futures = [executor.submit(process_file, path) for path in json_paths]
    for future in futures:
        result = future.result()
        if not result:
            continue

        track, artist_pairs, album_info = result
        track_id = track.musicbrainz_recordingid

        # Use a hashmap to check if the track has been already added (from another submission), 
        # only load it if that submission failed (missing data)
        if track_id not in track_index or track_index[track_id] is None:
            track_index[track_id] = track
        else:
            duplicate_count += 1
            continue

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
            
            track.album = album_index[album_id]
            albumartist_set.add((album_id, artist_id))
            


track_list = list(track_index.values())
end = time.time()
print(f"Finished loading records into memory in {end - start:.2f}s, now running the ORM inserts.")
print(f"Found {duplicate_count} duplicate submissions.")
print(f"Found {invalid_date_count} submissions with invalid dates.")
print(f"Found {missing_data_count} submissions with missing data.")

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
    trackartist_list.append(TrackArtist(artist=artist_index[artist_id], track=track_index[track_id]))
TrackArtist.objects.bulk_create(trackartist_list)

albumartist_list = []
for album_id, artist_id in albumartist_list:
    albumartist_list.append(AlbumArtist(artist=artist_index[artist_id], album=album_index[album_id]))
AlbumArtist.objects.bulk_create(albumartist_list)
print(f"Inserted M2M pairing for TrackArtist and AlbumArtist in {end - start:.2f} seconds")
end = time.time()

print("DONE")


