# %% [markdown]
# # AcousticBrainz High-Level Sample Data Processing for Music Recommendation System
# 
# ## Goals
# - [x] Iterate through all track files in the high-level sample
# - [x] Extract MusicBrainz ID, metadata, audio features to a dict
# - [ ] Map the dict to SQL (we'll add Django ORM later)
# 
# > The code assumes you have downloaded the AcousticBrainz DB dumps in the same directory, under `acousticbrainz-highlevel-sample-json-20220623-0/highlevel/`. They can be downloaded from here: https://acousticbrainz.org/download

# %%
import io
import os
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

from recommend_api.models import Track

# %%

def parse_flexible_date(date_str):
    """
    Given a date as a string, try to extract its information as a datetime object
    """
    if not date_str or not isinstance(date_str, str):
        return None

    date_str = date_str.strip()

    # Clean common invalid formats
    if date_str.startswith("0000") or "00-00" in date_str:
        return None

    formats = [
        "%Y-%m-%d", 
        "%Y-%m", 
        "%Y", 
        "%Y-%m-%dT%H:%M:%S", 
        "%Y-%m-%dT%H:%M:%SZ", 
        "%Y-%m-%d %H:%M:%S"
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
        parts = date_str.split("-")
        year = int(parts[0])
        month = int(parts[1]) if len(parts) > 1 else 1
        day = int(parts[2]) if len(parts) > 2 else 1
        return datetime(year, month, day).date()
    except Exception:
        return None

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

        artist = tags.get('artist', [None])[0]
        title = tags.get('title', [None])[0]

        release_date = parse_flexible_date(tags.get('originaldate', [None])[0])
        if not release_date:
            release_date = parse_flexible_date(tags.get('date', [None])[0])

        if not release_date:
            print(f"Missing or invalid date on track: {artist} - {title}, values: {tags.get('date', [None])[0]}, {tags.get('originaldate', [None])[0]}")
            return None

        try:
            # Required metadata
            album = tags['album'][0]
            duration = metadata['audio_properties']['length']

            # High-level features
            genre = highlevel['genre_dortmund']['value']
            danceability = highlevel['danceability']['all']['danceable']
            aggressiveness = highlevel['mood_aggressive']['all']['aggressive']
            happiness = highlevel['mood_happy']['all']['happy']
            sadness = highlevel['mood_sad']['all']['sad']
            relaxedness = highlevel['mood_relaxed']['all']['relaxed']
            partyness = highlevel['mood_party']['all']['party']
            acousticness = highlevel['mood_acoustic']['all']['acoustic']
            electronicness = highlevel['mood_electronic']['all']['electronic']
            instrumentalness = highlevel['voice_instrumental']['all']['instrumental']
            tonality = highlevel['tonal_atonal']['all']['tonal']
            brightness = highlevel['timbre']['all']['bright']
        except (KeyError, IndexError, TypeError):
            print(f'missing data in file: {filepath}')
            return None

        return Track(
            artist=artist,
            album=album,
            title=title,
            release_date=release_date,
            duration=duration,
            genre=genre,
            danceability=danceability,
            aggressiveness=aggressiveness,
            happiness=happiness,
            sadness=sadness,
            relaxedness=relaxedness,
            partyness=partyness,
            acousticness=acousticness,
            electronicness=electronicness,
            instrumentalness=instrumentalness,
            tonality=tonality,
            brightness=brightness,
        )

def process_file(json_path):
    """
    Utility function for loading and parsing JSON files in parallel
    """
    record = extract_data_from_json(json_path)
    if record is not None:
        # Extract the ID portion (before the last '-') to group submissions
        basename = os.path.basename(json_path)
        track_id = '-'.join(basename.split('-')[:-1])
        return (track_id, record)
    return None

# %%
#highlevel_path = 'acousticbrainz-highlevel-sample-json-20220623/highlevel/'
highlevel_path = 'acousticbrainz-highlevel-json-20220623/highlevel/'


# test = extract_data_from_json(os.path.join(highlevel_path, '00', '0', '000a9db8-949f-4fa2-9f40-856127df0dbc-0.json'))
# pprint(test)

json_paths = []

# walks through a branch of the directory tree, it will look at all subfolders and files recursively
for root, dirs, files in os.walk(highlevel_path):
    for name in files:
        json_paths.append(os.path.join(root, name))

# Clean old records
Track.objects.all().delete()


# %%

start = time.time()

#json_paths = json_paths[0:1000]
print(f"Will load {len(json_paths)} records")

unique_records = {}
# cpu_threads = os.cpu_count() or 4
# max_workers = cpu_threads * 2
with ThreadPoolExecutor(max_workers=8) as executor:
    # TODO: To safely process the full 30M dataset on 16GB RAM, break JSON loading and inserts into smaller chunks
    # e.g. process 5–10 million files at a time to avoid memory exhaustion.

    futures = [executor.submit(process_file, path) for path in json_paths]
    for future in futures:
        result = future.result()
        if result:
            track_id, record = result
            # Use a hashmap to check if the track has been already added (from another submission), 
            # only load it if that submission failed (missing data)
            if track_id not in unique_records or unique_records[track_id] is None:
                unique_records[track_id] = record

records = list(unique_records.values())
end = time.time()
print(f"Finished loading records into memory in {end - start:.2f}s, now running the ORM inserts.")


start = time.time()
batch_size = 2000

for i in range(0, len(records), batch_size):
    print(f'{i}/{len(records)} processed')
    start_batch = time.time()
    Track.objects.bulk_create(records[i:i+batch_size])
    print(f'Batch took {time.time() - start_batch:.2f} seconds')

end = time.time()
print(f"Inserted {len(records)} records in {end - start:.2f} seconds")

print("DONE")


