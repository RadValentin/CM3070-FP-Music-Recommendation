# mprof run ingest/debug_pipeline.py
import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "music_recommendation.settings")
django.setup()

from ingest import pipeline

pipeline.build_database(use_sample=True, show_log=False)