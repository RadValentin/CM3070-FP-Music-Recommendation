import io, sys, time
import numpy as np, math
from django.core.management.base import BaseCommand, CommandError
from recommend_api.models import Track
import recommend_api.recommender as rec


class Command(BaseCommand):
    help = "Prints recommendations for a given MBID to the console (default: Metallica - Enter Sandman)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--mbid",
            type=str,
            default="62c2e20a-559e-422f-a44c-9afa7882f0c4",
            help="Use the sample dataset instead of full high-level parts.",
        )

    def handle(self, *args, **options):
        try:
            generate_recommendations(
                target_mbid=options["mbid"]
            )
        except Exception as e:
            raise CommandError(str(e))
        
        self.stdout.write(self.style.SUCCESS("Done."))


def generate_recommendations(target_mbid: str):
    start = time.time()

    # Select a track from the database by its MBID
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
    recommendations = rec.recommend(
        target_mbid=target_mbid, 
        options={
            "k": 100,
            "use_ros": True
        }
    )
    target_year = recommendations["target_year"]
    target_genre_dortmund = recommendations["target_genre_dortmund"]
    target_genre_rosamerica = recommendations["target_genre_rosamerica"]
    top_tracks = recommendations["top_tracks"]
    stats = recommendations["stats"]

    print(
        f'Cosine similarity search took {stats["search_time"]:.5f} seconds,',
        f'compared against {stats["candidate_count"]:,}/{feature_stats["unique_track_count"]:,}',
    )

    # create a hashmap of the Track objects by mbid
    top_mbids = [t["mbid"] for t in top_tracks]
    track_map = {
        t.musicbrainz_recordingid: t
        for t in Track.objects.filter(
            musicbrainz_recordingid__in=top_mbids
        ).prefetch_related("artists")
    }

    # add popularity and combined score
    for track in top_tracks:
        submissions = track_map.get(track["mbid"]).submissions
        # simple blend: mostly similarity, small nudge from popularity
        track["final_score"] = 0.9 * track["similarity"] + 0.1 * math.log1p(submissions)

    # rerank by final score
    top_tracks.sort(key=lambda x: x["final_score"], reverse=True)

    print(
        f"Tracks similar to: {target_artist.name} - {target_track.title} ({target_year}) [{target_genre_dortmund}] [{target_genre_rosamerica}] [{target_mbid}]:"
    )

    print("\nRecommendations:")
    header = f"{'Artist':20} | {'Title':30} | {'Year':6} | {'Dort':6} | {'Rosa':4} | {'Sim':5} | {'Sub':3} | {'Score':4} | {'MBID':36}"
    print(header)
    print("-" * len(header))

    # Display the tracks in order by going through top_mbids list and extracting track data from a dict.
    seen_artists = set()
    unique_tracks = []
    for track in top_tracks:
        track_obj = track_map.get(track["mbid"])
        artist = track_obj.artists.first()
        artist_name = artist.name if artist else "Unknown Artist"

        if len(unique_tracks) >= 10:
            break
        elif artist in seen_artists:
            continue  # skip duplicates
        elif track["mbid"] == target_mbid:
            # Skip is target track is encountered again somehow
            continue
        elif artist_name == target_artist.name and track_obj.title == target_track.title:
            # Skip if it's the same song by the same artist as the target track
            continue

        seen_artists.add(artist)
        unique_tracks.append(track)

        print(
            f'{artist_name[:20]:20} | {track_obj.title[:30]:30} | {str(track["year"]):6} | '
            f'{track["genre_dortmund"][:6]:6} | {track["genre_rosamerica"][:4]:4} | '
            f'{track["similarity"]:2.3f} | {track_obj.submissions:3d} | {track["final_score"]:1.3f} | '
            f'{track["mbid"]}'
        )


    top_tracks = unique_tracks
    # Print statistics
    print("\nStats for similarities:")
    print("mean:",stats["mean"],
          "std:",stats["std"],
          "p95:",stats["p95"],
          "max:",stats["max"])

    end = time.time()
    print(f"Script execution took {end - start:.5f} seconds")
