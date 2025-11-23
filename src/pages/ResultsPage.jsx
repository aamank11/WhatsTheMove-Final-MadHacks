// src/pages/ResultsPage.jsx
import { useEffect, useState } from "react";
import { MapContainer, TileLayer, Polyline } from "react-leaflet";
import ResultCard from "../components/ResultCard.jsx";
import "./ResultsPage.css";

// 👉 Change this to your real backend URL later
const BASE_URL = "http://localhost:8000";

// Turn "Madison, WI" into "madison-wi"
function slugifyCity(city) {
  if (!city) return "unknown";
  return city
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
}

// Turn "2025-06" into "june"
function monthSegment(monthStr) {
  if (!monthStr) return "unknown";
  const [year, month] = monthStr.split("-");
  const monthNames = [
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
  ];
  const idx = parseInt(month, 10) - 1;
  return monthNames[idx] || "unknown";
}

// Build the "##" flags:
//  1st bit: needsUhaul
//  2nd bit: wantsMovingServiceHelp
function buildFlagBits(formData) {
  const uhaulBit = formData.needsUhaul ? "1" : "0";
  const movingServiceBit = formData.wantsMovingServiceHelp ? "1" : "0";
  return `${uhaulBit}${movingServiceBit}`;
}

// Build the "######" transport bits
// Order: have-arrangements, drive-own-car, moving-truck, rental-car, train-bus, plane
function buildTransportBits(formData) {
  // If they chose U-Haul, assume they're driving that truck
  if (formData.needsUhaul) {
    // 3rd bit (moving-truck) = 1 -> "001000"
    return "001000";
  }

  const order = [
    "have-arrangements",
    "drive-own-car",
    "moving-truck",
    "rental-car",
    "train-bus",
    "plane",
  ];

  const bits = order.map((option) =>
    formData.transportPlan === option ? "1" : "0"
  );

  // If nothing selected, all zeros
  return bits.join("");
}

// Build the full URL string
function buildQuoteUrl(formData) {
  const originSlug = slugifyCity(formData.origin);
  const destSlug = slugifyCity(formData.destination);

  const startMonthSeg = monthSegment(formData.jobStartDate);
  const endMonthSeg = monthSegment(formData.jobEndDate);

  const flags = buildFlagBits(formData); // "##"
  const transportBits = buildTransportBits(formData); // "######"

  const price = formData.housingBudget || 1400;

  return `${BASE_URL}/${originSlug}/${destSlug}/${startMonthSeg}/${endMonthSeg}/${flags}/${transportBits}/${price}`;
}

/**
 * Map with either:
 * - driving route (OSRM) when isPlane === false
 * - curved polyline between origin & destination when isPlane === true
 * Also reports driving distance in miles via onMilesChange (for driving only).
 */
function RouteMap({ origin, destination, isPlane, onMilesChange }) {
  const [mapData, setMapData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    async function fetchRoute() {
      if (!origin || !destination) {
        if (onMilesChange) onMilesChange(null);
        return;
      }

      try {
        // reset miles on each new fetch
        if (onMilesChange) onMilesChange(null);

        // 1) Geocode both locations via Nominatim
        const [fromRes, toRes] = await Promise.all([
          fetch(
            `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(
              origin
            )}`
          ),
          fetch(
            `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(
              destination
            )}`
          ),
        ]);

        const [fromJson, toJson] = await Promise.all([
          fromRes.json(),
          toRes.json(),
        ]);

        if (!fromJson[0] || !toJson[0]) {
          setError("We couldn’t find one of these locations on the map.");
          if (onMilesChange) onMilesChange(null);
          return;
        }

        const from = [
          parseFloat(fromJson[0].lat),
          parseFloat(fromJson[0].lon),
        ];
        const to = [parseFloat(toJson[0].lat), parseFloat(toJson[0].lon)];

        const center = [(from[0] + to[0]) / 2, (from[1] + to[1]) / 2];

        let routeCoords = null;
        let bounds = null;

        if (isPlane) {
          // 2A) Plane: curved arc between from & to — no miles for flights
          const numPoints = 40;
          const [lat1, lng1] = from;
          const [lat2, lng2] = to;

          const midLat = (lat1 + lat2) / 2;
          const midLng = (lng1 + lng2) / 2;

          const dx = lng2 - lng1;
          const dy = lat2 - lat1;
          const distance = Math.sqrt(dx * dx + dy * dy) || 1;

          const normX = -dy / distance;
          const normY = dx / distance;

          const curvature = 0.35;
          const controlLat = midLat + normY * distance * curvature;
          const controlLng = midLng + normX * distance * curvature;

          const points = [];
          for (let i = 0; i <= numPoints; i++) {
            const t = i / numPoints;
            const oneMinusT = 1 - t;
            const lat =
              oneMinusT * oneMinusT * lat1 +
              2 * oneMinusT * t * controlLat +
              t * t * lat2;
            const lng =
              oneMinusT * oneMinusT * lng1 +
              2 * oneMinusT * t * controlLng +
              t * t * lng2;
            points.push([lat, lng]);
          }

          routeCoords = points;

          let minLat = Infinity,
            maxLat = -Infinity,
            minLng = Infinity,
            maxLng = -Infinity;
          points.forEach(([lat, lng]) => {
            if (lat < minLat) minLat = lat;
            if (lat > maxLat) maxLat = lat;
            if (lng < minLng) minLng = lng;
            if (lng > maxLng) maxLng = lng;
          });
          bounds = [
            [minLat, minLng],
            [maxLat, maxLng],
          ];

          if (onMilesChange) onMilesChange(null); // no miles for flights
        } else {
          // 2B) Driving: OSRM route, and compute miles
          try {
            const osrmUrl = `https://router.project-osrm.org/route/v1/driving/${from[1]},${from[0]};${to[1]},${to[0]}?overview=full&geometries=geojson`;
            const routeRes = await fetch(osrmUrl);
            const routeJson = await routeRes.json();

            if (
              routeJson.routes &&
              routeJson.routes[0] &&
              routeJson.routes[0].geometry
            ) {
              const route = routeJson.routes[0];
              const coords = route.geometry.coordinates.map(
                ([lon, lat]) => [lat, lon]
              );
              routeCoords = coords;

              // distance in meters → miles
              if (typeof route.distance === "number") {
                const miles =
                  Math.round((route.distance / 1609.34) * 10) / 10; // 1 decimal
                if (onMilesChange) onMilesChange(miles);
              } else if (onMilesChange) {
                onMilesChange(null);
              }

              let minLat = Infinity,
                maxLat = -Infinity,
                minLng = Infinity,
                maxLng = -Infinity;
              coords.forEach(([lat, lng]) => {
                if (lat < minLat) minLat = lat;
                if (lat > maxLat) maxLat = lat;
                if (lng < minLng) minLng = lng;
                if (lng > maxLng) maxLng = lng;
              });
              bounds = [
                [minLat, minLng],
                [maxLat, maxLng],
              ];
            } else if (onMilesChange) {
              onMilesChange(null);
            }
          } catch (e) {
            console.error("OSRM route error:", e);
            if (onMilesChange) onMilesChange(null);
          }
        }

        setMapData({ from, to, center, routeCoords, bounds });
        setError("");
      } catch (err) {
        console.error(err);
        setError("There was a problem loading the map.");
        if (onMilesChange) onMilesChange(null);
      }
    }

    fetchRoute();
  }, [origin, destination, isPlane, onMilesChange]);

  if (!origin || !destination) {
    return (
      <p className="results-map-note">
        Add a valid origin and destination to see the map.
      </p>
    );
  }

  if (error) {
    return <p className="results-map-note">{error}</p>;
  }

  if (!mapData) {
    return <p className="results-map-note">Loading map…</p>;
  }

  const { from, to, center, routeCoords, bounds } = mapData;
  const polylinePositions = routeCoords || [from, to];

  return (
    <div className="results-map-inner">
      <MapContainer
        center={center}
        zoom={5}
        bounds={bounds || undefined}
        scrollWheelZoom={false}
        className="results-map-container"
      >
        <TileLayer
          attribution="&copy; OpenStreetMap contributors"
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <Polyline
          positions={polylinePositions}
          pathOptions={{ color: "red", weight: 4 }}
        />
      </MapContainer>
    </div>
  );
}

function ResultsPage({ formData, onBack, onRestart }) {
  const [apiResult, setApiResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [apiError, setApiError] = useState("");
  const [miles, setMiles] = useState(null); // 👈 new

  // Decide if this is "plane" travel for the map curve
  const isPlaneTravel =
    formData.transportMode === "fly" ||
    formData.transportPlan === "plane" ||
    formData.transportPlan === "private-plane";

  // Call backend when this page loads / key answers change
  useEffect(() => {
    async function fetchQuote() {
      if (
        !formData.origin ||
        !formData.destination ||
        !formData.jobStartDate ||
        !formData.jobEndDate
      ) {
        return;
      }

      try {
        setLoading(true);
        setApiError("");

        const url = buildQuoteUrl(formData);
        console.log("Fetching quote from:", url);

        const res = await fetch(url);
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }

        const data = await res.json();
        setApiResult(data);
      } catch (err) {
        console.error("Quote fetch failed:", err);
        setApiError(
          "We couldn’t reach the quote service yet, so these numbers are using demo logic."
        );
      } finally {
        setLoading(false);
      }
    }

    fetchQuote();
  }, [
    formData.origin,
    formData.destination,
    formData.jobStartDate,
    formData.jobEndDate,
    formData.needsUhaul,
    formData.wantsMovingServiceHelp,
    formData.transportPlan,
    formData.housingBudget,
  ]);

  // Fallback demo estimate
  const fallbackEstimate = {
    housing: 3200,
    travel: 450,
    moving_truck: formData.needsUhaul ? 600 : 0,
    other: 200,
  };

  // If backend provided a breakdown, use it; otherwise fallback
  const housing =
    apiResult?.breakdown?.housing ?? fallbackEstimate.housing;
  const travel =
    apiResult?.breakdown?.travel ?? fallbackEstimate.travel;
  const moving_truck =
    apiResult?.breakdown?.moving_truck ?? fallbackEstimate.moving_truck;
  const other =
    apiResult?.breakdown?.other ?? fallbackEstimate.other;

  const total =
    apiResult?.total_cost ?? housing + travel + moving_truck + other;

  return (
    <main className="screen results-screen">
      <h2>Your move estimate</h2>
      <p className="screen-subtitle">
        Based on your answers, here’s a rough breakdown of your expected costs.
      </p>

      <p className="results-context">
        From <strong>{formData.origin || "?"}</strong> to{" "}
        <strong>{formData.destination || "?"}</strong> between{" "}
        <strong>{formData.jobStartDate || "start month"}</strong> and{" "}
        <strong>{formData.jobEndDate || "end month"}</strong>, traveling by{" "}
        <strong>{formData.transportMode}</strong>
        {formData.needsUhaul ? " with a moving truck." : "."}
      </p>

      {/* Map card */}
      <section className="results-map-card">
        <div className="results-map-header">
          <h3>Route preview</h3>
          <p>
            A quick look at your{" "}
            {isPlaneTravel ? "flight path" : "drive"} from{" "}
            {formData.origin || "origin"} to{" "}
            {formData.destination || "destination"}.
          </p>
        </div>
        <RouteMap
          origin={formData.origin}
          destination={formData.destination}
          isPlane={isPlaneTravel}
          onMilesChange={setMiles} // 👈 capture driving miles
        />
      </section>

      {/* Show miles only for driving routes */}
      {!isPlaneTravel && miles != null && (
        <p className="results-map-note">
          Approximate driving distance:{" "}
          <strong>{miles.toLocaleString()} miles</strong>
        </p>
      )}

      {loading && (
        <p className="results-map-note">Fetching a personalized quote…</p>
      )}
      {apiError && <p className="results-map-note">{apiError}</p>}

      <div className="results-grid">
        <ResultCard label="Housing" amount={housing} />
        <ResultCard label="Travel" amount={travel} />
        <ResultCard label="Moving truck" amount={moving_truck} />
        <ResultCard label="Other" amount={other} />
      </div>

      <div className="results-total">
        <span>Total estimated cost</span>
        <strong>${total.toLocaleString()}</strong>
      </div>

      <div className="results-actions">
        <button className="secondary-btn" onClick={onBack}>
          Edit answers
        </button>
        <button className="ghost-btn" onClick={onRestart}>
          Start over
        </button>
      </div>
    </main>
  );
}

export default ResultsPage;
