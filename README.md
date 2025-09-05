# TasteMender: A stateless music recommendation API
> Created as a final project for UoL BScCS (CM3070) by Valentin Radulescu

## Installation

```bash
# install dependencies
cd backend/
pip install -r requirements.txt
python manage.py migrate
```

## (Optional) Building the database from scratch
Ideally you should have access to the already-built database in SQLite format and the features NPZ file. If this isn't the case you can replicate the DB from scratch using the instructions below. 

The first step is to download the dataset dumps from AcousticBrainz, these contain the audio features used to determine song similarity, link: https://acousticbrainz.org/download. I recommend unzipping each part into a separate directory using a structure like this:

- `AcousticBrainz`
  - `Sample`
    - `acousticbrainz-highlevel-sample-json-20220623-0`
  - `High-Level`
    - `acousticbrainz-highlevel-json-20220623-0`
    - `acousticbrainz-highlevel-json-20220623-1`
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

# Unzip the archives:
sudo apt install zstd
unzstd acousticbrainz-highlevel-sample-json-20220623-0.tar.zst
```

Then update the project's `.env` file with the paths to the dumps, ex:

```bash
AB_HIGHLEVEL_ROOT=D:/Datasets/AcousticBrainz/High-level
AB_SAMPLE_ROOT=D:/Datasets/AcousticBrainz/Sample
```

Now you can use the management commands in the project to merge all the JSON files into larger NDJSONs which will reduce file access bottlenecks during the DB build process

```bash
cd backend/
# Merge multiple JSON files into one NDJSON to speed up build times
python manage.py merge_json # Merge all available files OR
python manage.py merge_json --parts 2 # Merge only the first 2 parts of dataset OR
python manage.py merge_json --parts_list 5,6 # Merge parts 5 and 6 of the dataset
```

Finally you can now build the DB:

```bash
# Build the Django DB and the in-memory vector store for audio features
python manage.py build_db # Use all available parts of dataset OR
python manage.py build_db --parts 2 # Use 2 parts of dataset OR
python manage.py build_db --sample # Use the sample dataset with 100k entries
```

### TODO: Include data from MusicBrainz if needed

```bash
# Download DB dumps from MusicBrainz, these contain the metadata needed to display infomation about
# artists, tracks, albums, etc. Link: https://metabrainz.org/datasets/download

wget -r -np -nH --cut-dirs=5 -P . https://data.metabrainz.org/pub/musicbrainz/data/fullexport/20250806-001852/

md5sum -c MD5SUMS
```

## Folder Structure

- `backend`
  - `music_recommendation` - the main Django project
  - `recommend_api` - the Django app that provides the music recommendation API and serves the HTML/JS/CSS assets
  - `ingest` - scripts and commands for processing the datasets and building the DB
- `frontend` - assets that are bundled into static assets and served by the `recommend_api` app

## Prototype App

As a placeholder for the final dataset, I used the ["Spotify Million Song Dataset"](https://www.kaggle.com/datasets/notshrirang/spotify-million-song-dataset) licensed under [CC0: Public Domain](https://creativecommons.org/publicdomain/zero/1.0/) from Kaggle.

Prototype user flow:
- User finds the song he likes using the front-end
  - Back-end should support searching for songs by title, returning matches with their IDs
- Dataset is loaded, a machine learning model is trained on it

For 57650 songs it takes 2,85 GB of disk space to store their associated TF-IDF vectors. This is a noticeable increase in storage requirements as the lyrics themselves only take up 71 MB.

Some insights on the vectors themselves:
- Each has a 10k features upper bound
- They're sparsely populated, most values being zero
- They're stored in the DB as raw JSON which will involve some overhead when accessing and processing them
- Saving the data to the DB takes around 10 minutes

Similar songs can be identified by calculating the cosine similarity between the original song's and all other songs TF-IDF vectors. The songs with the highest values (between -1 and 1) will also be closest in terms of their lyrical content.

In order to increase performance I decided to store the vectors as a separate file instead and only keep the song metadata in the DB.

### Notes for project

I've chosen "NextTrack: A music recommendation API" as the template for my project. The main reason is that I find the domain area interesting and it addresses an real shortcoming of current-day music platforms which I often come across. It always happens that I get stuck in a loop of either the same songs or songs I don't enjoy. I think it would be interesting to solve this issue. Plus, I can use the project to demonstrate my web development skills when applying for jobs later on.

## Utilities
- MusicBrainz recording: https://musicbrainz.org/recording/87f40400-1009-4578-991f-421c1ad330eb (Enter Sandman by Metallica)
- AcousticBrainz recording:  https://acousticbrainz.org/2dacc772-bff6-4347-a586-8bff3a7d7c79 (Nothing Else Matters by Metallica)

The recommendation script

Recommendation script output, `python manage.py recommend --mbid 87f40400-1009-4578-991f-421c1ad330eb`
```
diag full: mean=-0.037 std=0.459 p95=0.825 max=0.987
diag prefilter[55022]: mean=0.003 std=0.451 p95=0.841 max=0.987
Vector search (prefilter[55022]) took 0.002s

Tracks similar to: Metallica - All Nightmare Long:
 1. Dominici — King of Terror [5566272d-0e5b-474a-bbd4-474a7ecd0699]  (cos=0.973, final=1.131, year=2008, genre=electronic)
 2. Revocation — Alliance in Tyranny [a22bc7c3-f731-456d-a77c-f80b21c0f3e8]  (cos=0.969, final=1.129, year=2008, genre=electronic)
 3. Manowar — Die for Metal [c7f95302-8ffd-484b-9808-1bc5cd1965c4]  (cos=0.975, final=1.128, year=2007, genre=electronic)
 4. The Faceless — Legion of the Serpent [b028e672-c1c2-4dd2-b2ca-4710f2326b32]  (cos=0.967, final=1.127, year=2008, genre=electronic)
 5. phoenixdk — No Smoking Area (MAP23: Bye Bye American Pie) [cb4bc7ec-bdbd-418e-b633-3edc3351ae79]  (cos=0.967, final=1.127, year=2008, genre=electronic)
 6. モーニング娘。 — 恋のダンスサイト [c81dc45d-11aa-478d-9b00-0454aaf0efe2]  (cos=0.970, final=1.124, year=2007, genre=electronic)
 7. Confusion Is Next — Graffiti [7e193e25-7d71-4ce4-b20f-117549cb5b19]  (cos=0.970, final=1.124, year=2009, genre=electronic)
 8. After Forever — Discord [1be2a709-9249-4685-998f-e5a58333823e]  (cos=0.968, final=1.123, year=2007, genre=electronic)
 9. Indukti — ... And Who's the God Now?! [b34867a9-a764-450a-b5e7-59377771e79a]  (cos=0.966, final=1.121, year=2009, genre=electronic)
10. Lacrimosa — Copycat (extended version) [a2b5a619-fcb4-433b-845e-f8b3b6058bd1]  (cos=0.973, final=1.121, year=2010, genre=electronic)
```

List data about an artist:
```sql
select track.musicbrainz_recordingid, title, artist.name as artist, album.name as album, album.date, genre_rosamerica, genre_dortmund, file_path from recommend_api_track as track
join recommend_api_trackartist as trackartist on trackartist.track_id = track.musicbrainz_recordingid
join recommend_api_artist as artist on trackartist.artist_id = artist.musicbrainz_artistid
join recommend_api_album as album on track.album_id = album.musicbrainz_albumid
where lower(artist.name) like '%metallica%';
```