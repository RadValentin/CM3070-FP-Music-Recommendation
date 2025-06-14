from django.urls import path
from .views import index
from . import api

urlpatterns = [
    path('', index, name='index'),
    path('api/song/<int:id>/', api.song_detail, name='song_detail_api'),
    path('api/similar/', api.similar_songs, name='similar_songs_api')
]