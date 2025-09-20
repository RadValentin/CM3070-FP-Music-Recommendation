import axios from "axios";
import type {
  Track, TrackFeaturesResponse, Artist, Paginated, RecommendRequest, RecommendResponse, 
  SearchResponse, Album
} from "./types";

export const API_BASE_URL = import.meta.env.VITE_API_BASE || "http://localhost:8000/api/v1/"

const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
});

export async function getTracks(ordering?: string) {
  const params: Record<string, string> = {};
  if (ordering) params.ordering = ordering;

  return api.get<Paginated<Track>>(`tracks/`, {params}).then(resp => resp.data);
}

export function getTrack(mbid: string) {
  return api.get<Track>(`tracks/${mbid}/`).then(resp => resp.data);
}

export function getTrackFeatures(mbid: string) {
  return api.get<TrackFeaturesResponse>(`tracks/${mbid}/features/`).then(resp => resp.data);
}

export function getTrackSources(mbid: string) {
  return api.get(`tracks/${mbid}/sources/`).then(resp => resp.data.sources);
}

export async function getArtists() {
  return api.get<Paginated<Artist>>(`artists/`).then(resp => resp.data);
}

export function getArtist(mbid: string) {
  return api.get<Artist>(`artists/${mbid}/`).then(resp => resp.data);
}

export function getArtistTracks(mbid: string) {
  return api.get<Paginated<Track>>(`artists/${mbid}/tracks/`).then(resp => resp.data);
}

export function getArtistTopTracks(mbid: string) {
  return api.get<Paginated<Track>>(`artists/${mbid}/top-tracks/`).then(resp => resp.data);
}

export function getArtistAlbums(mbid: string) {
  return api.get<Paginated<Album>>(`artists/${mbid}/albums/`).then(resp => resp.data);
}

export async function getAlbums() {
  return api.get<Paginated<Album>>(`albums/`).then(resp => resp.data);
}

export function getAlbum(mbid: string) {
  return api.get<Album>(`albums/${mbid}/`).then(resp => resp.data);
}

export function getAlbumArt(mbid: string) {
  return api.get<string>(`albums/${mbid}/art/`).then(resp => resp.data);
}

export function getRecommendations(body: RecommendRequest) {
  return api.post<RecommendResponse>("recommend/", body).then(resp => resp.data);
}

export function searchTracks(query: string, limit: number=25) {
  return api.get<SearchResponse<Track>>(`search/?type=track&q=${encodeURIComponent(query)}&limit=${limit}`)
    .then(resp => resp.data);
}

export default api;