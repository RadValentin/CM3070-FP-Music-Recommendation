from django.urls import path
from .views import index
from . import api

urlpatterns = [
    path('', index, name='index'),
    path('api/track/<str:musicbrainz_recordingid>/', api.track_detail, name='track_detail_api'),
    path('api/similar/', api.similar_tracks, name='similar_tracks_api')
]