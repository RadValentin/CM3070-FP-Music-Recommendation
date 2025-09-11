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
        """
        Augment the default root response to contain:
        - Info (name/version)
        - DRF router links
        - Extra links that were defined outside the router
        """
        resp = super().get(request, *args, **kwargs)

        info = OrderedDict()
        info["message"] = "Welcome to the TasteMender API"
        info["version"] = "v1"
        data = OrderedDict(**info, **resp.data)

        extras = OrderedDict()
        extras["genres"] = request.build_absolute_uri(reverse("api:genre-list"))
        extras["recommend"] = request.build_absolute_uri(reverse("api:recommend"))
        extras["search"] = request.build_absolute_uri(reverse("api:search"))
        extras["documentation"] = {
           "schema": request.build_absolute_uri(reverse("api:schema")),
           "swagger-ui": request.build_absolute_uri(reverse("api:swagger-ui")),
           "redoc": request.build_absolute_uri(reverse("api:redoc")),
        }
        # merge extras at the bottom
        data = OrderedDict(**data, **extras)
        return Response(data)

class APIRouter(DefaultRouter):
    APIRootView = CustomAPIRootView
