import io, os, sys, time, django

# Ensure print output is UTF-8 formatted so it can be logged to a file (if needed)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# Django setup so we can access ORM models
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(os.getcwd()))))
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "music_recommendation.settings")
# django.setup()

from recommend_api.models import Track
import recommend_api.recommender as rec

start = time.time()

# Select a track from the database by its MBID
target_mbid = "62c2e20a-559e-422f-a44c-9afa7882f0c4"  # Metallica - Enter Sandman
target_track = Track.objects.get(musicbrainz_recordingid=target_mbid)
target_artist = target_track.artists.first()

# Display stats about feature matrix
feature_stats = rec.get_feature_stats()
print("Feature matrix stats:")
print(f'Number of unique tracks: {feature_stats["unique_track_count"]}')
print(f'Number of unique feature vectors: {feature_stats["unique_vector_count"]}')
print(f'Number of near-zero columns: {feature_stats["near_zero_col_count"]}')
print(f'Total number of columns: {feature_stats["total_col_count"]}')

# Display recommendations
recommendations = rec.recommend(target_mbid, 50, True)
target_year = recommendations["target_year"]
target_genre_dortmund = recommendations["target_genre_dortmund"]
target_genre_rosamerica = recommendations["target_genre_rosamerica"]
top_tracks = recommendations["top_tracks"]
stats = recommendations["stats"]

print(
    f'Cosine similarity search took {stats["search_time"]:.5f} seconds,',
    f'compared against {stats["candidate_count"]:,}/{feature_stats["unique_track_count"]:,}',
)

top_mbids = [t["mbid"] for t in top_tracks]
track_map = {
    t.musicbrainz_recordingid: t
    for t in Track.objects.filter(
        musicbrainz_recordingid__in=top_mbids
    ).prefetch_related("artists")
}

print(
    f"Tracks similar to: {target_artist.name} - {target_track.title} ({target_year}) [{target_genre_dortmund}] [{target_genre_rosamerica}] [{target_mbid}]:"
)

print("\nRecommendations:")
header = f"{'Artist':20} | {'Title':30} | {'Year':6} | {'Dortmund':10} | {'Rosamerica':10} | {'Sim':7} | {'MBID':10}"
print(header)
print("-" * len(header))

# Display the tracks in order by going through top_mbids list and extracting track data from a dict.
result_counter = 0
for track in top_tracks:
    track_obj = track_map.get(track["mbid"])
    artist = track_obj.artists.first()
    artist_name = artist.name if artist else "Unknown Artist"

    if result_counter >= 10:
        break
    elif track["mbid"] == target_mbid:
        # Skip is target track is encountered again somehow
        continue
    elif artist_name == target_artist.name and track_obj.title == target_track.title:
        # Skip if it's the same song by the same artist as the target track
        continue
    else:
        result_counter += 1

    print(
        f'{artist_name[:20]:20} | {track_obj.title[:30]:30} | {str(track["year"]):6} | '
        f'{track["genre_dortmund"]:10} | {track["genre_rosamerica"]:10} | {track["similarity"]:6.5f} | {track["mbid"]}'
    )

# Print statistics
print("\nStats for similarities:")
print(
    "mean:",
    stats["mean"],
    "std:",
    stats["std"],
    "p95:",
    stats["p95"],
    "max:",
    stats["max"],
)

end = time.time()
print(f"Script execution took {end - start:.5f} seconds")
