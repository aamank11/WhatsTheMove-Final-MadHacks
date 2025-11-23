// src/pages/Upload.jsx
import { useState } from "react";
import "./Upload.css";

const JOB_SEARCH_ENDPOINT =
  "https://whatsthemove-final-madhacks.fly.dev/job-search";

function Upload({ formData, onChange, onContinue }) {
  const [jobUrl, setJobUrl] = useState(formData.jobUrl || "");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setResult(null);

    const trimmed = jobUrl.trim();
    if (!trimmed) {
      setError("Please paste a valid job posting URL.");
      return;
    }

    try {
      setLoading(true);
      const urlParam = encodeURIComponent(trimmed);
      const res = await fetch(`${JOB_SEARCH_ENDPOINT}?job_url=${urlParam}`);

      if (!res.ok) {
        throw new Error(`Request failed with status ${res.status}`);
      }

      const data = await res.json();
      setResult(data);

      if (!data.is_valid_job_posting) {
        setError(
          data.validity_reason ||
            "This does not appear to be a valid job posting URL."
        );
        return;
      }

      // 🔹 0) Origin is always Madison, WI
      onChange("origin", "Madison, WI");

      // 1) Destination city from job location
      if (data.location) {
        onChange("destination", data.location);
      }

      // 2) Job duration from start/end month & year
      const padMonth = (m) => String(m).padStart(2, "0");

      if (data.job_start_year && data.job_start_month) {
        const startMonth = `${data.job_start_year}-${padMonth(
          data.job_start_month
        )}`;
        onChange("jobStartDate", startMonth);
      }

      if (data.job_end_year && data.job_end_month) {
        const endMonth = `${data.job_end_year}-${padMonth(data.job_end_month)}`;
        onChange("jobEndDate", endMonth);
      }

      // Optional: store some extra context for later pages
      onChange("jobUrl", trimmed);
      if (data.job_title) onChange("jobTitle", data.job_title);
      if (data.company_name) onChange("companyName", data.company_name);
    } catch (err) {
      console.error(err);
      setError("Something went wrong while checking your job URL.");
    } finally {
      setLoading(false);
    }
  };

  const handleContinue = () => {
    // Go to PlannerPage (parent controls navigation)
    onContinue();
  };

  return (
    <main className="upload-page">
      <section className="upload-hero">
        <div className="upload-hero-overlay">
          <h1 className="upload-title">Paste your job posting</h1>
          <p className="upload-subtitle">
            We&apos;ll automatically pull the job location and duration to kick
            off your move planning.
          </p>
        </div>
      </section>

      <section className="upload-content">
        <div className="upload-card">
          <form onSubmit={handleSubmit}>
            <label className="upload-label" htmlFor="job-url">
              Job application URL
            </label>
            <input
              id="job-url"
              type="url"
              className="upload-input"
              placeholder="https://www.example.com/job-posting"
              value={jobUrl}
              onChange={(e) => {
                setError("");
                setJobUrl(e.target.value);
              }}
            />

            <button
              type="submit"
              className="upload-submit-btn"
              disabled={loading}
            >
              {loading ? "Checking job posting..." : "Analyze job posting"}
            </button>
          </form>

          {error && <p className="upload-error">{error}</p>}

          {result && result.is_valid_job_posting && (
            <div className="upload-result">
              <h2 className="upload-result-heading">We found your job 🎉</h2>
              <p className="upload-result-main">
                <strong>{result.job_title}</strong>{" "}
                {result.company_name && `at ${result.company_name}`}
              </p>

              {result.location && (
                <p className="upload-result-line">
                  <span className="upload-result-label">Location:</span>{" "}
                  {result.location}
                </p>
              )}

              {(result.job_start_month || result.job_end_month) && (
                <p className="upload-result-line">
                  <span className="upload-result-label">Duration:</span>{" "}
                  {result.job_start_month && result.job_start_year
                    ? `${result.job_start_month}/${result.job_start_year}`
                    : "?"}{" "}
                  →{" "}
                  {result.job_end_month && result.job_end_year
                    ? `${result.job_end_month}/${result.job_end_year}`
                    : "?"}
                </p>
              )}

              {result.quick_summary && (
                <p className="upload-result-summary">
                  {result.quick_summary}
                </p>
              )}
            </div>
          )}

          <div className="upload-next-actions">
            <button
              className="upload-continue-btn"
              onClick={handleContinue}
              disabled={loading}
            >
              Continue to planner →
            </button>
            <p className="upload-note">
              On the next page, your origin will be Madison, WI and your
              destination and job months will be pre-filled. You can still edit
              anything before we estimate your move.
            </p>
          </div>
        </div>
      </section>
    </main>
  );
}

export default Upload;
