/** Shared */
export type UUID = string;
export type IsoDate = string;

/** Links (HATEOAS) */
export interface ArtistLinks {
  self: string;
  tracks: string;
  "top-tracks": string;
  albums: string;
}

export interface AlbumLinks {
  self: string;
  art: string;
}

export interface TrackLinks {
  self: string;
  features: string;
  sources: string;
}

/** Core resources (match Model/Serializer fields) */
export interface Artist {
  // musicbrainz_artistid
  mbid: UUID;           
  name: string;
  links: ArtistLinks;
}

export interface Album {
  // musicbrainz_albumid
  mbid: UUID;
  name: string;
  artists: Artist[];
  date: IsoDate | null;
  links: AlbumLinks;
}

export interface Track {
  // musicbrainz_recordingid
  mbid: UUID;
  title: string;
  artists: Artist[];
  album?: Album | null;
  duration: number;
  genre_dortmund: string;
  genre_rosamerica: string;
  submissions: number;
  links: TrackLinks;
}

/** Variants & aux responses */
export interface SimilarTrack extends Track {
  similarity: number;
}

export interface GenreResponse {
  genre_dortmund: string[];
  genre_rosamerica: string[];
}

export interface TrackFeaturesResponse {
  track: Track;
  features: Record<string, unknown>;
  raw_features: Record<string, unknown>;
}

/** Recommendation API */
export interface RecommendStats {
  candidate_count: number;
  search_time: number;
  mean: number | null;
  std: number | null;
  p95: number | null;
  max: number | null;
}

export interface RecommendResponse {
  target_track: Track;
  similar_list: SimilarTrack[];
  stats: RecommendStats;
}

export type GenreClassification = "rosamerica" | "dortmund";

export interface RecommendFilters {
  // list of artist MBIDs (strings)
  exclude_artists?: string[];
  same_genre?: boolean;
  same_decade?: boolean;
  genre_classification?: GenreClassification;
}

export interface RecommendRequest {
  mbid: UUID;
  listened_mbids?: UUID[];
  filters?: RecommendFilters;
  feature_weights?: Record<string, number>;
  total_weights?: Record<string, number>;
  limit?: number;
}

/** Search API */
export type SearchType = "track" | "artist" | "album";

export interface SearchResponse<T = Record<string, unknown>> {
  query: string;
  type: SearchType;
  use_trigram: boolean;
  response_time: number;
  count: number;
  results: T[];
}

/** DRF pagination helper */
export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
