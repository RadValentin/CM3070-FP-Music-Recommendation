from django.urls import path, include, re_path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
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
    re_path(r"^(?!api/).*$", views.SPAView.as_view(), name="spa"),
    path("api/v1/", include(router.urls)),
    path("api/v1/genres/", api.GenreView.as_view(), name="genre-list"),
    path("api/v1/recommend/", api.RecommendView.as_view(), name="recommend"),
    path("api/v1/search/", api.SearchView.as_view(), name="search"),
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/v1/swagger-ui/", SpectacularSwaggerView.as_view(url_name="api:schema"), name="swagger-ui"),
    path("api/v1/redoc/", SpectacularRedocView.as_view(url_name="api:schema"), name="redoc"),
]
