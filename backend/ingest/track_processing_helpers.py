import re, os, orjson, json, tarfile, uuid
import numpy as np
import zstandard as zstd
from collections import Counter, defaultdict
from datetime import datetime, date
from statistics import median_low
from typing import NamedTuple

mute_logs = False
invalid_date_count = 0
missing_data_count = 0

# Columns of multi-value features, we want to ensure same order is used when they're processed
# For moods_mirex
MIREX_ORDER = ["Cluster1", "Cluster2", "Cluster3", "Cluster4", "Cluster5"]

MBID_REGEX = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

MIN_YEAR = 1000

# Fields that are audio features, stored in a Numpy array
FEATURE_FIELDS = [
    "danceability", "aggressiveness", "happiness", "sadness", "relaxedness", "partyness", 
    "acousticness", "electronicness", "instrumentalness", "tonality", "brightness",
]
FEATURE_INDEX = {name: i for i, name in enumerate(FEATURE_FIELDS)}


class AlbumInfo(NamedTuple):
    album_id: str | None
    album_name: str | None
    release_date: str | None


def is_mbid(s: str) -> bool:
    """
    Check if a string is a valid 36 character MBID
    Link: https://musicbrainz.org/doc/MusicBrainz_Identifier
    """
    if not s or not isinstance(s, str):
        return False

    mbid_string = s.strip()
    if not MBID_REGEX.match(mbid_string):
        return False
    try:
        # raises ValueError if not valid hex
        uuid.UUID(mbid_string)
        return True
    except ValueError:
        return False


def log(message: str) -> None:
    global mute_logs

    if not mute_logs:
        print(message)


def parse_flexible_date(date_str: str = None) -> str | None:
    """
    Given a date as a string, try to extract its information as a ISO date string
    """
    if not date_str or not isinstance(date_str, str):
        return None

    date_str = date_str.strip().lower()

    # Clean common invalid formats
    if date_str.startswith(("0000", "0001")) or "00-00" in date_str:
        return None

    # Remove ordinal suffixes: 1st, 2nd, 3rd, 23rd, etc.
    date_str = re.sub(r"(\d{1,2})(st|nd|rd|th)", r"\1", date_str)

    # Remove "of" (e.g. "23 of February" to "23 February")
    date_str = re.sub(r"\bof\b", "", date_str)

    # Remove extra commas and fix spacing
    date_str = re.sub(r",", "", date_str)
    date_str = re.sub(r"\s+", " ", date_str).strip()

    formats = [
        "%Y-%m-%d",  # "2005-07-14"
        "%Y-%m",  # "2005-07"
        "%Y",  # "2005"
        "%Y.%m.%d",  # "2000.06.21"
        "%d %B %Y",  # "23 February 1998"
        "%d %b %Y",  # "23 Feb 1998"
        "%Y-%m-%dT%H:%M:%S",  # "2005-07-14T13:45:30"
        "%Y-%m-%dT%H:%M:%SZ",  # "2005-07-14T13:45:30Z"
        "%Y-%m-%d %H:%M:%S",  # "2005-07-14 13:45:30"
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            if dt.year < MIN_YEAR:
                return None

            # Fill in missing components manually
            if fmt == "%Y":
                return datetime(dt.year, 1, 1).date().isoformat()
            elif fmt == "%Y-%m":
                return datetime(dt.year, dt.month, 1).date().isoformat()
            else:
                return dt.date().isoformat()
        except ValueError:
            continue

    # Fallback: try partial ISO dates like "1984-1"
    try:
        parts = re.split(r"[-./]", date_str)
        year = int(parts[0])
        month = int(parts[1]) if len(parts) > 1 else 1
        day = int(parts[2]) if len(parts) > 2 else 1

        if year < MIN_YEAR:
            return None

        return datetime(year, month, day).date().isoformat()
    except Exception:
        return None


def extract_artist_info(tags: dict) -> list[tuple[str, str]]:
    """
    Returns a list of tuples (artist_id, artist_name)
    """
    artist_ids = tags.get("musicbrainz_artistid", None)
    if not artist_ids:
        return []

    # Identify which key contains the artist name (might not all be present),
    # we also need to be able to match it to an id.
    if "artist" in tags and len(artist_ids) == len(tags["artist"]):
        artist_key = "artist"
    elif "artists" in tags and len(artist_ids) == len(tags["artists"]):
        artist_key = "artists"
    else:
        return []
    
    if len(artist_ids) != len(tags[artist_key]):
        return []

    artists = []
    # Keep track of all artists inside an index
    for idx, artist_id in enumerate(artist_ids):
        artist_id = artist_id.strip()
        if is_mbid(artist_id):
            artists.append((artist_id, tags[artist_key][idx]))

    return artists


def extract_album_info(tags: dict) -> AlbumInfo | None:
    """
    Returns a tuple (album_id, album_name, release_date)
    """
    global invalid_date_count
    album_id = tags.get("musicbrainz_albumid", [None])[0]
    album_name = tags.get("album", [None])[0]

    # Date parsing, look through multiple fields to increase chances of finding a valid date
    date = tags.get("date", [None])[0]
    originaldate = tags.get("originaldate", [None])[0]

    release_date = parse_flexible_date(originaldate)
    if not release_date:
        release_date = parse_flexible_date(date)

    if not release_date:
        invalid_date_count += 1

    if not (album_id and is_mbid(album_id)) and not album_name and not release_date:
        return None

    return (album_id if is_mbid(album_id) else None, album_name, release_date)


def extract_prob_vector(highlevel: dict, parent_key: str, order: list[str]) -> list[float]:
    """
    Extracts and normalizes a probability vector from a nested dict.
    - highlevel: source dictionary
    - parent_key: key in highlevel containing the sub-dict
    - order: list of keys specifying the output order
    """
    all = (highlevel or {}).get(parent_key, {})
    probs = (all.get("all") or {})
    vec = [float(probs.get(key, 0.0)) for key in order]
    s = sum(vec)
    return [x / s for x in vec] if s > 0 else vec

# Stores extracted track information, more memory efficient than using a dict
class TrackInfo:
    __slots__ = ['album_info', 'artist_pairs', 'duration', 'genre_dortmund', 'genre_rosamerica', 
                 'moods_mirex', 'musicbrainz_recordingid', 'numeric_features', 'title', 'submissions']
    def __init__(self, album_info: AlbumInfo | None,
                 artist_pairs: list[tuple[str, str]],
                 duration: float,
                 genre_dortmund: str,
                 genre_rosamerica: str,
                 moods_mirex: np.ndarray,
                 musicbrainz_recordingid: bytes,
                 numeric_features: np.ndarray,
                 title: str,
                 submissions: int = 0) -> None:
        self.album_info = album_info
        self.artist_pairs = artist_pairs
        self.duration = duration
        self.genre_dortmund = genre_dortmund
        self.genre_rosamerica = genre_rosamerica
        self.moods_mirex = moods_mirex
        self.musicbrainz_recordingid = musicbrainz_recordingid
        self.numeric_features = numeric_features
        self.title = title
        self.submissions = submissions

def extract_data_from_json_str(json_str: str, file_path: str | None = None) -> TrackInfo | None:
    """
    Returns a TrackInfo class containing:
    metadata - musicbrainz_recordingid, title, duration, etc.
    high-level features - danceability, aggressiveness, etc.
    artist_pairs - a list of tuples (artist_id, artist_name), the artists for the track
    album_info - a list of tuples (album_id, album_name, release_date), the album the track is on
    """
    global missing_data_count

    try:
        data = orjson.loads(json_str)
    except orjson.JSONDecodeError:
        log(f"Bad JSON string")
        missing_data_count += 1
        return None

    highlevel = data.get("highlevel") or {}
    metadata = data.get("metadata") or {}
    tags = metadata.get("tags") or {}

    try:
        mbid = tags.get("musicbrainz_recordingid", [None])[0]
        if not mbid:
            raise ValueError(f"missing musicbrainz_recordingid")
        elif not is_mbid(mbid):
            raise ValueError(f"bad MBID: {mbid}")
        
        # TODO: Strip leading and trailing single/double quotes
        title = tags.get("title", [None])[0]
        if not title:
            raise ValueError("missing title")

        # High-level features     
        numeric_values = [
            float(highlevel["danceability"]["all"]["danceable"]),
            float(highlevel["mood_aggressive"]["all"]["aggressive"]),
            float(highlevel["mood_happy"]["all"]["happy"]),
            float(highlevel["mood_sad"]["all"]["sad"]),
            float(highlevel["mood_relaxed"]["all"]["relaxed"]),
            float(highlevel["mood_party"]["all"]["party"]),
            float(highlevel["mood_acoustic"]["all"]["acoustic"]),
            float(highlevel["mood_electronic"]["all"]["electronic"]),
            float(highlevel["voice_instrumental"]["all"]["instrumental"]),
            float(highlevel["tonal_atonal"]["all"]["tonal"]),
            float(highlevel["timbre"]["all"]["bright"]),
        ]
        numeric_features = np.array(numeric_values, dtype=np.float32)
        moods_mirex = np.asarray(
            extract_prob_vector(highlevel, "moods_mirex", MIREX_ORDER),
            dtype=np.float32
        )
        
        # Create a new track entry using the data from JSON
        return TrackInfo(
            # Associate artists and album with the track
            album_info = extract_album_info(tags=tags),
            artist_pairs = extract_artist_info(tags=tags),
            # Required metadata
            musicbrainz_recordingid = uuid.UUID(mbid).bytes,
            title = title,
            duration = np.float32(metadata["audio_properties"]["length"] or np.nan),
            # TODO: Store these as references to an enum instead of strings since we're 
            # dealing with a small subset of values.
            genre_dortmund = highlevel["genre_dortmund"]["value"],
            genre_rosamerica = highlevel["genre_rosamerica"]["value"],
            numeric_features = numeric_features,
            moods_mirex = moods_mirex
        )

    except (KeyError, IndexError, TypeError, ValueError) as ex:
        if file_path:
            log(f"Missing data in JSON string ({ex}), path: {os.path.normpath(file_path)}")
        else:
            log(f"Missing data in JSON string ({ex})")
        missing_data_count += 1
        return None


def merge_album_info(tracks: list[TrackInfo]) -> tuple[str, str, str] | None:
    """
    Given a list of duplicate tracks, merge album information by selecting most representative values:
    1) Pick the most common `album_id` across duplicates.
    2) Among entries with that `album_id`, pick most common name.
    3) For date, pick the median date (robust to outliers).

    `tracks: list[dict]` where each dict has `"album_info": (album_id, album_name, release_date)`

    Returns: (album_id, album_name, release_date) or None
    """
    id_counter = Counter()
    name_counter = defaultdict(list)
    date_counter = defaultdict(list)

    for track in tracks:
        album = getattr(track, "album_info", None)
        if not album:
            continue

        album_id, album_name, release_date = album
        if album_id:
            id_counter[album_id] += 1
        if album_name:
            name_counter[album_id].append(album_name)
        if release_date:
            date_counter[album_id].append(release_date)
    
    if not id_counter:
        return None

    best_id = id_counter.most_common(1)[0][0]
    best_name = Counter(name_counter[best_id]).most_common(1)[0][0] if name_counter[best_id] else None
    best_date = median_low(date_counter[best_id]) if date_counter[best_id] else None

    if not best_id or not best_name or not best_date:
        raise ValueError(f"Missing data during merge {best_id}, {best_name}, {best_date}")

    return (best_id, best_name, best_date)


def merge_artist_pairs(tracks: list[TrackInfo]) -> list[tuple[str, str]]:
    """
    Given a list of duplicate tracks, extract a list of tuples from each (artist_id, artist_name) 
    and merge the tracks by selecting the most common tuple combination.
    """
    # Count each unique, sorted artist pair combination
    pair_counter = Counter()
    for track in tracks:
        artist_pairs = getattr(track, "artist_pairs", None)
        if artist_pairs:
            artist_pairs_sorted = tuple(sorted(artist_pairs, key=lambda tup: tup[0]))
            pair_counter[artist_pairs_sorted] += 1

    if not pair_counter:
        return []

    # Get the most common artist pair combination
    most_common_pair, _ = pair_counter.most_common(1)[0]
    return list(most_common_pair)


def merge_distribution(tracks: list[TrackInfo], key: str) -> np.ndarray:
    """
    Merge duplicate distributions (e.g. moods_mirex).
    Assumes all vectors under `key` have the same length.
    """
    vecs = [getattr(t, key) for t in tracks if getattr(t, key, None) is not None]
    if not vecs:
        return np.array([])

    # Stack and average using numpy
    arr = np.stack(vecs)
    merged = np.mean(arr, axis=0)

    s = np.sum(merged)
    return merged / s if s > 0 else merged


def process_file(json_path: str) -> TrackInfo | None:
    """
    Utility function for loading and parsing individual JSON files in parallel
    """
    try:
        with open(json_path, "rb") as f:
            json_string = f.read()
        return extract_data_from_json_str(json_string, json_path)
    except Exception as ex:
        log(f"Could not process file ({ex}): {os.path.normpath(json_path)}")
        return None


def stream_json_from_tar_zst(path: str, read_size=2*1024*1024):
    dctx = zstd.ZstdDecompressor()
    with open(path, "rb") as f:
        with dctx.stream_reader(f, read_size=read_size) as stream:
            with tarfile.open(fileobj=stream, mode="r|*") as tar:
                for member in tar:
                    if not (member.isfile() and member.name.endswith(".json")):
                        continue
                    try:
                        fileobj = tar.extractfile(member)
                        if not fileobj:
                            log(f"[WARN] Skipping {member.name}")
                            continue
                        with fileobj:
                            data = fileobj.read().decode("utf-8", errors="replace")
                            yield member.name, data
                    except Exception as e:
                        log(f"[WARN] Failed {member.name}: {e}")                  

def iter_archive(archive_path: str):
    print(f"Loading {archive_path}", flush=True)
    for filename, raw_json in stream_json_from_tar_zst(archive_path):
        result = extract_data_from_json_str(raw_json, filename)
        if result:
            yield result
            