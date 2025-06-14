from django.urls import path
from .views import index
from . import api

urlpatterns = [
    path('', index, name='index'),
    path('api/song/<int:id>/', api.song_detail)
]