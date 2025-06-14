from django.http import HttpResponse
from django.shortcuts import render
from .models import *

def index(request):
    songs = Song.objects.all().order_by('?')[:20]
    return render(request, 'index.html', {
        'songs': songs
    })