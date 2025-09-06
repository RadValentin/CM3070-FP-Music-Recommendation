# Progress Log

### 09 June 2025 
- Drafted a simple development plan
- Went through Week 3 materials
### 11 June 2025
- Write preliminary report: Introduction, Validation
### 13 June 2025
- Find basic dataset for use in prototype
- Format data and load it into DB
- Extract features (TF-IDF) to use for checking if songs are similar
### 14 June 2025
- Optimize data storage so it's performant enough to demo (remove bottlenecks)
- Create basic API for retrieving song details and song recommendations
### 15 June 2025
- Wrote simple report section on prototype
### 16 June 2025
- Finalized report section on prototype development
- Submitted preliminary report
### 17 July 2025
- Sketch out a rough development plan and create a few Github issues for the 1st week work
### 18 July 2025
- Research online datasets that contain pre-extracted audio features
- Research how Spotify does recommendations
### 19 July 2025
- Load the AcousticBrainz data into SQLite through a Python script so it can be easily queried
### 21 - 27 July 2025
- VACATION
### 28 July
- Optimize data processing script to skip duplicate entries
- Research ISMIR and recommender systems
### 29 July
- Research ISMIR and recommender systems
### 30 July
- TODO: Read `A Historical Survey of Music Recommendation Systems - Towards Evaluation.pdf`
### 11 August
- Normalize database by extracting Artist and Album information from Tracks to their own models
### 12 August
- Store information about high-level features (acousticness, danceability) in vector files instead of in the DB
- Implement a script that makes recommendations based on the cosine similarity of audio features
- Notice that tracks are tagged imprecisely when it comes to genre(eg. Metallica tagged as electronic music)
- Genre and decade prefiltering will be needed to increase accuracy
### 13 August
- Update the DB build script so that for tracks that have duplicates we select the most common values for genre and high-level features instead defaulting to the 1st submission and discarding the rest.
### 19 August
- Refine recommendation logic: pre-filter candidate tracks to be same genre and decade as target track, avoid duplicated tracks
### 20 August
- Decrease DB build time by 64 seconds (17% improvement) by using `orjson` package instead of native json to parse the dataset record files
### 21 August
- Begin API development, add endpoint for track details `api/track/<str:musicbrainz_recordingid>/`
- Extract recommendation logic to a separate module
### 22 August
- Add tests for recommendation logic
- Add endpoint for making recommendations `api/similar/`
### 23 August
- Add tests for recommendation endpoint
### 03 September
- Iron out data processing:
  - Add script for compiling many JSON files into one NDJSON to speed up data ingest process by reducing file open/close overhead. Dataset load time time went from 33s to 29s for 100k records (it's going to matter for 30M records).
  - Update DB build script to accept either path to JSON files or path to merged NDJSON (split into multiple functions if needed), store paths in some sort of `.env` file
  - Refactor scripts as Django commands: merging JSON files (`python manage.py merge_json`), building db (`python manage.py build_db`), showing recommendation in console (`python manage.py recommend`)
- Ensure metadata correctness: when processing the MBID must match a standard format (regex)
### 04 September
- Select most common values for album and artists when merging tracks, previously we were populating these fields with the values from the first encountered instance of a track.
- Track how many duplicates each track has and store in DB under `submissions` in `Track` model.
### 05 September
- Modify how data is loaded into the DB:
  - Data is read directly from the dump archives (`.tar.zst` format)
  - Archives are processed in parallel as separate tasks (futures) `ThreadPoolExecutor > process_archive`
  - Inside each thread, the archive is decompressed and its contained JSON files are streamed and processed sequentially (relevant data is extracted from JSON files)
  - As each future completes, it creates a list of processed tracks which can be further processed in subsequent phases of the pipeline
- Streaming the data removes the need to unzip the archives manually. We also don't need to worry about file access bottlenecks and don't need to merge the millions of JSON files into NDJSONs.


## Final Stretch Plan

### 06 September
- Design API
- Document development in report
- Document literature review

### Second-to-last week
- Implement search endpoint
- Begin developing front-end to consume API: search and recommend
- 1 day for report writing
- Rest spent on API and front-end
- Data exploration: genre distribution, popular tracks, popular artists
- Include popularity as a way of ranking results

### Last week
- Polish implementation
- Finalize report