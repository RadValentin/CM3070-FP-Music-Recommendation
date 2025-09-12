import type { Track } from "../types";
import TrackItem from "./TrackItem";

type Props = {
  tracks: Track[];
  onPlay?: (track: Track) => void;
};

export default function TrackList({tracks, onPlay}: Props) {
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