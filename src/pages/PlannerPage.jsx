// src/pages/PlannerPage.jsx
import "./PlannerPage.css";

function PlannerPage({ formData, onChange, onNext }) {
  const origin = formData.origin || "Origin city";
  const destination = formData.destination || "Destination city";

  const handleFieldChange = (field, value) => {
    onChange(field, value);
  };

  const showTransportQuestion = !formData.needsUhaul; // hide transport if U-Haul is yes

  return (
    <main className="planner-page">
      {/* Hero banner */}
      <section className="planner-hero">
        <div className="planner-hero-overlay">
          <button className="planner-hero-pill-small">Got it!</button>
          <h1 className="planner-hero-title">
            Let’s finish planning your move from{" "}
            <span className="planner-hero-emphasis">{origin}</span> to{" "}
            <span className="planner-hero-emphasis">{destination}</span>!
          </h1>
        </div>
      </section>

      {/* What we know so far */}
      <section className="planner-section">
        <h2 className="planner-section-heading">What we know so far</h2>

        <div className="planner-card planner-location-card">
          <div className="planner-card-header">Location</div>

          <div className="planner-location-pill">
            <div className="planner-location-item">
              <div className="planner-location-icon">📍</div>
              <div className="planner-location-text">
                <span className="planner-location-value">{origin}</span>
                <span className="planner-location-caption">Origin</span>
              </div>
            </div>

            <div className="planner-location-arrow">→</div>

            <div className="planner-location-item">
              <div className="planner-location-icon">🏁</div>
              <div className="planner-location-text">
                <span className="planner-location-value">{destination}</span>
                <span className="planner-location-caption">Destination</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* What we still need to know */}
      <section className="planner-section">
        <h2 className="planner-section-heading">What we still need to know</h2>

        {/* Job duration card (months) */}
        <div className="planner-card">
          <div className="planner-card-header">Job Duration</div>
          <p className="planner-card-subtitle">
            Please choose the months during which you expect to be living near
            your job location.
          </p>

          <div className="planner-dates-row">
            <div className="planner-date-pill">
              <input
                type="month"
                className="planner-date-input"
                value={formData.jobStartDate || ""}
                onChange={(e) =>
                  handleFieldChange("jobStartDate", e.target.value)
                }
              />
              <span className="planner-date-caption">Start month</span>
            </div>

            <span className="planner-location-arrow">→</span>

            <div className="planner-date-pill">
              <input
                type="month"
                className="planner-date-input"
                value={formData.jobEndDate || ""}
                onChange={(e) =>
                  handleFieldChange("jobEndDate", e.target.value)
                }
              />
              <span className="planner-date-caption">End month</span>
            </div>
          </div>
        </div>

        {/* U-Haul question */}
        <div className="planner-card">
          <div className="planner-card-header">
            Would you like to see results for a U-Haul or moving truck?
          </div>
          <p className="planner-card-subtitle">
            This helps us estimate truck rental and driving costs.
          </p>

          <div className="planner-options-grid">
            <label className="planner-option-row">
              <input
                type="radio"
                name="needsUhaul"
                value="yes"
                checked={formData.needsUhaul === true}
                onChange={() => handleFieldChange("needsUhaul", true)}
              />
              <span>Yes, show U-Haul / moving truck options.</span>
            </label>

            <label className="planner-option-row">
              <input
                type="radio"
                name="needsUhaul"
                value="no"
                checked={formData.needsUhaul === false}
                onChange={() => handleFieldChange("needsUhaul", false)}
              />
              <span>No, I won’t be using a moving truck.</span>
            </label>
          </div>

          {formData.needsUhaul === true && (
            <p className="planner-disabled-note">
              Since you’re using a moving truck, we’ll assume you’re driving
              that vehicle for your move.
            </p>
          )}
        </div>

        {/* Moving service question (now above transportation) */}
        <div className="planner-card">
          <div className="planner-card-header">
            Would you like us to find a moving service?
          </div>
          <p className="planner-card-subtitle">
            We can look for professional movers or shipping options that match
            your move.
          </p>

          <div className="planner-options-grid">
            <label className="planner-option-row">
              <input
                type="radio"
                name="movingService"
                value="yes"
                checked={formData.wantsMovingServiceHelp === true}
                onChange={() =>
                  handleFieldChange("wantsMovingServiceHelp", true)
                }
              />
              <span>Yes, help me find a moving service.</span>
            </label>

            <label className="planner-option-row">
              <input
                type="radio"
                name="movingService"
                value="no"
                checked={formData.wantsMovingServiceHelp === false}
                onChange={() =>
                  handleFieldChange("wantsMovingServiceHelp", false)
                }
              />
              <span>No, I’ll handle moving services myself.</span>
            </label>
          </div>
        </div>

        {/* Transportation card – only shown if NOT using U-Haul */}
        {showTransportQuestion && (
          <div className="planner-card">
            <div className="planner-card-header">
              Will you need transportation arrangements?
            </div>
            <p className="planner-card-subtitle">
              Select the box that best reflects your transportation needs.
            </p>

            <div className="planner-options-grid">
              <label className="planner-option-row">
                <input
                  type="radio"
                  name="transportPlan"
                  value="have-arrangements"
                  checked={formData.transportPlan === "have-arrangements"}
                  onChange={(e) =>
                    handleFieldChange("transportPlan", e.target.value)
                  }
                />
                <span>No, I already have travel arrangements.</span>
              </label>

              <label className="planner-option-row">
                <input
                  type="radio"
                  name="transportPlan"
                  value="drive-own-car"
                  checked={formData.transportPlan === "drive-own-car"}
                  onChange={(e) =>
                    handleFieldChange("transportPlan", e.target.value)
                  }
                />
                <span>No, I anticipate driving my own car.</span>
              </label>

              <label className="planner-option-row">
                <input
                  type="radio"
                  name="transportPlan"
                  value="moving-truck"
                  checked={formData.transportPlan === "moving-truck"}
                  onChange={(e) =>
                    handleFieldChange("transportPlan", e.target.value)
                  }
                />
                <span>
                  No, I anticipate driving via a moving service (U-Haul, etc.).
                </span>
              </label>

              <label className="planner-option-row">
                <input
                  type="radio"
                  name="transportPlan"
                  value="rental-car"
                  checked={formData.transportPlan === "rental-car"}
                  onChange={(e) =>
                    handleFieldChange("transportPlan", e.target.value)
                  }
                />
                <span>
                  Yes, I anticipate driving and will need a rental car.
                </span>
              </label>

              <label className="planner-option-row">
                <input
                  type="radio"
                  name="transportPlan"
                  value="train-bus"
                  checked={formData.transportPlan === "train-bus"}
                  onChange={(e) =>
                    handleFieldChange("transportPlan", e.target.value)
                  }
                />
                <span>
                  Yes, I anticipate traveling via intercity bus or train.
                </span>
              </label>

              <label className="planner-option-row">
                <input
                  type="radio"
                  name="transportPlan"
                  value="plane"
                  checked={formData.transportPlan === "plane"}
                  onChange={(e) =>
                    handleFieldChange("transportPlan", e.target.value)
                  }
                />
                <span>Yes, I anticipate traveling via passenger plane.</span>
              </label>
            </div>
          </div>
        )}

        {/* Housing card (no preferences section) */}
        <div className="planner-card">
          <div className="planner-card-header">
            Will you need housing arrangements?
          </div>
          <p className="planner-card-subtitle">
            Select the box that best reflects your housing needs.
          </p>

          <div className="planner-options-grid">
            <label className="planner-option-row">
              <input
                type="radio"
                name="needsHousing"
                value="no"
                checked={formData.needsHousing === false}
                onChange={() => handleFieldChange("needsHousing", false)}
              />
              <span>No, I already have housing arrangements.</span>
            </label>

            <label className="planner-option-row">
              <input
                type="radio"
                name="needsHousing"
                value="yes"
                checked={formData.needsHousing === true}
                onChange={() => handleFieldChange("needsHousing", true)}
              />
              <span>Yes, I will need housing arrangements.</span>
            </label>
          </div>

          <div className="planner-budget-block">
            <p className="planner-budget-label">
              If you need housing arrangements, what is your anticipated housing
              budget?
            </p>

            <div className="planner-budget-slider-row">
              <span className="planner-budget-edge">$600/month</span>

              <input
                type="range"
                min="600"
                max="2800"
                step="50"
                value={formData.housingBudget || 1400}
                onChange={(e) =>
                  handleFieldChange("housingBudget", Number(e.target.value))
                }
              />

              <span className="planner-budget-edge">$2800/month</span>
            </div>

            <div className="planner-budget-value-pill">
              ${(formData.housingBudget || 1400).toLocaleString()}/month
            </div>
          </div>
        </div>

        <div className="planner-actions">
          <button className="planner-primary-btn" onClick={onNext}>
            See my estimate
          </button>
        </div>
      </section>
    </main>
  );
}

export default PlannerPage;
