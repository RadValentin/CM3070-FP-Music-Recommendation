from django.urls import path, include, reverse
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter, Route
from recommend_api.router import APIRouter
from recommend_api import views
from recommend_api import api

router = APIRouter()
router.register(r"tracks", api.TrackViewSet, basename="track")
router.register(r"albums", api.AlbumViewSet, basename="album")
router.register(r"artists", api.ArtistViewSet, basename="artist")

app_name = "api"
urlpatterns = [
    path("", views.index, name="index"),
    path("api/v1/", include(router.urls)),
    path("api/v1/genres/", api.GenreView.as_view(), name="genre-list"),
    path("api/v1/recommend/", api.RecommendView.as_view(), name="recommend"),
    path("api/v1/search/", api.SearchView.as_view(), name="search")
]
