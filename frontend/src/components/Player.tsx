/* eslint-disable @typescript-eslint/no-explicit-any */
import React, { useEffect, useImperativeHandle, useRef, useState } from "react";
import type { Track } from "../types";
import { getTrackSources } from "../api.ts"
import "./Player.css";

export interface PlayerRef {
  loadAndPlay: (track: Track) => void,
  reset: () => void,
}

export type PlayerProps = {
  ref: React.RefObject<PlayerRef | null>
}

type PlayerState = {
  track: Track | undefined,
  isReady: boolean,
  isPlaying: boolean,
  isMaximized: boolean
}

declare global {
  interface Window {
    YT?: any;
    onYouTubeIframeAPIReady?: () => void;
  }
}

const loadYouTubeIframeAPI = (() => {
  let p: Promise<void> | null = null;
  return () => {
    if (window.YT && window.YT.Player) return Promise.resolve();
    if (p) return p;
    p = new Promise<void>((resolve) => {
      const tag = document.createElement("script");
      tag.src = "https://www.youtube.com/iframe_api";
      document.head.appendChild(tag);
      window.onYouTubeIframeAPIReady = () => resolve();
    });
    return p;
  };
})();

const defaultState: PlayerState = {
  track: undefined,
  isReady: false,
  isPlaying: false,
  isMaximized: false
};

export default function Player({ ref }: PlayerProps) {
  const iframeRef = useRef<any>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [state, setState] = useState<PlayerState>(defaultState);

  // Load the YouTube iframe player on first mount
  useEffect(() => {
    let mounted = true;

    (async () => {
      await loadYouTubeIframeAPI();
      if (!mounted || !containerRef.current) return;

      iframeRef.current = new window.YT.Player(containerRef.current, {
        height: "360",
        width: "640",
        playerVars: {
          rel: 0,
          playsinline: 1,
        },
        events: {
          onReady: () => { 
            setState(state => ({...state, isReady: true}));
          },
          onStateChange: (e: any) => {
            const YT = window.YT;
            if (!YT) return;

            setState(state => ({
              ...state,
              isPlaying: e.data === YT.PlayerState.PLAYING
            }));
          }
        }
      });
    })();

    return () => {
      mounted = false;
      try {
        iframeRef.current?.destroy?.();
      } catch { 
        console.error("Could not destroy iframe player");
      }
    };
  }, []);

  // Methods callable by parent component
  useImperativeHandle(ref, () => ({
    // Play a track
    loadAndPlay: (track: Track) => { 
      console.log("I've been told to play this track:", track);
      getTrackSources(track.mbid).then(sources => {
        if (!sources[0]) {
          console.error(`No sources found for mbid ${track.mbid}`)
          return;
        }

        iframeRef.current.loadVideoById({ videoId: sources[0].id });
        setState(state => ({ ...state, track, isMaximized: true }));
      })
    },
    // Stop playback and reset state
    reset: () => {
      try {
        iframeRef.current?.stopVideo?.();
      } catch (e) {
        console.warn("Could not stop video:", e);
      }
      setState(defaultState);
    }
  }));

  const togglePlayback = () => {
    if (state.isPlaying) {
      iframeRef.current?.pauseVideo();
    } else {
      iframeRef.current?.playVideo();
    }
  };

  const toggleMaximize = () => {
    setState(state => ({...state, isMaximized: !state.isMaximized}));
  }

  const renderContent = () => {
    if (!state.track) {
      return;
    }

    const track = state.track;
    const artists = track.artists?.map(a => a.name).join(", ") || "Unknown artist";
    const album = track.album?.name ?? null;
    const year = track.album?.date ? new Date(track.album.date).getFullYear() : null;

    return (
      <div className="content">
        <div className="meta">
          <div className="title" title={track.title}>{track.title}</div>
          <div className="artist-album">
            <span className="artist" title={artists}>{artists}</span>
            {album && <> • <span className="album" title={album}>{album}</span></>}
            {year && <> • <span className="year">{year}</span></>}
          </div>
        </div>
        
        <div>
          <button type="button" className="button" aria-label="Play/Pause" onClick={togglePlayback}>
            { state.isPlaying 
              ? <i className="fa-solid fa-pause"></i> 
              : <i className="fa-solid fa-play"></i>
            }
          </button>
          <button type="button" className="button" aria-label="Minimize/Maximize" onClick={toggleMaximize}>
            { state.isMaximized 
              ? <i className="fa-solid fa-caret-down"></i> 
              : <i className="fa-solid fa-caret-up"></i>
            }
          </button>
        </div>
      </div>
    );
  };

  const overlayClass = state.isMaximized ? "overlay maximized" : "overlay minimized";

  return (
    <div className="player">
      <div className={overlayClass}>
        <div className="filters"></div>
        <div className="iframe" ref={containerRef}></div>
        <div className="recommendations"></div>
      </div>
      {state.track && renderContent()}
    </div>
  );
}