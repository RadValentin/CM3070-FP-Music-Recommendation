import React, { useImperativeHandle } from "react";
import type { Track } from "../types";
import "./Player.css";

export interface PlayerRef {
  loadAndPlay: (track: Track) => void,
}

export type PlayerProps = {
  ref: React.RefObject<PlayerRef | null>
}

export default function Player({ ref }: PlayerProps) {
  useImperativeHandle(ref, () => ({
    loadAndPlay: (track: Track) => { 
      console.log("I've been told to play this track:", track) 
    }
  }));


  return (
    <div className="player">Player</div>
  );
}