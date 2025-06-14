# Music Recommendation System Prototype

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

Similar songs can be identified by calculating the cosine similarity between the original song's and all other songs TF-IDF vectors. The songs with the highest values (between -1 and 1) will also be closest in terms of their lyrical content.