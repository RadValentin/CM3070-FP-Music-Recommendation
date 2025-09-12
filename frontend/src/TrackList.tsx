import { useEffect, useState } from "react";
import { getTracks } from "./api";

type Track = {
  id: string | number;
  title: string;
  artists: { name: string }[];
};

export default function TrackList() {
  const [tracks, setTracks] = useState<Track[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getTracks()
      .then((data) => setTracks(data))
      .catch((err) => console.error("API error:", err))
      .finally(() => { setLoading(false); });
  }, []);

  if (loading) {
    return <p>Loading...</p>;
  }

  return (
    <ul>
      {tracks.map((track) => (
        <li key={track.id}>
          {track.title} - {track.artists[0].name}
        </li>
      ))}
    </ul>
  );
}
