# Music Recommendation System - Report Notes

> This document contains notes which will be used as a basis for a final report on a music recommendation system

## Literature Review

### Recommendation Systems
#### Spotify
Data storage:
- Structured data (tracks, artists, albums) is stored in PostgreSQL relational databases
- Blob storage is used for the audio files
- Audio features are extracted from tracks as vectors and stored in a fast-access systems (Redis, vector databases)

The basic concept of how recommendations are made boils down to comparing vectors:
- Each track has a set of N features, each representing an axis in a vector
- By comparing each pair of vectors and calculating the distance between them we can determine which tracks are similar (smaller distance)
- The main challenge is how to do comparison at scale when dealing with millions of songs, two options are:
  - Annoy (Approximate Nearest Neighbors Oh Yeah) - this is what Spotify uses
  - FAISS (Facebook AI Similarity Search)

### Datasets
#### Million Song Dataset - http://millionsongdataset.com/
- Largely out of date: last release ~2011-2012, full copy of the dataset (~300gb) isn't available for download anymore on the official website
- Provides rich metadata for each track, having 55 fields which cover: tempo, pitch, tags, terms, external identifiers, artist location, release year, etc.

#### Spotify Million Song Dataset - https://www.kaggle.com/datasets/notshrirang/spotify-million-song-dataset
- Dataset hosted on Kaggle, small and simple enough for a proof of concept
- Not enough metadata to do proper matching, only covers: artist, title, lyrics
- At minimum it should be amended with genre and release year

#### FMA (Free Music Archive) - https://github.com/mdeff/fma
- Limited number of songs, ~100k, and out of date with the latest release being in 2017
- Song metadata: extracted audio features (tempo, key loudness, etc.), tags, genre, etc.

#### Spotify API
- Huge selection of tracks accessible through the Spotify Web API which is intended for personal or non-commercial use under their [Developer Terms of Service](https://developer.spotify.com/terms).
- Access is rate limited to ~100 requests per hour according to https://apipark.com/technews/O4zBQwTk.html (unverified), the official documentation doesn't specify an exact number: https://developer.spotify.com/documentation/web-api/concepts/rate-limits. The limits make it difficult to pull in enough data to generate accurate recommendations in real-time.
- Pulling the data in through the server and cacheing it also isn't an option because of the obscene amount of time required to get a large enough dataset (1 year for 1M tracks).

#### Spotify 1 Million Tracks dataset - https://www.kaggle.com/datasets/amitanshjoshi/spotify-1million-tracks
- This dataset, hosted on Kaggle, contains data on 1M tracks that came out between 2000-2023. For each 19 features are recorded: popularity, year, danceability, energy, key, loudness, mode, speechiness, acousticness, instrumentalness, liveness, valence, tempo, time signature, duration.
- The data was collected wind the Spotipy by Amitansh Joshi an licensed under the [Open Database License v1.0](https://opendatacommons.org/licenses/odbl/1-0/).
- The dataset doesn't cover enough decades to appeal to a large audience. It doesn't cover the 80s even though this decade is still relevant in popular culture, for example the Minecraft Movie, Stranger Things, Guardians of the Galaxy all feature 80s tracks.
- The legality of this dataset is unclear. According to the Spotify [Developer Terms of Service](https://developer.spotify.com/terms) the data retrieved from their API can be stored only if it supports the operation of an SDA (Spotify Developer Application), it must also be updated regularly. Hosting a database dump on Kaggle seems to be outside the terms of service. I'm opting to not use this dataset because of the licensing issues.

#### AcousticBrainz - https://acousticbrainz.org/
- Crowd-sourced acoustic information gathered between 2015-2022 for more than 1M tracks from a wide range of decades, 1920s - 2020s.
- The dataset is split into high-level and low-level features (genre, mood, voice/instrumental, danceability, etc.) which could be the basis of determining recommendations based on similarity.
  - High-level dump size: 39 GB (compressed)
  - Low-level dump size: 589 GB (compressed)
- Each track has a MusicBrainz ID which could be used to pull-in additional data through the API
- Minimal metadata is provided in the dumps (album, artist, release date), could be enough to use as a starting point
- Biggest downside is that the project was shut down in 2022 because the feature extraction process they were using was producing [inaccurate data](https://blog.metabrainz.org/2022/02/16/acousticbrainz-making-a-hard-decision-to-end-the-project/). This could affect the quality of the recommendations in a major way. Regardless, there doesn't seem to be another dataset out there which covers as many track and with as much detail, we'll have to risk inaccuracy for the sake of completeness.

- The high level features break down into:
  - Generic audio features: danceability, aggressiveness, happiness, sadness, etc.
  - Genre: 3 genre classifiers, each for a specific subset of genres, `genre_dortmund`, `genre_tzanetakis`, `genre_rosamerica`. The results may conflict.
  - Rhythm - good for detecting dance styles but not applicable to all tracks
- Each feature has:
  - A value (predicted label)
  - A probability (confidence in that label)
  - An all dict (probability for each category the label could belong to)

Other potential data sources: 
  - Discogs - open, user-generated data, 151M tracks, 
  - MusicBrainz - open, 50M tracks
  - [List of online music databases](https://en.wikipedia.org/wiki/List_of_online_music_databases)
  - > Most online databases provide metadata but not audio features

## Development

Repo structure diagram: https://www.mermaidchart.com/app/projects/dc9676ab-4061-43ce-8b7b-18a12bea05b7/diagrams/54cf4afe-1cbc-471e-9b64-e1286174a522/version/v0.1/edit

### Prototype App

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

### Takeaways from prototype
The prototype revealed that relational databases, while optimal for storing track metadata, aren't suitable for storing audio features. The features are usually in the form of vectors and most database systems don't offer support for such a datatype. Having to serialize vectors to strings for storage would significantly bottleneck database operations, the same goes for deserializing the data when it needs to be used in code. A vector DB/index is needed instead: FAISS, Annoy, ScaNN.

Another thing to consider is the complexity of making recommendations. For each song we'd have to compare against every other song to determine similarity which is a $O(N^2)$ problem. For a million records that would require the same number of DB requests to run the comparisons.

### Data Processing
> Note: The performance data was recorded on a system with 16GB DDR3 RAM, Intel 4690k 4-core CPU and SATA-3 SSD.

For the 100k records in the high-level sample dataset:
- Takes 34.79s to read all of the JSON files and build the model objects
- Takes 6.82s to insert the data in the DB
- 1475 records don't have any associated release dates

For 1M records high-level dataset:
- Takes 362s to read all of the JSON files and build the model objects
- Takes 50s to insert the data in the DB, inserts are batched in groups of 2000
- 2029 records don't have any associated release dates
- 3669 records have missing data (title, artist, etc.)
- 297011 records are duplicates
- 697291 records are left at the end to be inserted into the DB
- DB size on disk is 190 MB


The pitfalls of user-generated data:
- some release dates are inconsistently formatted, given as only a year, others in ISO date format, in SQL Datetime format, in ISO 8601 with Zulu (UTC) etc
- popular songs and artists (Nirvana, Beatles) appear frequently
- lots of generic placeholder titles: [untitled], End Credits, Finale, [unknown] for tracks
- character songs from anime or games, ex: `三千院ナギ starring 釘宮理恵`, `綾崎ハヤテ starring 白石涼子`
- keys for artists are given as a string "Jay-Z & Beyonce" while their MBIDs as an array, not clear if the order is maintained, splitting the string might not be valid (maybe band name has & in it, ex: "Earth Wind & Fire"). The track is skipped if not both the artists and their ids are given as arrays.

- > IMPORTANT: I only loaded 1M records and got the times above, need to load ALL 30M records from all archives

#### How AcousticBrainz Gets Its Data
- Volunteers run the Essentia analyzer locally on their audio files (MP3, FLAC, etc.).
- The analyzer extracts low-level audio features (e.g., MFCCs, spectral data) and high-level descriptors (e.g., danceability, mood).
- The results are uploaded to AcousticBrainz along with the song’s MusicBrainz ID (MBID).
- Over time, this crowd-sourced system has built up millions of submissions.

### Building the database

```sql
--Optional commands if DB/USER were created previously
--REVOKE ALL ON SCHEMA public FROM django;
--DROP DATABASE IF EXISTS taste_mender_db;
--DROP USER IF EXISTS django;
CREATE USER django WITH PASSWORD 'password';
CREATE DATABASE taste_mender_db WITH ENCODING 'UTF8' OWNER django;
GRANT ALL PRIVILEGES ON DATABASE taste_mender_db TO django;
GRANT ALL PRIVILEGES ON SCHEMA public TO django;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO django;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO django;

-- Needed for creating a DB when running tests
ALTER USER django CREATEDB;
```

#### What to extract from the JSON files

In order for a JSON file to be processed it must contain certain bits of information in it which are essential for making recommendations:
- MusicBrainz ID (`musicbrainz_recordingid`) - required as a means to identify the track, duplicate tracks are grouped by this ID for merging
- Title - required for humans to easily identify the track, without it we'd have to backfill this information by ingesting another dataset (MusicBrainz metadata). If a track appears under multiple titles, we select the most common one.
- Artist - similar to title but merging is more complex a track can have multiple artists. We'll merge by selecting the most common combination of artists. A track is dropped if after duplicates are merged it still doesn't have an associated artist.
- Audio features (`danceability`, `aggressiveness`, `happiness`, etc.) - the basis of which recommendations are made, if a track has duplicates then they are merged by selecting the median (middle) value.
- Genre (`genre_dortmund`, `genre_rosamerica`) - can also be used to match similar songs, duplicates are merged by selecting the most common value so one bad categorization doesn't mislabel a track.
- Album - optional but nice for display, duplicates are still merged by selecting the most common, not-none, pair of (`album_id`, `album_name`, `release_date`).
- Year - semi-optional, it's extracted from the album release year but there's no album info then the year is set to 0

For 100k records:
- 11,182 duplicate submissions
- 4 submissions with missing data (doesn't have one of the required fields, except artist)
- 3,082 tracks with no artist (determined after merging duplicates)
- 85,732 records are valid and can be saved
- 1,319 of the valid records have missing release years

Note: By merging duplicates I'm able to fill-in missing information in the dataset, increasing the chances of having a representative single-entry for each track. However this comes with the assumption that most duplicates are correct and outliers are rare.

> TODO: date parsing, evaluate if pulling metadata from MB would have been better (tradeoff in dev time) 

##### How dates are stored
- In the SQLite DB dates (`date`, `originaldate`) are stored for albums, not tracks. This data was retrieved initially from MusicBrainz metadata and it represents album-level information (when the album, not the track was released).
- In the feature matrix (`features_and_index.npz`) dates are stored for each track based on when the track's album was released. This was needed in order to match tracks based on when they were release without needing to query the DB.


#### (DROP) Merging the JSON files

Merging multiple JSON files into one NDJSON. This is done to reduce the number of individual file reads needed to build the database. In theory it should be much faster to read JSON data sequentially from a single location than when split across millions of tiny files.
```bash
# Linux (or WSL)
/usr/bin/time -v bash -lc '
find acousticbrainz-highlevel-json-20220623-0/acousticbrainz-highlevel-json-20220623 -type f -name "*.json" -print0 \
| xargs -0 -n 20000 -P 12 jq -c . > highlevel-merged-0.ndjson
'
```
In WSL 
- for 100k records merge took 3min 54s (234s)
- for 1M records merge took 39min 07s (2347s)

In both cases this is much slower than processing each individual file in a Python script. One bottleneck is that the files are stored on an NTFS partition and not on a native Linux partition. The overhead of converting file access between the two formats adds extra milliseconds to each read.

```powershell
# Windows (Powershell 7+)
Measure-Command {
  Get-ChildItem -Path ".\acousticbrainz-highlevel-sample-json-20220623-0\acousticbrainz-highlevel-sample-json-20220623" `
    -Recurse -Filter *.json -File |
    ForEach-Object -Parallel{
      & jq -c . -- $_.FullName
    } | Out-File -FilePath merged.ndjson -Encoding utf8
}
```
Merge of 100k records takes 14min 36s (876s). This is even slower than through WSL. 

#### Recommendation logic

For making the recommendations we'll use the following approach:
- Extract metadata from the dataset to a database: track title, artist, album, genre, release year
- Extract audio features to a feature matrix that will be loaded in memory
- Run cosine simialrity between a target track and the feature matrix
- Return a list of tracks with the highest simiarities

> NOTE: Feature accuracy: https://acousticbrainz.org/datasets/accuracy

We can't run cosine similarity against the DB data directly because it involves comparing the current track against every other track. For 7M tracks that would involve getting all 7M rows from the DB for every request. Instead, we keep the data needed for comparisons in memory which reduces load on the DB. We'll only get the metadata from the DB.

Filtering is another complication. Ideally we should be able to pre-filter the list of candidate tracks to a smaller subset before running cosine similarity. Now the question becomes if we should store all data in memory but this dramatically increases RAM load. A hybrid approach is a good compromise here: keep the metadata in the DB for prefiltering and the audio features in memory.


Now we'll focus on the quality of the recommendations made. We've selected 11 audio features which seemed most relevant for making recommendations: "danceability", "aggressiveness", "happiness", "sadness", "relaxedness", "partyness", "acousticness", "electronicness", "instrumentalness", "tonality", "brightness". We'll use cosine similarity to make recommendations based on how close two tracks are in feature space.

The track selected as a target for testing is "Metallica - Enter Sandman". The reasoning for choosing it is that it's a popular track from a mainstream band so we can quickly assess if the recommendations made fit (other popular bands/tracks). Rock music is also heavily represented in the dataset (18.89%) so the recommender will have ample data to choose from, outlier recommendations can't be blamed on lack of data.

> TODO: Insert image of genre distribution here according to the 2 classifiers. Note that Dortmund is inaccurate as it incorrectly classifies "Enter Sandman" as being electronic music, as well as 87% of the tracks in the dataset. We cannot rely on it for matching genre.


The recommendation script output for the sample dataset (100k tracks):
```
Cosine similarity search took 0.01 seconds
Tracks similar to: Metallica - Enter Sandman (1991) [electronic] [roc]:

Recommendations:
Artist               | Title                          | Year   | Dortmund   | Rosamerica | Sim
-------------------------------------------------------------------------------------------------
Covenant             | I Am                           | 1998   | electronic | dan        |  0.999
Cubanate             | Blackout                       | 1993   | electronic | dan        |  0.996
Covenant             | Edge of Dawn                   | 1995   | electronic | dan        |  0.995
C-TYPE               | ワタシはメイド[洗脳調教MIX]      | 2001   | electronic | dan        |  0.994
Stabbing Westward    | Shame                          | 1996   | electronic | roc        |  0.993
Chanson Plus Bifluor | La Marie                       | 2006   | electronic | hip        |  0.993
Mika Bomb            | Super Sexy Razor Happy Girls   | 1999   | electronic | roc        |  0.991
Bon Jovi             | Woman in Love                  | 1992   | electronic | roc        |  0.991
Cubanate             | Switch                         | 1993   | electronic | dan        |  0.989
Die Toten Hosen      | In Dulci Jubilo                | 1998   | electronic | roc        |  0.989

Stats for similarities:
mean: -0.016901573166251183 std: 0.359785795211792 p95: 0.5544604063034058 max: 0.9988737106323242
Script execution took 0.03 seconds
```

While feature similarity is high numerically, the recommendations span a wide array of genres: electronic (Cubante, Coventant, C-TYPE), rock (Stabbing Westward, Bon Jovi, Die Toten Hosen), pop (Chanson Plus Bifluorée), indie rock (Mika Bomb). Given that the target track is from a well-established heavy-metal band, we'd expect predominantly rock recommendations. We can also see that the Dortmund genre classification of the recommendations is consistent with the target track although genre wasn't targeted in the logic.

First attempt to increase recommendation accuracy is to expand the dataset. This is the script output for the partial high-level dataset (1M tracks):

```
Cosine similarity search took 0.04 seconds
Tracks similar to: Metallica - Enter Sandman (1991) [electronic] [roc] [62c2e20a-559e-422f-a44c-9afa7882f0c4]:

Recommendations:
Artist               | Title                          | Year   | Dortmund   | Rosamerica | Sim     | MBID
---------------------------------------------------------------------------------------------------------------
dZihan & Kamien      | Touch the Sun                  | 2005   | electronic | hip        | 0.99999 | 78af6b52-8135-47b0-9bc2-a13f8c8cbc18
The Weakerthans      | The Prescience of Dawn         | 2003   | electronic | pop        | 0.99998 | 3f000987-70a0-4289-823c-cbd250438e33
Compay Segundo       | Viejos sones de Santiago       | 1999   | electronic | hip        | 0.99998 | 97773ff9-de13-402b-aeda-6ce15aab846d
Brody Dalle          | Meet the Foetus / Oh the Joy   | 2014   | electronic | pop        | 0.99997 | 45a8f8c4-1cb8-48ff-bb31-f9311ac08632
スパークリング☆ポイント         | 春風                             | 2005   | electronic | hip        | 0.99996 | 8f793b53-c27d-4d07-8816-0d420e8d1700
Deadsy               | Cruella                        | 2002   | electronic | hip        | 0.99996 | 602a684d-043e-44ae-afc0-e7daf889d128
Atlantic Starr       | Secret Lovers                  | 2002   | electronic | hip        | 0.99996 | ecb994df-bc2e-4923-94d7-dfe09c2d5cea
Corona               | Try Me Out                     | 1995   | electronic | dan        | 0.99996 | e4ffbd2a-86ad-48da-a34c-7f8828952bec
Midnight Oil         | Bullroarer                     | 1987   | electronic | hip        | 0.99996 | 51c88781-a6a9-4d12-899a-e7d3c455ca4f
Murmansk             | Paper Dust                     | 2009   | electronic | roc        | 0.99995 | 9b1734c6-02c6-48fb-a11b-dbd5ee8013e7

Stats for similarities:
mean: 0.10738343745470047 std: 0.564008355140686 p95: 0.9618921279907227 max: 0.9999926686286926
Script execution took 0.14 seconds
```

Increasing the number of datapoints did not significantly improve recommendation accuracy. The next attempt is to restrict the recommendations to be of the same genre and released in the same decade. We will use the categories set by the Rosamerica algorithm for genre because it consistently ranks Metallica as rock and not electronic. This is the script output:

```
Cosine similarity search took 0.00 seconds
Tracks similar to: Metallica - Enter Sandman (1991) [electronic] [roc] [62c2e20a-559e-422f-a44c-9afa7882f0c4]:

Recommendations:
Artist               | Title                          | Year   | Dortmund   | Rosamerica | Sim     | MBID
---------------------------------------------------------------------------------------------------------------
Ornette Coleman      | City Living                    | 1996   | electronic | roc        | 0.99993 | 70d7cac8-2e50-40bc-bd53-682d66ced3c8
Kristin Hersh        | Like You                       | 1998   | electronic | roc        | 0.99981 | 1a4004e6-2cc1-4c27-88a4-7e351a45fb2a
Rage                 | From the Cradle to the Grave   | 1998   | electronic | roc        | 0.99977 | e130ae06-e5e4-4668-ba44-cefda15a49b3
Anthrax              | Burst                          | 1993   | electronic | roc        | 0.99974 | 49863b15-0d64-4bc6-85e4-f386cb0b91a6
Garageland           | Cut It Out                     | 1997   | electronic | roc        | 0.99971 | c1dd982a-a8ea-4f80-9fb7-987673bb78e5
The Smashing Pumpkin | Today                          | 1993   | electronic | roc        | 0.99965 | 622baf54-342a-40a6-801e-43f159fc4f38
HammerFall           | Dreamland                      | 1998   | electronic | roc        | 0.99959 | 8ef679e3-6e66-4893-a27c-5f530067dafb
Mad Season           | I Don't Know Anything          | 1995   | electronic | roc        | 0.99953 | b8647283-0644-4eb2-a1d9-2bcddc5e7e3f
Evanescence          | Imaginary                      | 1998   | electronic | roc        | 0.99949 | 5399493d-4599-4d1e-9fb8-74257a6efbd3
Ayreon               | Act I "The Dawning": Eyes of T | 1995   | electronic | roc        | 0.99949 | a2d97860-e047-4356-a43f-5948b9a221c5

Stats for similarities:
mean: 0.09563542157411575 std: 0.566411018371582 p95: 0.972338080406189 max: 0.9999292492866516
Script execution took 0.02 seconds
```

Now most tracks (Rage, Anthrax, HammerFall, Mad Season, The Smashing Pumpkins, Ayreon) are aligning well with 1990s heavy metal, thrash, grunge, or alternative rock. However the recommendation with the highest similarity is an outlier (0.99993, Ornette Coleman - City Living ) and is jazz music incorrectly categorized as rock. This shows the limitations of the Acoustic Brainz dataset, we can't get accurate predictions if the data itself is flawed. Let's try increasing the dataset again, to 2M data points.

```
Cosine similarity search took 0.00500 seconds, compared against 58,534/1,117,188
Tracks similar to: Metallica - Enter Sandman (1991) [electronic] [roc] [62c2e20a-559e-422f-a44c-9afa7882f0c4]:

Recommendations:
Artist               | Title                          | Year   | Dort       | Rosa | Sim
--------------------------------------------------------------------------------------------
Anti‐Flag            | We've Got His Gun              | 1998   | electronic | roc  | 0.97018
The Smashing Pumpkin | Appels + Oranjes               | 1998   | electronic | roc  | 0.96874
Kitchens of Distinct | Cowboys and Aliens             | 1994   | electronic | roc  | 0.96406
Happy Drivers        | I Shot Da Sheriff (live)       | 1991   | electronic | roc  | 0.95316
Dark Funeral         | Slava Satan                    | 1998   | electronic | roc  | 0.94786
Ария                 | Бесы                           | 1991   | electronic | roc  | 0.94724
Demoniac             | So Bar Gar                     | 1994   | rock       | roc  | 0.94720
Isengard             | Total Death                    | 1995   | electronic | roc  | 0.94715
Abscess              | Die Pig Die                    | 1995   | rock       | roc  | 0.94682
D-A-D                | Blood In/Out                   | 1995   | electronic | roc  | 0.94531

Stats for similarities:
mean: 0.2099045217037201 std: 0.2784648537635803 p95: 0.6205866932868958 max: 0.9701764583587646
Script execution took 1.36628 seconds
```

This set of recommendations contains a majority of rock/metal/grunge tracks from the 1990s, which fits the target track: Anti-Flag (punk rock), Smashing Pumpkins (alt rock), Dark Funeral (black metal), Ария (Russian heavy metal), Isengard (black metal), Abscess (death/doom), D-A-D (hard rock). Some outliers still creep in: Kitchens of Distinction – Cowboys and Aliens (dream pop / indie rock),  Happy Drivers – I Shot Da Sheriff (psychobilly/rockabilly). These are not perceptually close to the target, mostly because the genre classification of rock covers a wide spectrum and doesn't have enough granularity to differentiate between sonically different subgenres.


We've seen that expanding the dataset size does produce better results but doesn't completely remove outliers. Next we'll focus on expanding the feature space (dimensionality). We'll start again from the sample dataset as a baseline and see how recommendation quality changes as the number of features increases. At the same time, we'll keep the decade and genre guardrails since we've already validated that they produce a significant increase in perceived quality.

Sample output with 11 features (only single dimensional features, decade and genre filters)
```
Feature matrix stats:
Number of unique tracks: 84850
Number of unique feature vectors: 84833
Number of near-zero columns: 0
Total number of columns: 11
Cosine similarity search took 0.00000 seconds, compared against 3,296/84,850
Tracks similar to: Metallica - Enter Sandman (1991) [electronic] [roc] [62c2e20a-559e-422f-a44c-9afa7882f0c4]:

Recommendations:
Artist               | Title                          | Year   | Dort       | Rosa | Sim     | MBID
---------------------------------------------------------------------------------------------------------
Stabbing Westward    | Shame                          | 1996   | electronic | roc  | 0.99341 | d4016854-750b-4404-b146-e177ad083c67
Mika Bomb            | Super Sexy Razor Happy Girls   | 1999   | electronic | roc  | 0.99152 | 08104eeb-51ce-4930-a24a-e7e9847af86a
Bon Jovi             | Woman in Love                  | 1992   | electronic | roc  | 0.99108 | bed34077-0202-4ac7-8b24-5858e8de6b95
Die Toten Hosen      | In Dulci Jubilo                | 1998   | electronic | roc  | 0.98887 | 9a32af1a-ba59-4a4e-b3a0-f05e2267306c
Guns N' Roses        | Bad Obsession                  | 1991   | electronic | roc  | 0.98319 | 5c6d9c76-f9cd-4711-9c0a-a9f1c1c89c16
Sonic Youth          | 100% (LP version)              | 1992   | rock       | roc  | 0.97900 | d4561919-ae4e-45a2-8014-4947f6766f61
Die Toten Hosen      | König der Blinden              | 1999   | electronic | roc  | 0.97581 | 17eff1f4-1fc6-48e7-8641-ddffa8f3c67a
Stabbing Westward    | I Don’t Believe                | 1996   | electronic | roc  | 0.97542 | 408f69a3-0e23-4c38-a8b6-2bf0868d6ece
Melt-Banana          | Cannot                         | 1998   | rock       | roc  | 0.96966 | 9d0d7efa-d9ea-4313-a2de-e7c7f1f6fac2
Guns N' Roses        | Don't Damn Me                  | 1991   | electronic | roc  | 0.96864 | 5c3198ad-c5d1-448d-8c86-866fa38808b7

Stats for similarities:
mean: 0.2587907016277313 std: 0.2640484869480133 p95: 0.636947751045227 max: 0.9934141635894775
Script execution took 0.08100 seconds
```

Sample output with 16 features (added moods_mirex)
```
Feature matrix stats:
Number of unique tracks: 84850
Number of unique feature vectors: 84832
Number of near-zero columns: 0
Total number of columns: 16
Cosine similarity search took 0.00100 seconds, compared against 3,296/84,850
Tracks similar to: Metallica - Enter Sandman (1991) [electronic] [roc] [62c2e20a-559e-422f-a44c-9afa7882f0c4]:

Recommendations:
Artist               | Title                          | Year   | Dort       | Rosa | Sim
--------------------------------------------------------------------------------------------
Stabbing Westward    | Shame                          | 1996   | electronic | roc  | 0.99447
Mika Bomb            | Super Sexy Razor Happy Girls   | 1999   | electronic | roc  | 0.99286
Bon Jovi             | Woman in Love                  | 1992   | electronic | roc  | 0.99250
Die Toten Hosen      | In Dulci Jubilo                | 1998   | electronic | roc  | 0.99059
Guns N' Roses        | Bad Obsession                  | 1991   | electronic | roc  | 0.98587
Sonic Youth          | 100% (LP version)              | 1992   | rock       | roc  | 0.98230
Die Toten Hosen      | König der Blinden              | 1999   | electronic | roc  | 0.97967
Stabbing Westward    | I Don’t Believe                | 1996   | electronic | roc  | 0.97924
Guns N' Roses        | Don't Damn Me                  | 1991   | electronic | roc  | 0.97371
Melt-Banana          | Cannot                         | 1998   | rock       | roc  | 0.97345

Stats for similarities:
mean: 0.2892068028450012 std: 0.27297839522361755 p95: 0.6601920127868652 max: 0.9944671392440796
Script execution took 0.09200 seconds
```

Adding` moods_mirex` is a low-noise improvement, it strengthens cohesion without changing the flavor of the results.

Sample with 36 features ("moods_mirex", "ismir04_rhythm", "genre_tzanetakis")
```
Feature matrix stats:
Number of unique tracks: 84850
Number of unique feature vectors: 84831
Number of near-zero columns: 0
Total number of columns: 36
Cosine similarity search took 0.00100 seconds, compared against 3,296/84,850
Tracks similar to: Metallica - Enter Sandman (1991) [electronic] [roc] [62c2e20a-559e-422f-a44c-9afa7882f0c4]:

Recommendations:
Artist               | Title                          | Year   | Dort       | Rosa | Sim
--------------------------------------------------------------------------------------------
Die Toten Hosen      | In Dulci Jubilo                | 1998   | electronic | roc  | 0.99537
Stabbing Westward    | I Don’t Believe                | 1996   | electronic | roc  | 0.99151
Die Toten Hosen      | Merry X‐Mas Everybody          | 1998   | electronic | roc  | 0.98532
Guns N' Roses        | Don't Damn Me                  | 1991   | electronic | roc  | 0.98206
Yo La Tengo          | Big Day Coming                 | 1993   | electronic | roc  | 0.97579
Die Toten Hosen      | Entschuldigung, es tut uns lei | 1999   | electronic | roc  | 0.97465
Queen                | The Hero                       | 1994   | electronic | roc  | 0.97354
Die Toten Hosen      | Weihnachtsmann vom Dach        | 1998   | electronic | roc  | 0.97279
Die Toten Hosen      | Unsterblich                    | 1999   | electronic | roc  | 0.97080
Stabbing Westward    | Crushing Me                    | 1996   | electronic | roc  | 0.96807

Stats for similarities:
mean: 0.08835283666849136 std: 0.19821356236934662 p95: 0.2858421504497528 max: 0.9953653812408447
Script execution took 0.12400 seconds
```

Adding the extra features leads to an over-representation of a single artist "Die Toten Hosen" in the results. They seem to inject more noise than signal, the reason is that:
- `ismir04_rhythm` is too categorical being focused on ballroom dance styles and irrelevant outside of this domain area.
- `genre_tzanetakis` is one of the oldest genre classifiers (2002) and mislabels rock/metal badly. The classifier tends to overpredict jazz, blues, and pop, and it’s weak at distinguishing subgenres of rock/metal.

Among other features in the dataset that we could add, genre classifiers (Dortmund and Rosamerica) are better suited as guardrails rather than as features in the cosine similarity space. This is because categorical outputs don’t map well to an algorithm that works best with smooth, continuous values. If included directly, the results would collapse into clusters around broad genre centroids, which hides the finer musical differences that actually matter for recommendations. 

Other features that can be left out:
- `genre_electronic` it’s a very narrow classifier (ambient, dnb, house, techno, trance), could introduce noise, similar to other categorical features.
- `gender` this just predicts whether the main vocal sounds male or female. That's not a strong driver of musical similarity.

Finally, `moods_mirex`, although it also splits probabilities into multiple buckets like other classifiers (ismir04_rhythm, genre_tzanetakis), has two important advantages:

- The buckets capture general perceptual characteristics that apply to any piece of music rather than genre-specific labels, so it doesn't introduce noise when applied outside a narrow domain.
  - Cluster 1 – Passionate / Cheerful / Rowdy
  - Cluster 2 – Poignant / Sad / Bittersweet
  - Cluster 3 – Humorous / Silly / Witty
  - Cluster 4 – Aggressive / Fiery / Intense
  - Cluster 5 – Peaceful / Relaxed / Calming
- The outputs are continuous rather than categorical: they’re not hard predictions but distributions that describe a track's mood profile. Probabilities are usually spread across several clusters, which creates smoother gradients of similarity instead of forcing tracks into one rigid bucket.

With the features decided, this is the new output of the recommender for a dataset with 2M tracks:

```
Feature matrix stats:
Number of unique tracks: 1117188
Number of unique feature vectors: 1117016
Number of near-zero columns: 0
Total number of columns: 16
Cosine similarity search took 0.00700 seconds, compared against 58,534/1,117,188
Tracks similar to: Metallica - Enter Sandman (1991) [electronic] [roc] [62c2e20a-559e-422f-a44c-9afa7882f0c4]:

Recommendations:
Artist               | Title                          | Year   | Dort       | Rosa | Sim
--------------------------------------------------------------------------------------------
The Smashing Pumpkin | Appels + Oranjes               | 1998   | electronic | roc  | 0.96584
Demoniac             | So Bar Gar                     | 1994   | rock       | roc  | 0.94603
Isengard             | Total Death                    | 1995   | electronic | roc  | 0.94592
Ария                 | Бесы                           | 1991   | electronic | roc  | 0.94585
Kitchens of Distinct | Cowboys and Aliens             | 1994   | electronic | roc  | 0.94556
Abscess              | Die Pig Die                    | 1995   | rock       | roc  | 0.94545
D-A-D                | Blood In/Out                   | 1995   | electronic | roc  | 0.94457
Dimple Minds         | Die Besten Trinken Aus         | 1993   | electronic | roc  | 0.94435
Happy Drivers        | I Shot Da Sheriff (live)       | 1991   | electronic | roc  | 0.94406
Comecon              | The Mule                       | 1992   | rock       | roc  | 0.94398

Stats for similarities:
mean: 0.2700285315513611 std: 0.30203670263290405 p95: 0.6666585803031921 max: 0.965840220451355
Script execution took 1.38800 seconds
```

Comparing against the previous result for 2M datapoints (11 features) we can see a few meaningful changes. Outliers are still present but are ranked lower (Kitchens of Distinction, Happy Drivers) while the top spots are bands like Demoniac, Isengard, Ария, Abscess, all firmly in the heavy/black/death metal spectrum. That’s musically close to Metallica. The Smashing Pumpkins is not as heavy as Metallica but still musically related to rock.

### API

We take advantage of DRF's router and ModelViewSet classes to create list and detail endpoints based on Django models. Extended functionality (tracks or albums by an artist) can be added by appending `@action` methods to the classes. We can also extend what each endpoint returns by overriding the corresponding method: `retrieve` for `detail` and `list`.

DB field names can be renamed in the serializers to make them human-readable, ex: `musicbrainz_recordingid` becomes `mbid`.

Pagination through `rest_framework.pagination.PageNumberPagination`
Filters through `django_filters.rest_framework.DjangoFilterBackend`

#### API Documentation

- Used `drf-spectacular` to generate documentation dynamically withot the need for a separate build step. The views it provides `SpectacularAPIView`, `SpectacularRedocView`, `SpectacularSwaggerView` map to API endpoints and are listed on the API root.
- All API views were made to serialize their data before returning it as a response. For ModelViewSets the choice of serializer is picked up automatically and listed in the documentation.
- The `@extend_schema` decorator is used to specify additional info that will show up in the docs:
  - Choice of serializer for regulat APIViews (`responses`)
  - Request format serializer (`request`)
  - Text description (`description`)
  - Query string parameters (`parameters`)

- If a serializer uses a custom method to generate a field (ex: `get_links()` for HATEOAS) we'll need to sepecify how that field is serialized using the `@extend_schema_field` decorator.


#### Search

**Trigram search** compares how many overlapping 3-character substrings (or trigrams) two strings share. Two strings with many common trigrams are considered to be very similar. For example, from the string "Alice" we can create 3 trigrams: "ali", "lic", and "ice".

PostgreSQL exposes trigram operators through the [`pg_trgm` extension](https://www.postgresql.org/docs/current/pgtrgm.html) extension. To enable it we'll need to manually create a migration that enables `TrigramExtension`. We'll also need to add `django.contrib.postgres` to the installed apps list to enable the `trigram_similar` lookup field.

```py
# Now we can use the lookup field to filter in Django
Track.objects.filter(title__trigram_similar=query)
```

```sql
-- In SQL the % operator is used in the query
SELECT title
FROM recommend_api_track
WHERE title % 'sunshine of your love';
```

With this implementation the results are somewhat relevant to the query but they're not sorted by the similarity score by default. To rank results, we'll need to annotate the queryset with the trigram distance between the search terms and track title and order them.

```py
Track.objects.filter(title__trigram_similar=query)
  .annotate(distance=TrigramDistance("title", query))
  .order_by("distance")
```

```sql
-- The resulting SQL
SELECT title, (title <-> 'sunshine of your love') AS distance
FROM recommend_api_track
WHERE title % 'sunshine of your love'
ORDER BY distance ASC;
```

The search results will be more relevant now, however this also increases average query times from `0.119s` to `0.463s` which could be annoying for the user. In order to keep the response times down we can create complementary trigram indexes on the models:
- **GIN trigram index** (gin_trgm_ops): accelerates filtering like `WHERE title % 'q'`.
- **GiST trigram index** (gist_trgm_ops): enables k-NN (nearest-neighbour) ordering for queries like `ORDER BY title <-> 'q'` without scanning/sorting the entire table.

```py
# Example for track model
class Track(models.Model):
    title = models.TextField()
    class Meta:
        indexes = [
            GinIndex(fields=["title"], name="track_title_trgm", opclasses=["gin_trgm_ops"]),
            GistIndex(fields=["title"], name="track_title_trgm_gist", opclasses=["gist_trgm_ops"]),
        ]
```

Note: It's important to validate that the indexes are actually used in queries. We can do this either by calling `query.explain()` in Python or exporting the SQL query it generates from a QuerySet and running it in SQL with EXPLAIN. In both cases the explanation should included something like "Index Scan using ... gist_trgm_ops...".


Performance of searching by track title on a DB with 1,921,455 rows in Track model, endpoint: `/search/?q=enter` 
- **Filter only** with `trigram_similar` lookup field (`Track.objects.filter(title__trigram_similar=query)`) - 0.001s
- **Filter + paginate** Filtering in QS and paginating the response - 0.991s
  - Paging the response causes the DB query to be run twice, increasing response times
- **Filter + paginate + `ORDER BY title`** Filtering in QS, paginating the response, ordering by title - 1.6s
- **Filter + `TrigramSimilarity` order, no paging** Annotating the QS response with a similarity score via `TrigramSimilarity` and ordering by similarity, no paging - 0.463s
- **With GIN + GiST indexes** Adding GIN and GiST indexes - 0.028s
- **Add secondary order by `submissions`** Sorting by number of submissions - 0.4s

Relevant links:
- https://docs.djangoproject.com/en/5.2/ref/contrib/postgres/search/
- https://medium.com/@saritasa/how-to-optimize-name-search-in-postgresql-with-trigram-and-btree-indexes-02c57eb27687

### Front-end

Vite is front-end build tool. The app is based on its React+TypeScript template that can be generated using the command `npm create vite@latest . -- --template react-ts`. The API is queried using Axios, an open-source HTTP client. Custom methods for querying the API are defined in `api.ts`.
To serve the React app from Django in production we can implement a view (`SPAView`) which loads the bundle generated by `npm run build`. For development we can use Vite to serve the front-end using `npm run dev`.

Styles are written in plain CSS. I took advantage of [CSS nesting](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_nesting) to wrap each component's styles in a namespace so they don't affect other components.