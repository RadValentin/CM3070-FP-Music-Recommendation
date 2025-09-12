import { useState, useEffect } from "react";
import "./App.css"
import type { Track } from "./types";
import { searchTracks, getTracks } from "./api";
import Header from "./components/Header";
import TrackList from "./components/TrackList";
import LoadingSpinner from "./components/LoadingSpinner";


type ResultsStatus = "TOP" | "SEARCH" | "ERROR"  | "EMPTY";
type ResultsState = {
  data: Track[];
  status: ResultsStatus;
}

function App() {
  const [results, setResults] = useState<ResultsState>({ data: [], status: "TOP" });
  const [isLoading, setLoading] = useState(false);

  function onSearch(query: string, type: string) {
    if (isLoading) {
      return;
    }
    if (!query) {
      loadTopTracks();
      return;
    }

    setLoading(true);
    if (type == "track") {
      searchTracks(query)
        .then(resp => {
          setResults({ 
            data: resp.results, 
            status: resp.results.length !== 0 ? "SEARCH" : "EMPTY"
          });
          setLoading(false);
        })
        .catch(err => {
          console.error("Error while searching for tracks: ", err);
          setResults({ data: [], status: "ERROR" });
          setLoading(false);
        });
    }
  }

  function loadTopTracks() {
    setLoading(true);
    getTracks("-submissions")
      .then(resp => {
        setResults({ 
          data: resp.results, 
          status: resp.results.length !== 0 ? "TOP" : "EMPTY"
        });
        setLoading(false);
      })
      .catch(err => {
        console.error("Error while searching loading top tracks:", err);
        setResults({ data: [], status: "ERROR" });
        setLoading(false);
      });
  }

  useEffect(() => {
    // Display top track only once on mount
    loadTopTracks();
  }, []);

  const renderContent = () => {
    if (isLoading) {
      return <div className="content"><LoadingSpinner /></div>;
    }

    if (results.status === "TOP") {
      return (
        <div className="content">
          <h2>Top tracks</h2>
          <TrackList tracks={results.data} onPlay={() => {}}></TrackList>
        </div>
      );
    }

    if (results.status === "SEARCH") {
      return (
        <div className="content">
          <h2>Search results</h2>
          <TrackList tracks={results.data} onPlay={() => {}}></TrackList>
        </div>
      );
    }

    if (results.status === "ERROR") {
      return <div className="content">There was an error while loading the tracks</div>;
    }

    return <div className="content">No results</div>;
  }


  return (
    <>
      <Header onSearch={onSearch}></Header>
      <div className="main">
        {renderContent()}
      </div>
      <div className="player">
        Player
      </div>
    </>
  )
}

export default App
