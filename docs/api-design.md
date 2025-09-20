## Browse

- [x] `GET /api/v1/` - show available endpoints
- [x] `GET /api/v1/tracks/` - list all tracks (paginated)
  - Ordering filter querystring param: `title`, `album__date`
- [x] `GET /api/v1/tracks/<mbid>/` - track details
- [x] `GET /api/v1/artists/` - list all artists (paginated)
  - Ordering filter querystring param: `name`
- [x] `GET /api/v1/artists/<mbid>/` - artist details
- [x] `GET /api/v1/artists/<mbid>/tracks/` - all tracks by artist (paginated)
- [x] `GET /api/v1/artists/<mbid>/top-tracks/` - top tracks by artist (paginated)
- [x] `GET /api/v1/artists/<mbid>/albums/` - albums by artist, sort by release date
- [x] `GET /api/v1/albums/` - list all albums (paginated)
  - Ordering filter querystring param: `name`, `date`
- [x] `GET /api/v1/albums/<mbid>/` - album details
- [x] `GET /api/v1/albums/<mbid>/art/`
  - Return album cover art from Cover Art Archive (CAA) <br/>
  https://coverartarchive.org/release/{MBID}/front <br/>
  https://coverartarchive.org/release-group/{MBID}/front <br/>
- [x] `GET /api/v1/genres/` - list all unique genre names in Rosamerica and Dortmund classifications
- [ ] Use caching for static resources (tracks, albums, artists, features): `ETag` and `Cache-Control`.
- [x] pagination for list endpoints (through `"DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination"`)
- [x] list endpoints should specify what sub-routes are available, ex: `tracks/`, `/albums/` for `/artists/` (HATEOAS)
 
### Recommendation

- [x] `GET /api/v1/tracks/<mbid>/sources/`
  - Best guess of matching a MusicBrainzID to a playable source
  - Ping MusicBrainz API to check if source is listed there
  - Search YouTube Data API v3, music category for title, artist
  - Return a list of possible sources
- [x] `GET /api/v1/tracks/<mbid>/features/` - show audio features from feature matrix for a track
- [x] `POST /api/v1/recommend/`
**Request**
```js
{
  // target track that we compare against others
  "mbid": "mbid",
  // listened previously, excluded from results
  "listened_mbids": ["mbid","mbid","mbid"],
  "filters": { 
    // if the user "dislikes" a song, we can exclude the artist from future recommendations
    "exclude_artists": ["mbid"], 
    "same_genre": true,
    "same_decade": true,
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
  "limit": 10
}
```

**Response**
```json
{
  "target_track": {
    "mbid": "62c2e20a-559e-422f-a44c-9afa7882f0c4",
    "title": "Enter Sandman"
  },
  "similar_list": [
    {
      "mbid": "9420c245-10aa-43bf-a583-08f0219e5666",
      "title": "Don't Tread on Me",
      "similarity": 0.9326974749565125
    }
  ],
  "stats": {
    "candidate_count": 79448,
    "search_time": 0.008000850677490234,
    "mean": 0.4038538336753845,
    "std": 0.3162822425365448,
    "p95": 0.8052042126655579,
    "max": 0.9930822849273682
  }
}
```
- [x] `GET /api/v1/search/`
  - Query: `q` (string), `type` (track title/artist name/album name)
  - <s>Paginated</s> (Update: pagination is very costly, return a good number of results instead and paginate on client)
- [ ] Disable caching for dynamic resources (/recommend/ results, searches).

### Filters
- [ ] Weights for audio features: 11 main ones + 5 mirex moods, values should be proportional and not all weights need to be provided (infer values)
- [x] Genre guardrails options: Rosamerica (default), Dortmund, None
- [x] Same decade guardrails
- [x] Weights for Similarity vs Popularity (what to prioritise)
- [ ] Randomness factor


## Discovery

- [ ] `GET /api/v1/artists/<mbid>/similar-artists/`

## Other
- [x] Error shape: `{ "error": { "code":"INVALID_FILTER", "message":"year.min must be <= year.max" } }`
- [x] Swagger API docs
- [x] Docstrings
- [ ] CORS enabled
- [ ] Rate limit by: API key (HTTP `Authorization: Bearer <token>`) or anonymous with restrictive limits
  - Return `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `Retry-After` headers
- [ ] Discogs API or YouTube thumbnail could also be used for cover art as last resorts