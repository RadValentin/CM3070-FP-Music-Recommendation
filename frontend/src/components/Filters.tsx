/* eslint-disable @typescript-eslint/no-explicit-any */
import { useState, useEffect } from "react";
import "./Filters.css";

type FiltersProps = {
    onChange: (payload: {
      filters?: any;
      feature_weights?: any; 
      total_weights?: any;
    }) => void;
}

const defaultFiltersState = {
   same_genre: true, same_decade: true, genre_classification: "rosamerica"
}

const FEATURES = ["danceability", "aggressiveness", "happiness", "sadness", "relaxedness", "partyness",
  "acousticness", "electronicness", "instrumentalness", "tonality", "brightness", "moods_mirex_1",
  "moods_mirex_2", "moods_mirex_3", "moods_mirex_4", "moods_mirex_5"];
const defaultFeatureWeightsState = Object.fromEntries(
  FEATURES.map(f => [f, 1])
);

const defaultTotalWeightsState = {
  similarity: 0.7, popularity: 0.3
}

export default function Filters({ onChange }: FiltersProps) {
  const [filters, setFilters] = useState(defaultFiltersState);
  const [totalWeights, setTotalWeights] = useState(defaultTotalWeightsState);
  const [featureWeights, setFeatureWeights] = useState(defaultFeatureWeightsState);

  const updateSimilarity = (val: number) => {
    setTotalWeights({ similarity: val, popularity: +(1 - val).toFixed(4) });
  };

  const updatePopularity = (val: number) => {
    setTotalWeights({ similarity: +(1 - val).toFixed(4), popularity: val });
  };

  const toggleFilter = (key: "same_genre" | "same_decade") => {
    setFilters(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const updateClassification = (value: string) => {
    const val = value === "dortmund" ? "dortmund" : "rosamerica";
    setFilters(prev => ({ ...prev, genre_classification: val }));
  };

  const updateFeatureWeight = (key: string, value: number) => {
    setFeatureWeights(prev => ({...prev, [key]: value}));
  }

  const resetState = () => {
    setFilters(defaultFiltersState);
    setTotalWeights(defaultTotalWeightsState);
    setFeatureWeights(defaultFeatureWeightsState);
  };

  // When filters change, call the parent with updated payload
  const handleChangeEnd = () => {
    onChange({
      filters: {
        same_genre: filters.same_genre,
        same_decade: filters.same_decade,
        genre_classification: filters.genre_classification
      },
      total_weights: {
        similarity: +totalWeights.similarity.toFixed(4),
        popularity: +totalWeights.popularity.toFixed(4),
      },
      feature_weights: featureWeights
    });
  };

  // For checkboxes and select automatically call the parent on state updates
  useEffect(() => {
    handleChangeEnd();
  }, [filters]);

  return (
    <div className="filters">
      <div className="heading">Filters</div>
      <label>
        <span>Same genre</span>
        <input
          type="checkbox"
          checked={filters.same_genre}
          onChange={() => toggleFilter("same_genre")}
        />
      </label>
      <label>
        <span>Same decade</span>
        <input
          type="checkbox"
          checked={filters.same_decade}
          onChange={() => toggleFilter("same_decade")}
        />
      </label>
      <label>
        <span>Genre classification</span>
        <select 
          value={filters.genre_classification} 
          onChange={e => {updateClassification(e.target.value)}}
        >
          <option value="rosamerica">rosamerica</option>
          <option value="dortmund">dortmund</option>
        </select>
      </label>

      <div className="heading">Total Weights</div>
      <label>
        <span>Similarity</span>
        <input 
          className="slider" type="range" min={0} max={1} step={0.1}
          value={totalWeights.similarity}
          onChange={e => updateSimilarity(parseFloat(e.target.value))}
          onMouseUp={handleChangeEnd}
          onKeyUp={handleChangeEnd}
          onTouchEnd={handleChangeEnd}  
        />
      </label>
      <label>
        Popularity
        <input 
          className="slider" type="range" min={0} max={1} step={0.1}
          value={totalWeights.popularity}
          onChange={e => updatePopularity(parseFloat(e.target.value))}   
          onMouseUp={handleChangeEnd}
          onKeyUp={handleChangeEnd}
          onTouchEnd={handleChangeEnd}  
        />
      </label>
      
      <div className="heading">Feature Weights</div>
      {FEATURES.map(feature_name => (
        <label key={feature_name}>
          <span>{feature_name}</span>
          <input 
            className="slider" type="range" min={0} max={2} step={0.1}
            value={featureWeights[feature_name]}
            onChange={e => updateFeatureWeight(feature_name, parseFloat(e.target.value))}   
            onMouseUp={handleChangeEnd}
            onKeyUp={handleChangeEnd}
            onTouchEnd={handleChangeEnd}  
          />
        </label>
      ))}

      <button className="button" onClick={resetState}>RESET</button>
    </div>
  )
}