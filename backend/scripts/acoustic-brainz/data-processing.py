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

        # TODO: If artist, title and possibly other fields end up being None, skip and log. 
        # Determine which fields are mandatory.
        return Track(
            # metadata
            artist = artist,
            album= tags.get('album', [None])[0],
            title= title,
            release_date= release_date,
            duration= metadata.get('audio_properties', {}).get('length', None),
            
            # high-level features
            genre= highlevel.get('genre_dortmund', {}).get('value', None),
            danceability= highlevel.get('danceability', {}).get('all', {}).get('danceable', None),
            aggressiveness= highlevel.get('mood_aggressive', {}).get('all', {}).get('aggressive', None),
            happiness= highlevel.get('mood_happy', {}).get('all', {}).get('happy', None),
            sadness= highlevel.get('mood_sad', {}).get('all', {}).get('sad', None),
            relaxedness= highlevel.get('mood_relaxed', {}).get('all', {}).get('relaxed', None),
            partyness= highlevel.get('mood_party', {}).get('all', {}).get('party', None),
            acousticness= highlevel.get('mood_acoustic', {}).get('all', {}).get('acoustic', None),
            electronicness= highlevel.get('mood_electronic', {}).get('all', {}).get('electronic', None),
            instrumentalness= highlevel.get('voice_instrumental', {}).get('all', {}).get('instrumental', None),
            tonality= highlevel.get('tonal_atonal', {}).get('all', {}).get('tonal', None),
            brightness= highlevel.get('timbre', {}).get('all', {}).get('bright', None),
        )

# %%
highlevel_path = 'acousticbrainz-highlevel-json-20220623/highlevel/'


# test = extract_data_from_json(os.path.join(highlevel_path, '00', '0', '000a9db8-949f-4fa2-9f40-856127df0dbc-0.json'))
# pprint(test)

json_paths = []

# walks through a branch of the directory tree, it will look at all subfolders and files recursively
for root, dirs, files in os.walk(highlevel_path):
    for name in files:
        json_paths.append(os.path.join(root, name))

Track.objects.all().delete()


# %%
records = []
start = time.time()

#json_paths = json_paths[0:1000]

print(f"Will load {len(json_paths)} records")

for json_path in json_paths:
    # TODO: Use a hashmap to check if the track has been already added (from another submission), 
    # only load it if that submission failed (missing data)
    record = extract_data_from_json(json_path)

    if record is not None:
        records.append(record)

end = time.time()
print(f"Finished loading records into memory in {end - start:.2f}s, now running the ORM inserts.")

start = time.time()

# TODO: Increase batch size, proportional to dataset size
batch_size = 1000
for i in range(0, len(records), batch_size):
    print(str(i) + '/' + str(len(records)) + ' processed')
    Track.objects.bulk_create(records[i:i+batch_size])

end = time.time()
print(f"Inserted {len(records)} records in {end - start:.2f} seconds")

print("DONE")


