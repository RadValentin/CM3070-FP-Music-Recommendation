from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import api

router = DefaultRouter()
router.register(r"tracks", api.TrackViewSet, basename="track")
router.register(r"albums", api.AlbumViewSet, basename="album")
router.register(r"artists", api.ArtistViewSet, basename="artist")

app_name = "api"
urlpatterns = [
    path("", views.index, name="index"),
    path("api/v1/recommend", api.RecommendView.as_view(), name="recommend"),
    path("api/v1/", include(router.urls)),
]