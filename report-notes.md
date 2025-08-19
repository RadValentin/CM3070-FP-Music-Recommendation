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

### Recommendation logic

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
Tracks similar to: Metallica - Enter Sandman (1991) [electronic] [roc]:

Recommendations:
Artist               | Title                          | Year   | Dortmund   | Rosamerica | Sim
-------------------------------------------------------------------------------------------------
Death From Above 197 | Little Girl                    | 2004   | electronic | roc        |  1.000 |
Ornette Coleman      | Angel Voice                    | 1958   | electronic | hip        |  1.000 |
Cecilia Barraza      | El Sueño de Pochi              | 2002   | electronic | jaz        |  1.000 |
Jonathan Edwards     | Sunshine (Go Away Today)       | 2007   | electronic | hip        |  1.000 |
Funker Vogt          | Spread Your Legs!              | 1998   | electronic | dan        |  1.000 |
Big Rude Jake        | Queer for Cat                  | 1999   | electronic | pop        |  1.000 |
Rewiring Genesis     | Back in N.Y.C.                 | 2008   | electronic | roc        |  1.000 |
Buddy Rich           | Funk City-Ola                  | 2007   | electronic | roc        |  1.000 |
Dave Dobbyn          | P.C.                           | 1994   | electronic | rhy        |  1.000 |
Herbert Grönemeyer   | Männer                         | 1997   | electronic | hip        |  1.000 |

Stats for similarities:
mean: 0.10890465974807739 std: 0.5467357039451599 p95: 0.9561436772346497 max: 0.9999586939811707
Script execution took 0.14 seconds
```