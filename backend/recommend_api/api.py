from django.http import HttpResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import *
from .serializers import *
import recommend_api.recommender as rec


@api_view(['GET'])
def track_detail(request, musicbrainz_recordingid):
    try:
        print(f'MBID:{musicbrainz_recordingid}')
        song = Track.objects.get(musicbrainz_recordingid=musicbrainz_recordingid)
    except Track.DoesNotExist:
        return HttpResponse(status=404)

    if request.method == 'GET':
        serializer = TrackSerializer(song)
        return Response(serializer.data)

@api_view(['POST'])
def similar_tracks(request):
    target_mbid = request.POST.get('musicbrainz_recordingid')

    if not target_mbid:
        return Response({"detail": "Missing 'mbid' parameter."}, status=status.HTTP_400_BAD_REQUEST)

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
    similar_tracks = []
    similar_counter = 0
    for track in top_tracks:
        track_obj = track_map.get(track["mbid"])
        artist = track_obj.artists.first()
        artist_name = artist.name if artist else "Unknown Artist"
        
        if similar_counter >= 5:
            break
        elif track["mbid"] == target_mbid:
            # Skip is target track is encountered again somehow
            continue
        elif artist_name == target_artist.name and track_obj.title == target_track.title:
            # Skip if it's the same song by the same artist as the target track
            continue
        else:
            similar_counter += 1
        
        similar_tracks.append(track_obj)


    target_serializer = SimilarTrackSerializer(target_track)
    similar_serializer = SimilarTrackSerializer(similar_tracks, many=True)
    stats_serializer = RecommendStatsSerializer(recommendations["stats"])
    
    return Response({
        'target_track': target_serializer.data,
        'similar_tracks': similar_serializer.data,
        'stats': stats_serializer.data
    })

