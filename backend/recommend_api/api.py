from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.parsers import JSONParser
from .models import *
from .serializers import *

@csrf_exempt
def song_detail(request, id):
    try:
        song = Song.objects.get(id=id)
    except Song.DoesNotExist:
        return HttpResponse(status=404)

    if request.method == 'GET':
        serializer = SongSerializer(song)
        return JsonResponse(serializer.data)