// src/pages/LandingPage.jsx
import { useEffect, useState } from "react";
import "./LandingPage.css";
import citiesCsv from "../assets/csv/cities.csv?raw";

function LandingPage({ onStart, onUpload, formData, onChange }) {
  const [cities, setCities] = useState([]);
  const [error, setError] = useState("");

  // Parse City column from CSV once
  useEffect(() => {
    if (!citiesCsv) return;

    const lines = citiesCsv
      .split("\n")
      .map((l) => l.trim())
      .filter((l) => l.length > 0);

    const rows = lines.slice(1); // skip header row

    const parsed = rows
      .map((line) => {
        // find first three commas: city,state_id,population,City
        const first = line.indexOf(",");
        if (first === -1) return null;
        const second = line.indexOf(",", first + 1);
        if (second === -1) return null;
        const third = line.indexOf(",", second + 1);
        if (third === -1) return null;

        // everything after the third comma is the City field
        let cityField = line.slice(third + 1).trim(); // e.g. `"Madison, WI"`

        if (
          cityField.startsWith('"') &&
          cityField.endsWith('"') &&
          cityField.length > 1
        ) {
          cityField = cityField.slice(1, -1); // remove surrounding quotes
        }

        return cityField || null;
      })
      .filter(Boolean);

    setCities(parsed);
  }, []);

  const normalize = (s) => s.trim().toLowerCase();

  const handleBeginSearch = () => {
    if (!formData.origin || !formData.destination) {
      setError("Please choose both an origin and a destination city.");
      return;
    }

    const originValid = cities.some(
      (c) => normalize(c) === normalize(formData.origin)
    );
    const destValid = cities.some(
      (c) => normalize(c) === normalize(formData.destination)
    );

    if (!originValid || !destValid) {
      setError(
        "Cities must match one from the list (e.g. “Madison, WI”). Start typing and pick a suggestion."
      );
      return;
    }

    setError("");
    onStart(); // go to next page; formData already contains origin/destination
  };

  const handleFieldChange = (field, value) => {
    setError("");
    onChange(field, value);
  };

  return (
    <div className="landing-page">
      {/* Top bar */}
      <header className="landing-topbar">
        <div className="landing-topbar-inner">
          <div className="landing-logo-pill">WhatsTheMoove.com</div>

          <p className="landing-topbar-text">
            Learn how{" "}
            <span className="landing-topbar-brand">WhatsTheMoove?</span> makes
            moving the easiest part of your job search →
          </p>
        </div>
      </header>

      {/* Hero section */}
      <section className="landing-hero">
        <div className="landing-hero-overlay">
          <h1 className="landing-hero-title">
            <p1 className="landing-hero-title-left">You land the j*b,</p1>
            <p1>we&apos;ll do the rest</p1>
          </h1>

          <button className="landing-hero-pill">So, WhatsTheMoove?</button>
        </div>
      </section>

      {/* Search card + upload pill */}
      <section className="landing-search-wrapper">
        <div className="landing-search-card">
          <div className="landing-search-fields">
            <div className="landing-field">
              <div className="landing-field-icon">📍</div>
              <div className="landing-field-text">
                <input
                  type="text"
                  className="landing-input"
                  placeholder="Origin"
                  value={formData.origin}
                  onChange={(e) =>
                    handleFieldChange("origin", e.target.value)
                  }
                  list="cities-list"
                />
              </div>
            </div>

            <div className="landing-field-divider" />

            <div className="landing-field">
              <div className="landing-field-icon">🏁</div>
              <div className="landing-field-text">
                <input
                  type="text"
                  className="landing-input"
                  placeholder="Destination"
                  value={formData.destination}
                  onChange={(e) =>
                    handleFieldChange("destination", e.target.value)
                  }
                  list="cities-list"
                />
              </div>
            </div>
          </div>

          <button className="landing-search-button" onClick={handleBeginSearch}>
            Begin search →
          </button>
        </div>

        {/* shared datalist for both inputs */}
        {cities.length > 0 && (
          <datalist id="cities-list">
            {cities.map((city) => (
              <option key={city} value={city} />
            ))}
          </datalist>
        )}

        {error && <p className="landing-error">{error}</p>}

        <button
          className="landing-upload-pill"
          onClick={() => onUpload && onUpload()}
        >
          Already have a job application?{" "}
          <span className="landing-upload-strong">
            Upload it to refine your results
          </span>{" "}
          →
        </button>
      </section>

      {/* Footer */}
      <footer className="landing-footer">
        <span>Built for MadHacks 2025</span>
        <span>WhatsTheMoove? © 2025</span>
      </footer>
    </div>
  );
}

export default LandingPage;
