from django.http import HttpResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import *
from .serializers import *

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
    try:
        query_song = Track.objects.get(musicbrainz_recordingid=request.POST.get('musicbrainz_recordingid'))
    except Track.DoesNotExist:
        return HttpResponse(status=404)
    
    #query_vec = TFIDF_MATRIX[query_song.id].reshape(1, -1)
    #similarities = cosine_similarity(query_vec, TFIDF_MATRIX).flatten()
    #top_indices = np.argpartition(similarities, -11)[-11:]
    #top_indices = top_indices[np.argsort(similarities[top_indices])[::-1]]
    top_indices = [i for i in top_indices if i != query_song.id][:10]
    similar_songs = Track.objects.filter(id__in=top_indices)

    query_serializer = TrackSerializer(query_song)
    similar_serializer = TrackSerializer(similar_songs, many=True)
    
    return Response({
        'query_song': query_serializer.data,
        'similar_songs': similar_serializer.data
    })

