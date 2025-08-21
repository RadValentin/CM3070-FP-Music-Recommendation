from django.http import HttpResponse
from django.shortcuts import render
from .models import *

def index(request):
    tracks = Track.objects.prefetch_related('artists').all().order_by('?')[:20]
    return render(request, 'index.html', {
        'tracks': tracks
    })