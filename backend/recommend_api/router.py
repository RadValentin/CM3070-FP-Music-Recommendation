from collections import OrderedDict
from django.urls import reverse
from django.utils.safestring import mark_safe
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter, APIRootView

class CustomAPIRootView(APIRootView):
    def get_view_name(self) -> str:
        return "TasteMender API"

    def get_view_description(self, html=False) -> str:
        text = "A stateless music recommendation REST API"
        if html:
            return mark_safe(f"<p>{text}</p>")
        else:
            return text

    def get(self, request, *args, **kwargs):
        resp = super().get(request, *args, **kwargs)

        extras = OrderedDict()
        extras["message"] = "Welcome to the TasteMender API"
        extras["version"] = "v1"

        extras["genres"] = request.build_absolute_uri(reverse("api:genre-list"))
        extras["recommend"] = request.build_absolute_uri(reverse("api:recommend"))
        extras["search"] = request.build_absolute_uri(reverse("api:search"))

        # merge extras at the top
        data = OrderedDict(**extras, **resp.data)
        return Response(data)

class APIRouter(DefaultRouter):
    APIRootView = CustomAPIRootView
