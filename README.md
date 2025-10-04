# TasteMender: A stateless music recommendation API
> Created as a final project for UoL BScCS (CM3070) by Valentin Radulescu

> [!IMPORTANT]
> After the 22nd of September 2025 development will move to the [`dev`](https://github.com/RadValentin/CM3070-FP-Music-Recommendation/tree/dev) branch.

## Installation

1. Install required software: `Python@3.12.4`, `PostgreSQL@17.6`, `Node.js@v20.17.0 `

2. Create a config file in `backend/.env` with DB login information, see `.env.example`

3. Build the DB (see below)

4. Install Django dependencies, check that everything is running:
```bash
cd backend/
pip install -r requirements.txt
python manage.py migrate
python manage.py test
python manage.py runserver
```

5. Install React dependencies:
```bash
cd frontend/
npm install
npm run dev
```

## Building the database from scratch
Ideally you should have access to the already-built database in SQLite format and the features NPZ file. If this isn't the case you can replicate the DB from scratch using the instructions below. For development, the **sample** data should be enough.

The first step is to download the dataset dumps from AcousticBrainz, these contain track metadata and the audio features used to determine song similarity, link: https://acousticbrainz.org/download. I recommend using a structure like this:

- `AcousticBrainz`
  - `Sample`
    - `acousticbrainz-highlevel-sample-json-20220623-0.tar.zst`
  - `High-Level`
    - `acousticbrainz-highlevel-json-20220623-0.tar.zst`
    - `acousticbrainz-highlevel-json-20220623-1.tar.zst`
    - `...`

You download the datasets from a browser or by using these commands:

```bash
# Sample DB dump with 100k entries, good for development
mkdir Sample
cd Sample
wget -P . https://data.metabrainz.org/pub/musicbrainz/acousticbrainz/dumps/acousticbrainz-sample-json-20220623/acousticbrainz-highlevel-sample-json-20220623-0.tar.zst

# Full DB dump with 30M entries, good for production
mkdir High-level
cd High-level
wget -r -np -nH --cut-dirs=5 -P . https://data.metabrainz.org/pub/musicbrainz/acousticbrainz/dumps/acousticbrainz-highlevel-json-20220623/

# Check that the downloaded files aren't corrupted
sha256sum -c sha256sums
```

Then update the project's `.env` file with the paths to the dumps, ex:

```bash
AB_HIGHLEVEL_ROOT=D:/Datasets/AcousticBrainz/High-level
AB_SAMPLE_ROOT=D:/Datasets/AcousticBrainz/Sample
```

Finally you can now build the SQLite database and the features file (`features_and_index.npz`):

```bash
# Build the Django DB and the in-memory vector store for audio features
python manage.py build_db # Use all available parts of dataset OR
python manage.py build_db --parts 2 # Use 2 parts of dataset OR
python manage.py build_db --sample # Use the sample dataset with 100k entries
```

## Repo Structure

- `backend/`
  - `music_recommendation/` - the main Django project
  - `recommend_api/` - recommendation API
    - `services/`
      - `recommender.py` - recommendation logic
      - `youtube_sources.py` - gets playable sources for tracks
    - `tests/` - unit tests
    - `api.py` - endpoint views
  - `ingest/` - scripts for building the DB
    - `management/commands/`
      - `build_db.py` - dataset ingest and DB build command
      - `recommend.py` - command for showing recommendations
- `frontend/` - standalone app that consumes the API

## How It Works

### Dataset Ingest

Track data is loaded from the [DB dumps](https://acousticbrainz.org/download) of the AcousticBrainz dataset. The build pipeline does the following:

1. Stream JSON data from `.tar.zst` archives, processing the archives in parallel
1. Extract relevant information from each file (title, audio features, metadata), discarding those that have missing or invalid data
1. Build a hashmap (`track_index`) of duplicate tracks indexed by their MusicBrainz ID (`musicbrainz_recordingid`)
1. Merge duplicates into a single entry by selecting the most common value for each field (title, audio features, metadata)
1. Build the DB models:
  1. `Track` from `track_index`
  1. `Artist`, `Album` and M2M pairings (`AlbumArtist`, `TrackArtist`) from the track metadata
1. Extract audio features to a separate file (`features_and_index.npz`), this will be loaded into memory by the Django app to allow for fast searching

Because many popular tracks are duplicated in the dataset, the final number of tracks that the app will be working with is considerably lower than what was ingested.

$$finalSize = datasetSize - duplicateCount - tracksMissingData - tracksMissingArtist$$

For the sample dataset (100k tracks), 85732 unique entries will be loaded:
$$85732 = 100000 - 11182 - 4 - 3082$$