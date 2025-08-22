import logging
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import *
from .serializers import *
import recommend_api.recommender as rec

log = logging.getLogger(__name__)

@api_view(['GET'])
def track_detail(request, musicbrainz_recordingid):
    try:
        song = Track.objects.get(musicbrainz_recordingid=musicbrainz_recordingid)
    except Track.DoesNotExist:
        return Response({"detail": "Track not found"}, status=status.HTTP_404_NOT_FOUND)

    
    serializer = TrackSerializer(song)
    return Response(serializer.data)

@api_view(['POST'])
def similar_tracks(request):
    target_mbid = request.data.get('musicbrainz_recordingid')
    if not target_mbid:
        return Response({"detail": "Missing 'musicbrainz_recordingid' parameter."}, 
                        status=status.HTTP_400_BAD_REQUEST)

    try:
        target_track = Track.objects.get(musicbrainz_recordingid=target_mbid)
        target_artist = target_track.artists.first()
    except Track.DoesNotExist:
        return Response({"detail": "Target track not found"}, status=status.HTTP_404_NOT_FOUND)
    
    # Get the recommendations dict, ask for a large number of similar tracks (50) 
    # so we can have a buffer in case we need to filter the data 
    # (e.g. same artist shows up multiple times)
    try:
        recommendations = rec.recommend(target_mbid, 50, True)
        top_tracks = recommendations["top_tracks"]
    except ValueError as e:
        # MBID not found in feature matrix
        return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except FileNotFoundError as e:
        # Feature matrix data couldn't be loaded from disk
        return Response({"detail": str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    except Exception as e:
        # Any other error
        log.exception("Unexpected error in similar_tracks")
        return Response({"detail": "Unexpected error."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Build the QuerySet for the similar track data and create an index based on MBID
    top_mbids = [t["mbid"] for t in top_tracks]
    track_map = {
        t.musicbrainz_recordingid: t
        for t in Track.objects.filter(musicbrainz_recordingid__in=top_mbids)
                              .prefetch_related("artists")
    }

    # Go through the similar tracks and extract a subset by filtering for
    # artist name, track title, etc.
    similar_list = []
    for track in top_tracks:
        # Skip is target track is encountered again somehow
        if track["mbid"] == target_mbid:
            continue
        
        track_obj = track_map.get(track["mbid"])
        if not track_obj:
            continue

        artist = track_obj.artists.first()
        artist_name = artist.name if artist else "Unknown Artist"

        # Skip if it's the same song by the same artist as the target track
        if artist_name == target_artist.name and track_obj.title == target_track.title:
            continue
        
        # Include similarity score for the track
        similar_list.append((track_obj, track["similarity"]))

        # Limit the subset
        if len(similar_list) >= 5:
            break


    target_serializer = SimilarTrackSerializer(target_track)
    stats_serializer = RecommendStatsSerializer(recommendations["stats"])

    # Keep similarity in payload
    similar_payload = [
        {**SimilarTrackSerializer(obj).data, "similarity": sim}
        for (obj, sim) in similar_list
    ]
    
    return Response({
        'target_track': target_serializer.data,
        'similar_list': similar_payload,
        'stats': stats_serializer.data
    })

