import { useState } from 'react';
import { API_BASE_URL } from '../api';
import './Header.css'

export default function Header({onSearch}: { onSearch: (query: string, type: string) => void }) {
  const [searchType, setSearchType] = useState("track");
  const [searchQuery, setSearchQuery] = useState("");

  const inputPlaceholder = `Search for ${searchType}s...`;

  function onInputKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      onSearch(searchQuery, searchType)
    }
  }

  return (
    <div className="header">
      <h1>TasteMender</h1>
      <div>
        <input 
          value={searchQuery}
          placeholder={inputPlaceholder}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={onInputKeyDown}
        />
        <select value={searchType} onChange={e => setSearchType(e.target.value)}>
          <option value="track">Track</option>
          <option value="artist" disabled>Artist</option>
          <option value="album" disabled>Album</option>
        </select>
      </div>
      <div style={{textAlign: "right"}}>
        <a href={API_BASE_URL}>API</a>
        {/* <a href="#">About</a> */}
      </div>
    </div>
  );
}