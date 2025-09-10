from django.db import migrations
from django.contrib.postgres.operations import TrigramExtension


class Migration(migrations.Migration):
    dependencies = [("recommend_api", "0014_alter_track_artists_alter_track_title")]
    operations = [TrigramExtension()]



