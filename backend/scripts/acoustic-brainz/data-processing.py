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

from recommend_api.models import Track

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

        # Date parsing, look through multiple fields to increase chances of finding a valid date
        date = tags.get('date', [None])[0]
        originaldate = tags.get('originaldate', [None])[0]

        release_date = parse_flexible_date(originaldate)
        if not release_date:
            release_date = parse_flexible_date(date)

        if not release_date:
            print(f"Missing or invalid date on track: {tags.get('artist', [None])[0]} - {tags.get('title', [None])[0]}, values: {date}, {originaldate}")
            global invalid_date_count
            invalid_date_count += 1
            return None

        try:
            # Required metadata
            artist = tags['artist'][0] if 'artist' in tags else tags['artists'][0]
            title = tags['title'][0]
            album = tags.get('album', [None])[0]
            musicbrainz_recordingid = tags['musicbrainz_recordingid'][0]
            duration = metadata['audio_properties']['length']
            country = tags.get('releasecountry', [None])[0]

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
        except (KeyError, IndexError, TypeError) as ex:
            print(f'Missing data in file ({ex}): {filepath}')
            global missing_data_count
            missing_data_count += 1
            return None

        return Track(
            musicbrainz_recordingid=musicbrainz_recordingid,
            artist=artist,
            album=album,
            title=title,
            release_date=release_date,
            duration=duration,
            country=country,
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
highlevel_path = 'highlevel/'
#highlevel_path = 'sample/'
#highlevel_path = 'sample/acousticbrainz-highlevel-sample-json-20220623-0/acousticbrainz-highlevel-sample-json-20220623/highlevel/00/0/'


# test = extract_data_from_json(os.path.join(highlevel_path, '00', '0', '000a9db8-949f-4fa2-9f40-856127df0dbc-0.json'))
# pprint(test)

json_paths = []

# walks through a branch of the directory tree, it will look at all subfolders and files recursively
for root, dirs, files in os.walk(highlevel_path):
    for name in files:
        if name.lower().endswith(".json"):
            json_paths.append(os.path.join(root, name))
        else:
            print(f"Non-json file found: {name}")

# Clean old records
Track.objects.all().delete()


# %%

start = time.time()

#json_paths = json_paths[0:1000]
print(f"Will load {len(json_paths)} records")

unique_records = {}
duplicate_count = 0
invalid_date_count = 0
missing_data_count = 0
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
            else:
                duplicate_count += 1

records = list(unique_records.values())
end = time.time()
print(f"Finished loading records into memory in {end - start:.2f}s, now running the ORM inserts.")
print(f"Found {duplicate_count} duplicate submissions.")
print(f"Found {invalid_date_count} submissions with invalid dates.")
print(f"Found {missing_data_count} submissions with missing data.")

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


