import { useEffect, useState } from "react";
import { getTracks } from "./api";
import type { Track } from "./types";

export default function TrackList() {
  const [tracks, setTracks] = useState<Track[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getTracks()
      .then((data) => setTracks(data.results))
      .catch((err) => console.error("API error:", err))
      .finally(() => { setLoading(false); });
  }, []);

  if (loading) {
    return <p>Loading...</p>;
  }

  return (
    <ul>
      {tracks.map((track) => (
        <li key={track.mbid}>
          {track.title} - {track.artists[0].name}
        </li>
      ))}
    </ul>
  );
}
