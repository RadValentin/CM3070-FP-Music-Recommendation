import factory
from factory.django import DjangoModelFactory
from random import randint, choice
from recommend_api.models import Artist, Album, Track


class ArtistFactory(DjangoModelFactory):
    class Meta:
        model = Artist

    musicbrainz_artistid = factory.Sequence(lambda n: f"artist-{n}")
    name = factory.Faker("name")


class AlbumFactory(DjangoModelFactory):
    class Meta:
        model = Album

    musicbrainz_albumid = factory.Sequence(lambda n: f"album-{n}")
    name = factory.Faker("sentence", nb_words=2)
    date = factory.Faker("date")


class TrackFactory(DjangoModelFactory):
    class Meta:
        model = Track

    musicbrainz_recordingid = factory.Sequence(lambda n: f"track-{n}")
    album = factory.SubFactory(AlbumFactory)
    title = factory.Faker("sentence", nb_words=2)
    duration = factory.LazyAttribute(lambda o: randint(1, 1000))
    genre_dortmund = factory.LazyAttribute(lambda o: choice([
        "electronic", "folkcountry", "blues", "jazz", "alternative", "rock", "raphiphop", "pop", 
        "funksoulrnb",
    ]))
    genre_rosamerica =  factory.LazyAttribute(lambda o: choice([
        "rhy", "dan", "pop", "roc", "cla", "hip", "jaz", "spe"
    ]))
    submissions = factory.LazyAttribute(lambda o: randint(1, 100))
    file_path = factory.Faker("file_path", depth=3, extension="json")
