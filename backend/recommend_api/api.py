from django.http import HttpResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import *
from .serializers import *
import numpy as np
from scripts.tfidf_vector_store import TFIDF_MATRIX
from sklearn.metrics.pairwise import cosine_similarity

@api_view(['GET'])
def song_detail(request, id):
    try:
        song = Song.objects.get(id=id)
    except Song.DoesNotExist:
        return HttpResponse(status=404)

    if request.method == 'GET':
        serializer = SongSerializer(song)
        return Response(serializer.data)

@api_view(['POST'])
def similar_songs(request):
    try:
        query_song = Song.objects.get(id=request.POST.get('id'))
    except Song.DoesNotExist:
        return HttpResponse(status=404)
    
    query_vec = TFIDF_MATRIX[query_song.id].reshape(1, -1)
    similarities = cosine_similarity(query_vec, TFIDF_MATRIX).flatten()
    top_indices = np.argpartition(similarities, -11)[-11:]
    top_indices = top_indices[np.argsort(similarities[top_indices])[::-1]]
    top_indices = [i for i in top_indices if i != query_song.id][:10]
    similar_songs = Song.objects.filter(id__in=top_indices)

    query_serializer = SongSerializer(query_song)
    similar_serializer = SongSerializer(similar_songs, many=True)
    
    return Response({
        'query_song': query_serializer.data,
        'similar_songs': similar_serializer.data
    })

