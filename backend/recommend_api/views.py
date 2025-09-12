from django.conf import settings
from django.http import FileResponse, Http404
from django.shortcuts import render
from django.views.generic import View
from .models import *


class SPAView(View):
    """
    View that serves the front-end Single Page App
    """
    def get(self, request, *args, **kwargs):
        index = settings.BASE_DIR.parent / "frontend" / "dist" / "index.html"
        if index.exists():
            return FileResponse(open(index, "rb"))
        raise Http404("Build not found. Run `npm run build` in /frontend.")
