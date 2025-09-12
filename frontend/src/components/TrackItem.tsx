import { useState } from "react";
import "./TrackItem.css";
import type { Track } from "../types";

type Props = {
  track: Track;
  onPlay?: (track: Track) => void;
};

export default function TrackItem({ track, onPlay }: Props) {
  const [imgError, setImgError] = useState(false);

  const artists = track.artists?.map(a => a.name).join(", ") || "Unknown artist";
  const album = track.album?.name ?? null;
  const year = track.album?.date ? new Date(track.album.date).getFullYear() : null;
  const artUrl= track.album?.links?.art ?? null

  return (
    <div
      className={"track-item"}
      aria-label={`${track.title} by ${artists}`}
    >
      <div className="coverart" aria-hidden="true">
        {artUrl && !imgError ? (
          <img src={artUrl} alt="" loading="lazy" onError={() => setImgError(true)} />
        ) : (
          <div className="coverart-fallback">
            {track.title?.charAt(0)?.toUpperCase() ?? "♪"}
          </div>
        )}
      </div>

      <div className="meta">
        <div className="title" title={track.title}>{track.title}</div>
        <div className="artist-album">
          <span className="artist" title={artists}>{artists}</span>
          {album && <> • <span className="album" title={album}>{album}</span></>}
          {year && <> • <span className="year">{year}</span></>}
        </div>
        <div className="badges">
          <span className="badge">{track.genre_dortmund}</span>
          <span className="badge">{track.genre_rosamerica}</span>
          <span className="badge" title="Submissions">subs: {track.submissions}</span>
        </div>
      </div>

      <div className="actions">
        {onPlay && (
          <button
            type="button"
            className="button"
            aria-label="Play"
            onClick={() => onPlay(track)}
          >
            <i className="fa-solid fa-play"></i>
          </button>
        )}
      </div>
    </div>
  );
}
