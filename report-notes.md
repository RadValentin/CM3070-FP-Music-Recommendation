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
The prototype revealed that relational databases, while optimal for storing track metadata, aren't suitable for storing audio features. The features are usually in the form of vectors and most database systems don't offer support for such a datatype. Having to serialize vectors to strings for storage would significantly bottleneck database operations, the same goes for deserializing the data when it needs to be used in code. A vector DB/index is needed instead: FAISS, Annoy, ScaNN.

Another thing to consider is the complexity of making recommendations. For each song we'd have to compare against every other song to determine similarity which is a $O(N^2)$ problem. For a million records that would require the same number of DB requests to run the comparisons.

### Data Processing
> Note: The performance data was recorded on a system with 16GB DDR3 RAM, Intel 4690k 4-core CPU and SATA-3 SSD.

For the 100k records in the high-level sample dataset:
- Takes 34.79s to read all of the JSON files and build the model objects
- Takes 6.82s to insert the data in the DB
- 1475 records don't have any associated release dates
- In general, the dates in the dataset are inconsistently formatted, some given as only a year, some in ISO date format, some in SQL Datetime while others in ISO 8601 with Zulu (UTC).

For 1M records high-level dataset:
- Takes 362s to read all of the JSON files and build the model objects
- Takes 50s to insert the data in the DB, inserts are batched in groups of 2000
- 2029 records don't have any associated release dates
- 3669 records have missing data (title, artist, etc.)
- 297011 records are duplicates
- 697291 records are left at the end to be inserted into the DB
- DB size on disk is 190 MB
- The pitfalls of user-generated data
  - popular songs and artists (Nirvana, Beatles) appear frequently
  - lots of generic placeholder titles: [untitled], End Credits, Finale, [unknown]
  - character songs from anime or games, ex: `三千院ナギ starring 釘宮理恵`, `綾崎ハヤテ starring 白石涼子`

- > IMPORTANT: I only loaded 1M records and got the times above, need to load ALL 30M records from all archives

#### How AcousticBrainz Gets Its Data
- Volunteers run the Essentia analyzer locally on their audio files (MP3, FLAC, etc.).
- The analyzer extracts low-level audio features (e.g., MFCCs, spectral data) and high-level descriptors (e.g., danceability, mood).
- The results are uploaded to AcousticBrainz along with the song’s MusicBrainz ID (MBID).
- Over time, this crowd-sourced system has built up millions of submissions.

### Building the database

## Merging the JSON files

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

## Recommendation logic

For making the recommendations we'll use the following approach:
- Extract metadata from the dataset to a database: track title, artist, album, genre, release year
- Extract audio features to a feature matrix that will be loaded in memory
- Run cosine simialrity between a target track and the feature matrix
- Return a list of tracks with the highest simiarities

We can't run cosine similarity against the DB data directly because it involves comparing the current track against every other track. For 7M tracks that would involve getting all 7M rows from the DB for every request. Instead, we keep the data needed for comparisons in memory which reduces load on the DB. We'll only get the metadata from the DB.

Filtering is another complication. Ideally we should be able to pre-filter the list of candidate tracks to a smaller subset before running cosine similarity. Now the question becomes if we should store all data in memory but this dramatically increases RAM load. A hybrid approach is a good compromise here: keep the metadata in the DB for prefiltering and the audio features in memory.


The recommendation script output for sample dataset (100k tracks):
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

Now most tracks (Rage, Anthrax, HammerFall, Mad Season, The Smashing Pumpkins, Ayreon) are aligning well with 1990s heavy metal, thrash, grunge, or alternative rock. However the recommendation with the highest similarity is an outlier (0.99993, Ornette Coleman - City Living ) and is jazz music incorrectly categorized as rock. This shows the limitations of the Acoustic Brainz dataset, we can't get accurate predictions if the data itself is flawed.

