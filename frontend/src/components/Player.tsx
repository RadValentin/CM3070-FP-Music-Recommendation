/* eslint-disable @typescript-eslint/no-explicit-any */
import React, { useEffect, useImperativeHandle, useRef, useState } from "react";
import type { Track, SimilarTrack, RecommendRequest } from "../types";
import { getTrackSources, getRecommendations } from "../api.ts"
import TrackItem from "./TrackItem.tsx";
import Filters from "./Filters.tsx";
import ImageLoader from "./ImageLoader.tsx";
import "./Player.css";

export interface PlayerRef {
  loadAndPlay: (track: Track) => void,
  reset: () => void,
  minimize: () => void,
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

type RecState = {
  similarList: SimilarTrack[],
  stats: any,
  listenedMbids: string[]
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

const defaultPlayerState: PlayerState = {
  track: undefined,
  isReady: false,
  isPlaying: false,
  isMaximized: false
};

const defaultRecState: RecState = {
  similarList: [],
  stats: {},
  listenedMbids: []
}

export default function Player({ ref }: PlayerProps) {
  // Child refs
  const iframeRef = useRef<any>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  // State refs - needed for methods called by YT player events (closure)
  const recListRef = useRef<SimilarTrack[]>([]);
  const recIDsRef = useRef<string[]>([]);
  // Component state
  const [playerState, setPlayerState] = useState<PlayerState>(defaultPlayerState);
  const [recState, setRecState] = useState<RecState>(defaultRecState);

  useEffect(() => {
    recListRef.current = recState.similarList;
    recIDsRef.current = recState.listenedMbids;
  }, [recState.similarList, recState.listenedMbids]);

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
            setPlayerState(playerState => ({...playerState, isReady: true}));
          },
          onStateChange: (e: any) => {
            const YT = window.YT;
            if (!YT) return;

            setPlayerState(playerState => ({
              ...playerState,
              isPlaying: e.data === YT.PlayerState.PLAYING
            }));

            // If video ended, play first recommendation
            if (e.data === YT.PlayerState.ENDED && recListRef.current.length > 0) {
              playTrack(recListRef.current[0]);
            }
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
      playTrack(track);
      setPlayerState(defaultPlayerState);
      setRecState(defaultRecState);
    },
    // Stop playback and reset state
    reset: () => {
      iframeRef.current?.stopVideo();
      setPlayerState(defaultPlayerState);
      setRecState(defaultRecState);
    },
    minimize: () => {
      setPlayerState(playerState => ({...playerState, isMaximized: false}));
    }
  }));

  const playTrack = (track: Track) => {
    console.log("I've been told to play this track:", track);
    getTrackSources(track.mbid).then(sources => {
      if (!sources[0]) {
        console.error(`No sources found for mbid ${track.mbid}`)
        return;
      }

      iframeRef.current.loadVideoById({ videoId: sources[0].id });
      setPlayerState(playerState => ({ ...playerState, track, isMaximized: true }));

      const recommendPayload: RecommendRequest = {
        mbid: track.mbid,
        listened_mbids: recIDsRef.current
      };
      getRecommendations(recommendPayload).then(data => {
        console.log("Got recommendations:", data);
        setRecState(recState => ({
          ...recState, 
          similarList: data.similar_list, 
          stats: data.stats,
          listenedMbids: [track.mbid, ...recState.listenedMbids]
        }))
      });
    });
  };

  const togglePlayback = () => {
    if (playerState.isPlaying) {
      iframeRef.current?.pauseVideo();
    } else {
      iframeRef.current?.playVideo();
    }
  };

  const toggleMaximize = () => {
    setPlayerState(playerState => ({...playerState, isMaximized: !playerState.isMaximized}));
  }

  const renderContent = () => {
    if (!playerState.track) {
      return;
    }

    const track = playerState.track;
    const artists = track.artists?.map(a => a.name).join(", ") || "Unknown artist";
    const album = track.album?.name ?? null;
    const year = track.album?.date ? new Date(track.album.date).getFullYear() : null;
    const artUrl = track.album?.links?.art ?? null
    const fallbackText = track.title?.charAt(0)?.toUpperCase() ?? "♪"

    return (
      <div className="content">
        <div className="coverart" aria-hidden="true">
          <ImageLoader src={artUrl} alt="cover art" fallback={fallbackText} />
        </div>
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
            { playerState.isPlaying 
              ? <i className="fa-solid fa-pause"></i> 
              : <i className="fa-solid fa-play"></i>
            }
          </button>
          <button type="button" className="button" aria-label="Minimize/Maximize" onClick={toggleMaximize}>
            { playerState.isMaximized 
              ? <i className="fa-solid fa-caret-down"></i> 
              : <i className="fa-solid fa-caret-up"></i>
            }
          </button>
        </div>
      </div>
    );
  };

  const renderRecommendations = () => {
    if (!recState.similarList || recState.similarList.length < 1) {
      return;
    }

    const firstRec = recState.similarList[0];
    const otherRec = recState.similarList.slice(1);

    return (
      <div className="player-recommendations">
        <div className="heading">Up Next:</div>
        <TrackItem key={firstRec.mbid} track={firstRec} onPlay={() => {playTrack(firstRec)}} />
        <div className="heading">Other recommendations:</div>
        {otherRec.map(track => <TrackItem key={track.mbid} track={track} onPlay={() => {playTrack(track)}} />)}
        <div className="heading">Stats:</div>
        <ul>
          <li>Candidate count: {recState.stats.candidate_count}</li>
          <li>Max similarity: {Number(recState.stats.max).toPrecision(5)}</li>
          <li>Mean similarity: {Number(recState.stats.mean).toPrecision(5)}</li>
          <li>P95: {Number(recState.stats.p95).toPrecision(5)}</li>
          <li>STD: {Number(recState.stats.std).toPrecision(5)}</li>
          <li>Cosine search time: {Number(recState.stats.search_time).toPrecision(5)}s</li>
          <li>Listened to {recState.listenedMbids.length} tracks</li>
        </ul>
      </div>
    );
  };

  const overlayClass = playerState.isMaximized ? "overlay maximized" : "overlay minimized";

  return (
    <div className="player">
      <div className={overlayClass}>
        <div className="player-filters">
          <Filters onChange={(payload) => { console.log("Filters changed", payload) }} />
        </div>
        <div className="player-iframe" ref={containerRef}></div>
        {renderRecommendations()}
      </div>
      {playerState.track && renderContent()}
    </div>
  );
}