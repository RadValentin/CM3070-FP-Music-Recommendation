import factory
from factory.django import DjangoModelFactory
from random import randint, choice
from ..models import Artist, Album, Track


class ArtistFactory(DjangoModelFactory):
    class Meta:
        model = Artist
    
    musicbrainz_artistid = factory.Sequence(lambda n: f'artist-{n}')
    name = factory.Faker('name')


class AlbumFactory(DjangoModelFactory):
    class Meta:
        model = Album
    
    musicbrainz_albumid = factory.Sequence(lambda n: f'album-{n}')
    name = factory.Faker('sentence', nb_words=2)
    #artists = factory.SubFactory(ArtistFactory)   
    date = factory.Faker('date')


class TrackFactory(DjangoModelFactory):
    class Meta:
        model = Track
    
    musicbrainz_recordingid = factory.Sequence(lambda n: f'track-{n}')
    album = factory.SubFactory(AlbumFactory)
    #artists = factory.SubFactory(ArtistFactory)
    title = factory.Faker('sentence', nb_words=2)
    duration = randint(1, 1000)
    genre_dortmund = choice([
        'electronic','folkcountry','blues','jazz','alternative','rock','raphiphop','pop','funksoulrnb'
    ])
    genre_rosamerica = choice(['rhy','dan','pop','roc','cla','hip','jaz','spe'])
    file_path = factory.Faker('file_path', depth=3, extension='json')