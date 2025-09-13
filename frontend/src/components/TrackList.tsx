import type { Track } from "../types";
import TrackItem from "./TrackItem";

type TrackListProps = {
  tracks: Track[];
  onPlay?: (track: Track) => void;
};

export default function TrackList({tracks, onPlay}: TrackListProps) {
  return (
    <>
      {tracks.map((track: Track) => (
        <TrackItem
          key={track.mbid}
          track={track}
          {...(onPlay ? { onPlay } : {})}
        />
      ))}
    </>
  )
}