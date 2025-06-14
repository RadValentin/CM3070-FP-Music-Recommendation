import os
import sys
import django
from django.db import transaction
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "music_recommendation.settings")
django.setup()

from recommend_api.models import Song

# Spotify Million Song Dataset - https://www.kaggle.com/datasets/notshrirang/spotify-million-song-dataset
df = pd.read_csv("assets/spotify_millsongdata.csv")
df.reset_index(inplace=True)  # index becomes a column named "index"
df.rename(columns={"index": "id"}, inplace=True)  # rename it to "id"
df.drop(columns=['link'], inplace=True)

# limit to only a subset of 100 songs
#df = df[:100]

# clean the text
clean_text = df['text'].str.lower()
# remove carriage return (\r) and newline (\n) characters
clean_text = clean_text.replace(r'\r|\n', '', regex=True)
# remove punctuation
clean_text = clean_text.replace(r'[^\w\s]', '', regex=True)

# wipe DB
Song.objects.all().delete()

from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
import json

vectorizer = TfidfVectorizer(stop_words='english', max_features=10000)
tfidf_matrix = vectorizer.fit_transform(clean_text)
dense_matrix = tfidf_matrix.toarray()

print("Saving TF-IDF matrix to disk...")
filename = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".." ,"tfidf_matrix.npy")
np.save("tfidf_matrix.npy", dense_matrix) 

# create DB entries for songs
print("Creating DB entries in memory...")
songs = []
for index, row in df.iterrows():
    songs.append(Song(
        id=row['id'],
        title=row['song'],
        artist=row['artist'],
        lyrics=row['text']
    ))

print("Saving DB entries to disk...")
batch_size = 1000
for i in range(0, len(songs), batch_size):
    print(str(i) + '/' + str(len(songs)) + ' processed')
    Song.objects.bulk_create(songs[i:i+batch_size])

print('All songs processed!')

# # tab-separated text
# df['tfidf'] = [','.join(map(str, vec)) for vec in tfidf_matrix.toarray()]
# filename = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output.csv")
# df.to_csv(filename, sep="\t", index=False)  