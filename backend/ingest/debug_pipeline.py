# mprof run python ingest/debug_pipeline.py --sample
# mprof plot --flame
import os, json, orjson, uuid, shutil
import sys
import django
import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "music_recommendation.settings")
django.setup()

from ingest.pipeline import build_database
from ingest.lmdb_index import LMDBTrackIndex
import ingest.track_processing_helpers as tph

build_database(use_sample=True, show_log=False)

# track = {
#     "album_info": (
#         "25fbfbb4-b1ee-4448-aadf-ae3bc2e2dd27",
#         "The Dark Side of the Moon",
#         "1973-03-24",
#     ),
#     "artist_pairs": [("83d91898-7763-47d7-b03b-b92132375c47", "Pink Floyd")],
#     "musicbrainz_recordingid": "0e11c0fd-a1da-4b88-a438-7ef55c5809ec",
#     "title": "Time",
#     "duration": 426.475097656,
#     "genre_dortmund": "electronic",
#     "genre_rosamerica": "pop",
#     "numeric_features": [
#         0.411618977785,
#         0.0155805181712,
#         0.102452486753,
#         0.382577061653,
#         0.793852508068,
#         0.242396458983,
#         0.182972118258,
#         0.229634702206,
#         0.182331189513,
#         0.0208793897182,
#         0.0957588925958,
#     ],
#     "moods_mirex": [
#         0.0643387297442307,
#         0.06906175716310996,
#         0.38374096727023926,
#         0.08383685475347813,
#         0.3990216910689419,
#     ],
# }

# lmdb_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lmdb_data")

# if os.path.exists(lmdb_dir):
#     shutil.rmtree(lmdb_dir)
# os.makedirs(lmdb_dir, exist_ok=True)
# lmdb_dict = LMDBTrackIndex(lmdb_dir)
# lmdb_dict.append(track["musicbrainz_recordingid"], track)
# lmdb_dict.append(track["musicbrainz_recordingid"], track)
# lmdb_dict.append(track["musicbrainz_recordingid"], track)

# lmdb_dict.flush()

# print("test", lmdb_dict.keys())
# for mbid, tracks in lmdb_dict.items():
#     print(mbid, tracks)

# lmdb_dict.close()