import re, os, json, sys
from datetime import datetime

mute_logs = False
invalid_date_count = 0
missing_data_count = 0

def log(message):
    global mute_logs
    
    if not mute_logs:
        print(message)

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
    """
    Returns a list of tuples (album_id, album_name, release_date)
    """
    global invalid_date_count
    # Date parsing, look through multiple fields to increase chances of finding a valid date
    date = tags.get('date', [None])[0]
    originaldate = tags.get('originaldate', [None])[0]

    release_date = parse_flexible_date(originaldate)
    if not release_date:
        release_date = parse_flexible_date(date)

    if not release_date:
        invalid_date_count += 1
        raise ValueError(f"Missing or invalid date on track: {tags.get('artist', [None])[0]} - {tags.get('title', [None])[0]}, values: {date}, {originaldate}")
    
    return (tags['musicbrainz_albumid'][0], tags['album'][0], release_date)

def extract_data_from_json(filepath):
    """
    Returns a track dictionary with:
    metadata - musicbrainz_recordingid, title, duration, etc.
    high-level features - danceability, aggressiveness, etc.
    artist_pairs - a list of tuples (artist_id, artist_name), the artists for the track
    album_info - a list of tuples (album_id, album_name, release_date), the album the track is on
    """
    global missing_data_count
    
    with open(filepath, 'r') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            log(f"Bad JSON: {filepath}")
            return None

        highlevel = data.get('highlevel') or {}
        metadata = data.get('metadata') or {}
        tags = metadata.get('tags') or {}

        try:
            # Create a new track entry using the data from JSON
            track = {
                # Required metadata
                "musicbrainz_recordingid": tags['musicbrainz_recordingid'][0],
                "title": tags['title'][0],
                "duration": metadata['audio_properties']['length'],
                "genre_dortmund": highlevel['genre_dortmund']['value'],
                "genre_rosamerica": highlevel['genre_rosamerica']['value'],
                "file_path": os.path.normpath(filepath),
                # High-level features
                "danceability": highlevel['danceability']['all']['danceable'], 
                "aggressiveness": highlevel['mood_aggressive']['all']['aggressive'], 
                "happiness": highlevel['mood_happy']['all']['happy'], 
                "sadness": highlevel['mood_sad']['all']['sad'], 
                "relaxedness": highlevel['mood_relaxed']['all']['relaxed'], 
                "partyness": highlevel['mood_party']['all']['party'], 
                "acousticness": highlevel['mood_acoustic']['all']['acoustic'], 
                "electronicness": highlevel['mood_electronic']['all']['electronic'], 
                "instrumentalness": highlevel['voice_instrumental']['all']['instrumental'], 
                "tonality": highlevel['tonal_atonal']['all']['tonal'], 
                "brightness": highlevel['timbre']['all']['bright'], 
            }

            # Associate artists and album with the track
            track["artist_pairs"]  = extract_artist_info(tags=tags)
            track["album_info"] = extract_album_info(tags=tags)

            return track
    
        except (KeyError, IndexError, TypeError, ValueError) as ex:
            log(f'Missing data in file ({ex}): {os.path.normpath(filepath)}')
            missing_data_count += 1
            return None
        

def process_file(json_path):
    """
    Utility function for loading and parsing JSON files in parallel
    """
    try:
        return extract_data_from_json(json_path)
    except Exception as ex:
        log(f'Could not process file ({ex}): {os.path.normpath(json_path)}')
        return None