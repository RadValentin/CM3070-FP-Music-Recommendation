## Browse

- [x] `GET /api/v1/` - show available endpoints
- [x] `GET /api/v1/tracks/` - list all tracks (paginated)
- [x] `GET /api/v1/tracks/<mbid>/` - track details
- [x] `GET /api/v1/artists/` - list all artists (paginated)
- [x] `GET /api/v1/artists/<mbid>/` - artist details
- [x] `GET /api/v1/artists/<mbid>/tracks/` - all tracks by artist (paginated)
- [x] `GET /api/v1/artists/<mbid>/top-tracks/` - top tracks by artist (paginated)
- [x] `GET /api/v1/artists/<mbid>/albums/` - albums by artist, sort by release date
- [x] `GET /api/v1/albums/` - list all albums (paginated)
- [x] `GET /api/v1/albums/<mbid>/` - album details
- [x] `GET /api/v1/albums/<mbid>/art/`
  - Return album cover art from Cover Art Archive (CAA) <br/>
  https://coverartarchive.org/release/{MBID}/front <br/>
  https://coverartarchive.org/release-group/{MBID}/front <br/>
- [x] `GET /api/v1/genres/` - list all unique genre names in Rosamerica and Dortmund classifications
- [ ] Use caching for static resources (tracks, albums, artists, features): `ETag` and `Cache-Control`.
- [x] pagination for list endpoints

### Recommendation

- [ ] `GET /api/v1/tracks/<mbid>/sources/`
  - Best guess of matching a MusicBrainzID to a playable source
  - Ping MusicBrainz API to check if source is listed there
  - Search YouTube Data API v3, music category for title, artist
  - Return a list of possible sources
- [x] `GET /api/v1/tracks/<mbid>/features/` - show audio features from feature matrix for a track
- [ ] `POST /api/v1/recommend/`
**Request**
```json
{
  // listened previously
  "recent_track_ids": ["mbid","mbid","mbid"],
  "filters": { 
    "year": {"min":1995, "max":2005},
    // if the user "dislikes" a song, we can exclude the artist from future recommendations
    "exclude_artists": ["mbid"], 
    "same_genre": true,
    "genre_classification": "rosamerica"
  },
  // how much each audio feature should impact the similarity score
  "feature_weights": {
    "danceability": 0.5,
    "aggressiveness": 0.5
  },
  // how much similarity score should count vs track popularity in final scoring
  "total_weights": {
    "similarity": 0.7, 
    "popularity": 0.3
  },
  // how many results to return
  "limit": 1
}
```

**Response**
```json
{
  "results": [{
    "track_id":"mbid",
    "title": "Enter Sandman",
    "artist_id": "mbid",
    "artist": "Metallica",
    "album_id": "mbid",
    "album": "Metallica",
    "genre_rosamerica": "roc",
    "genre_dortmund": "electronic",
    "similarity": 0.82,
    "popularity": 0.9,
    "submissions": 5,
  }]
}
```
- [ ] `GET /api/v1/search/`
  - Query: `q` (string), `type` (track title/artist name/album name)
  - Paginated
- [ ] Disable caching for dynamic resources (/recommend/ results, searches).

### Filters
- [ ] Weights for audio features: 11 main ones + 5 mirex moods, values should be proportional and not all weights need to be provided (infer values)
- [ ] Genre guardrails options: Rosamerica (default), Dortmund, None
- [ ] Release year between min and max
- [ ] Weights for Similarity vs Popularity (what to prioritise)
- [ ] Randomness factor


## Discovery

- [ ] `GET /api/v1/artists/<mbid>/similar-artists/`

## Other
- Error shape: `{ "error": { "code":"INVALID_FILTER", "message":"year.min must be <= year.max" } }`
- Swagger API docs
- Docstrings
- CORS enabled
- Rate limit by: API key (HTTP `Authorization: Bearer <token>`) or anonymous with restrictive limits
  -  Return `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `Retry-After` headers
- Discogs API or YouTube thumbnail could also be used for cover art as last resorts