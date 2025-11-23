// src/pages/ResultsPage.jsx
import { useEffect, useState } from "react";
import { MapContainer, TileLayer, Polyline } from "react-leaflet";
import "./ResultsPage.css";
import flightDataCsv from "../assets/csv/flightdata.csv?raw";

// Backend URL
const BASE_URL = "https://whatsthemove-final-madhacks.fly.dev/whatsthemove";

// Rental / fuel / maintenance model
const RENTAL_MODEL = {
  DailyRental: {
    car: 65.0,
    minivan: 57.0,
    suv: 75.0,
    truck: 75.0,
    van: 108.0,
  },
  FuelPerMile: {
    car: 0.11829999999999999,
    minivan: 0.14176666666666668,
    suv: 0.14176666666666668,
    truck: 0.20485,
    van: 0.20485,
  },
  MaintenancePerMile: {
    car: 0.10220000000000001,
    minivan: 0.10676666666666668,
    suv: 0.10676666666666668,
    truck: 0.1038,
    van: 0.1038,
  },
  BusCPM: {
    0: 0.2794,
    1: 0.2413,
    2: 0.1905,
  },
};

/**
 * ---- Flight CSV helpers ----
 */

// Parse the flightdata.csv (distance_band, carrier, multiplier)
function parseFlightCsv(csvStr) {
  if (!csvStr) return [];
  const lines = csvStr.trim().split("\n");
  const rows = [];
  for (let i = 1; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) continue;
    const parts = line.split(",");
    if (parts.length < 3) continue;
    const [band, carrier, multStr] = parts;
    const [minStr, maxStr] = band.split("-");
    const min = parseInt(minStr, 10);
    const max = parseInt(maxStr, 10);
    const multiplier = parseFloat(multStr);
    if (
      Number.isFinite(min) &&
      Number.isFinite(max) &&
      Number.isFinite(multiplier)
    ) {
      rows.push({
        min,
        max,
        carrier: carrier.trim(),
        multiplier,
      });
    }
  }
  return rows;
}

const FLIGHT_ROWS = parseFlightCsv(flightDataCsv);

// Given a flight distance, find all matching rows for that band and
// compute a cost per airline.
function computeFlightOptions(distanceMiles) {
  if (!distanceMiles || distanceMiles <= 0) return null;
  const bandRows = FLIGHT_ROWS.filter(
    (r) => distanceMiles >= r.min && distanceMiles <= r.max
  );
  if (!bandRows.length) return null;

  return bandRows.map((row) => ({
    carrier: row.carrier,
    cost: Math.round(distanceMiles * row.multiplier),
  }));
}

/**
 * ---- URL + helpers used by backend ----
 */

function slugifyCity(city) {
  if (!city) return "unknown";
  return city.toLowerCase().replace(/[^a-z]/g, "");
}

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

// 1st bit: needsUhaul, 2nd bit: wantsMovingServiceHelp
function buildFlagBits(formData) {
  const uhaulBit = formData.needsUhaul ? "1" : "0";
  const movingServiceBit = formData.wantsMovingServiceHelp ? "1" : "0";
  return `${uhaulBit}${movingServiceBit}`;
}

// "######" bits: have-arrangements, drive-own-car, moving-truck, rental-car, train-bus, plane
function buildTransportBits(formData) {
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
  return bits.join("");
}

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

// Bucket: 0 < 500, 1: 500–1000, 2: 1000+
function getBusBucket(miles) {
  if (miles >= 1000) return 2;
  if (miles >= 500) return 1;
  return 0;
}

// Travel fallback using CPMs (no U-Haul logic here; that's handled separately)
function computeTravelFallback(formData, miles) {
  const mode = formData.transportPlan;

  if (!miles || miles <= 0) {
    // Simple placeholder if distance is unknown
    if (mode === "train-bus") return 150;
    if (mode === "plane") return 450;
    return 250;
  }

  // Personal car or rental car -> sedan CPM
  if (mode === "drive-own-car" || mode === "rental-car") {
    const type = "car";
    const cpm =
      (RENTAL_MODEL.FuelPerMile[type] || 0) +
      (RENTAL_MODEL.MaintenancePerMile[type] || 0);
    return Math.round(miles * cpm);
  }

  // Bus / train
  if (mode === "train-bus") {
    const bucket = getBusBucket(miles);
    const cpm = RENTAL_MODEL.BusCPM[bucket] || 0.25;
    return Math.round(miles * cpm);
  }

  // Moving truck or unknown – treat similar to truck CPM
  if (mode === "moving-truck") {
    const type = "truck";
    const cpm =
      (RENTAL_MODEL.FuelPerMile[type] || 0) +
      (RENTAL_MODEL.MaintenancePerMile[type] || 0);
    return Math.round(miles * cpm);
  }

  // Plane / other
  return 450;
}

// For UI only – show all vehicle types when rental-car chosen
function computeRentalVehicleBreakdown(miles) {
  if (!miles || miles <= 0) return null;

  const types = ["car", "minivan", "suv", "truck", "van"];

  return types.map((type) => {
    const fuel = RENTAL_MODEL.FuelPerMile[type] || 0;
    const maint = RENTAL_MODEL.MaintenancePerMile[type] || 0;
    const cpm = fuel + maint;
    return {
      type,
      cost: Math.round(miles * cpm),
    };
  });
}

// Months between two YYYY-MM strings
function monthsBetween(start, end) {
  if (!start || !end) return 3;
  const [ys, ms] = start.split("-").map(Number);
  const [ye, me] = end.split("-").map(Number);
  const diff = (ye - ys) * 12 + (me - ms) + 1;
  return diff > 0 ? diff : 1;
}

// Haversine formula to calculate distance between two lat/lng points in miles
function haversineDistance(lat1, lon1, lat2, lon2) {
  const R = 3959; // Earth's radius in miles
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

/**
 * Map with either:
 * - driving route (OSRM) when isPlane === false
 * - curved polyline between origin & destination when isPlane === true
 * Also reports driving distance in miles via onMilesChange (for driving only).
 * For flights, reports straight-line distance via onFlightMilesChange.
 */
function RouteMap({ origin, destination, isPlane, onMilesChange, onFlightMilesChange }) {
  const [mapData, setMapData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    async function fetchRoute() {
      if (!origin || !destination) {
        if (onMilesChange) onMilesChange(null);
        if (onFlightMilesChange) onFlightMilesChange(null);
        return;
      }

      try {
        if (onMilesChange) onMilesChange(null);
        if (onFlightMilesChange) onFlightMilesChange(null);

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
          setError("We couldn't find one of these locations on the map.");
          if (onMilesChange) onMilesChange(null);
          if (onFlightMilesChange) onFlightMilesChange(null);
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
          // Curved arc for flights
          const numPoints = 40;
          const [lat1, lng1] = from;
          const [lat2, lng2] = to;

          // Calculate straight-line distance for flight pricing
          const straightLineMiles = haversineDistance(lat1, lng1, lat2, lng2);
          if (onFlightMilesChange) {
            onFlightMilesChange(Math.round(straightLineMiles * 10) / 10);
          }

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

          if (onMilesChange) onMilesChange(null);
        } else {
          // Driving with OSRM
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

              if (typeof route.distance === "number") {
                const miles =
                  Math.round((route.distance / 1609.34) * 10) / 10;
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
        if (onFlightMilesChange) onFlightMilesChange(null);
      }
    }

    fetchRoute();
  }, [origin, destination, isPlane, onMilesChange, onFlightMilesChange]);

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
  const [miles, setMiles] = useState(null); // driving miles from map
  const [flightMiles, setFlightMiles] = useState(null); // straight-line flight miles

  // Selection state for "Add to total" buttons
  const [selectedRental, setSelectedRental] = useState(null); // { type, cost } | null
  const [selectedMoving, setSelectedMoving] = useState(null); // { id, cost } | null
  const [uhaulSelected, setUhaulSelected] = useState(false);
  const [selectedFlight, setSelectedFlight] = useState(null); // { carrier, cost } | null

  // Enhanced plane travel detection - checks multiple possible field names
  const isPlaneTravel =
    formData.transportMode === "fly" ||
    formData.transportMode === "plane" ||
    formData.transportMode === "airplane" ||
    formData.transportPlan === "plane" ||
    formData.transportPlan === "airplane" ||
    formData.transportPlan === "private-plane" ||
    formData.transportation === "plane" ||
    formData.transportation === "airplane" ||
    formData.travelMode === "plane" ||
    formData.travelMode === "airplane";

  // Debug logging to help identify the correct field
  useEffect(() => {
    console.log('=== TRANSPORT DEBUG ===');
    console.log('Full formData:', formData);
    console.log('Transport-related fields:', {
      transportMode: formData.transportMode,
      transportPlan: formData.transportPlan,
      transportation: formData.transportation,
      travelMode: formData.travelMode,
    });
    console.log('isPlaneTravel:', isPlaneTravel);
    console.log('flightMiles:', flightMiles);
    console.log('=====================');
  }, [formData, isPlaneTravel, flightMiles]);

  // Fetch backend quote
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
          "We couldn't reach the quote service yet, so these numbers are using demo logic."
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

  // --- Housing estimate (backend + fallback) ---
  const backendHousing = apiResult?.housing;
  const apartments = Array.isArray(backendHousing?.apartments)
    ? backendHousing.apartments
    : [];

  let housing = 3200;
  if (backendHousing?.enabled && apartments.length > 0) {
    const prices = apartments
      .map((a) => Number(a.price))
      .filter((p) => !Number.isNaN(p) && p > 0);
    if (prices.length) {
      const avg = prices.reduce((sum, p) => sum + p, 0) / prices.length;
      const months = monthsBetween(
        formData.jobStartDate,
        formData.jobEndDate
      );
      housing = Math.round(avg * months);
    }
  }

  // --- Transportation / moving help base numbers ---
  const backendTransport = apiResult?.transportation;
  const movingHelp = backendTransport?.moving_help;
  const movingProviders = Array.isArray(movingHelp?.providers)
    ? movingHelp.providers
    : [];

  // Flight distance for airline pricing (from backend, or fallback to calculated flight miles)
  const backendFlightDistance =
    typeof backendTransport?.distance_miles === "number"
      ? backendTransport.distance_miles
      : null;

  const flightDistance = isPlaneTravel
    ? backendFlightDistance ?? flightMiles
    : null;

  // Debug flight options calculation
  const flightOptions = isPlaneTravel && flightDistance
    ? computeFlightOptions(flightDistance)
    : null;

  useEffect(() => {
    if (isPlaneTravel) {
      console.log('Flight options debug:', {
        isPlaneTravel,
        flightDistance,
        flightOptions,
        numOptions: flightOptions?.length || 0
      });
    }
  }, [isPlaneTravel, flightDistance, flightOptions]);

  // Base moving help (other)
  let movingHelpBase = 200;
  if (movingHelp?.enabled && movingProviders.length > 0) {
    const costs = movingProviders
      .map((p) => Number(p.estimated_total))
      .filter((c) => !Number.isNaN(c) && c > 0);
    if (costs.length) {
      movingHelpBase = Math.round(Math.min(...costs));
    }
  }

  // Base travel from CPMs / bus
  const fallbackTravel = computeTravelFallback(formData, miles);
  let travelBase = fallbackTravel;

  // If bus/train and backend has a bus price, override base travel
  if (
    formData.transportPlan === "train-bus" &&
    backendTransport?.bus?.enabled &&
    typeof backendTransport.bus.example_price === "number"
  ) {
    travelBase = Math.round(backendTransport.bus.example_price);
  }

  // If we're flying and we have airline options, default to cheapest airline for base
  if (isPlaneTravel && flightOptions && flightOptions.length > 0) {
    const cheapest = flightOptions.reduce(
      (min, o) => (o.cost < min.cost ? o : min),
      flightOptions[0]
    );
    travelBase = cheapest.cost;
  }

  // Base U-Haul moving truck cost (if applicable)
  let movingTruckBase = 0;
  const defaultUhaulFallback = 600;

  if (formData.needsUhaul) {
    if (miles && miles > 0) {
      const type = "truck";
      const fuel = RENTAL_MODEL.FuelPerMile[type] || 0;
      const maint = RENTAL_MODEL.MaintenancePerMile[type] || 0;
      const cpm = fuel + maint;
      movingTruckBase = Math.round(miles * cpm);
    } else {
      movingTruckBase = defaultUhaulFallback;
    }
    // When using U-Haul, we treat all distance-based cost as moving truck, not "Travel"
    travelBase = 0;
  }

  // Rental car breakdown for UI
  const rentalBreakdown =
    formData.transportPlan === "rental-car" && miles
      ? computeRentalVehicleBreakdown(miles)
      : null;

  // Apply user selections to get final category amounts
  let travel = travelBase;
  let moving_truck = movingTruckBase;
  let moving_help = movingHelpBase;

  // If they chose a specific rental vehicle, use that for travel
  if (selectedRental && formData.transportPlan === "rental-car") {
    travel = selectedRental.cost;
  }

  // If they chose a specific airline, use that for travel
  if (selectedFlight && isPlaneTravel) {
    travel = selectedFlight.cost;
  }

  // If they chose a specific moving provider, use that for moving help
  if (selectedMoving && movingProviders.length > 0) {
    moving_help = selectedMoving.cost;
  }

  // If U-Haul toggle is used, only include moving truck when ON
  if (formData.needsUhaul) {
    moving_truck = uhaulSelected ? movingTruckBase : 0;
  }

  const prettyTransport =
    formData.transportPlan === "rental-car"
      ? "rental car"
      : formData.transportPlan === "drive-own-car"
      ? "your own car"
      : formData.transportPlan === "train-bus"
      ? "bus/train"
      : formData.transportPlan === "plane"
      ? "plane"
      : formData.transportMode || "your selected mode";

  const total = housing + travel + moving_truck + moving_help;

  // Only show clickable housing for Neenah / Seattle with URLs
  const destLower = (formData.destination || "").toLowerCase();
  const isAptSupportedCity =
    destLower.includes("neenah") || destLower.includes("seattle");

  const linkedApartments =
    isAptSupportedCity && apartments.length > 0
      ? apartments.filter(
          (apt) =>
            apt.listingWebsite &&
            apt.listingWebsite !== "NA" &&
            typeof apt.listingWebsite === "string"
        )
      : [];

  const uhaulChipCost =
    formData.needsUhaul && movingTruckBase ? movingTruckBase : null;

  return (
    <div className="results-page">
      {/* Top bar */}
      <header className="results-topbar">
        <div className="results-topbar-inner">
          <div className="results-logo-pill">WhatsTheMoove.com</div>
          <p className="results-topbar-text">
            Learn how{" "}
            <span className="results-topbar-brand">WhatsTheMoove?</span> makes
            moving the easiest part of your job search →
          </p>
        </div>
      </header>

      <main className="screen results-main">
        {/* Heading */}
        <header className="results-header">
          <h1>The results are in!</h1>
          <p>
            Based on your answers, here is a rough breakdown of your expected
            costs.
          </p>
        </header>

        {/* Overview pill */}
        <section className="results-card results-overview-card">
          <h3>Overview</h3>
          <p>
            From <strong>{formData.origin || "?"}</strong> to{" "}
            <strong>{formData.destination || "?"}</strong> between{" "}
            <strong>{formData.jobStartDate || "start month"}</strong> and{" "}
            <strong>{formData.jobEndDate || "end month"}</strong>, traveling by{" "}
            <strong>{prettyTransport}</strong>
            {formData.needsUhaul ? " with a moving truck." : "."}
          </p>
        </section>

        {/* Route preview */}
        <section className="results-card results-map-card">
          <div className="results-card-header">
            <h3>Route Preview</h3>
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
            onMilesChange={setMiles}
            onFlightMilesChange={setFlightMiles}
          />
          {!isPlaneTravel && miles != null && (
            <p className="results-map-footnote">
              Approximate driving distance:{" "}
              <strong>{miles.toLocaleString()} miles</strong>
            </p>
          )}
          {isPlaneTravel && flightMiles != null && (
            <p className="results-map-footnote">
              Approximate flight distance:{" "}
              <strong>{flightMiles.toLocaleString()} miles</strong>
            </p>
          )}
        </section>

        {loading && (
          <p className="results-map-note">Fetching a personalized quote…</p>
        )}
        {apiError && <p className="results-map-note">{apiError}</p>}

        {/* Housing options */}
        {linkedApartments.length > 0 && (
          <section className="results-card results-housing-section">
            <div className="results-card-header">
              <h3>Housing Options</h3>
              <p>
                Please consider time before and after your job in which you plan
                to stay in the location of your work.
              </p>
            </div>
            <div className="results-housing-row">
              {linkedApartments.map((apt) => (
                <a
                  key={apt.id}
                  href={apt.listingWebsite}
                  target="_blank"
                  rel="noreferrer"
                  className="results-housing-chip"
                >
                  <div className="results-housing-header">
                    <span className="results-housing-price">
                      ${Number(apt.price).toLocaleString()}
                    </span>
                    <span className="results-housing-type">
                      {apt.propertyType || "Listing"}
                    </span>
                  </div>
                  <div className="results-housing-address">
                    {apt.formattedAddress || `${apt.city}, ${apt.state}`}
                  </div>
                  <div className="results-housing-meta">
                    {apt.bedrooms && <span>{apt.bedrooms} bd</span>}
                    {apt.bathrooms && <span>{apt.bathrooms} ba</span>}
                    {apt.squareFootage &&
                      apt.squareFootage !== "NA" && (
                        <span>{apt.squareFootage} sq ft</span>
                      )}
                  </div>
                  <div className="results-housing-link-cta">
                    Open listing ↗
                  </div>
                </a>
              ))}
              <button
                type="button"
                className="results-housing-more"
                aria-label="See more listings"
              >
                →
              </button>
            </div>
          </section>
        )}

        {/* Moving options */}
        {movingProviders.length > 0 && (
          <section className="results-card results-moving-section">
            <div className="results-card-header">
              <h3>Moving Options</h3>
              <p>
                We found these moving options for{" "}
                {movingHelp?.loading_address || formData.origin},{" "}
                to {movingHelp?.unloading_address || formData.destination}.
              </p>
            </div>
            <div className="results-moving-row">
              {movingProviders.map((p, idx) => {
                const id = p.id || `provider-${idx}`;
                const isSelected =
                  selectedMoving && selectedMoving.id === id;
                return (
                  <div key={id} className="results-moving-chip">
                    <div className="results-moving-price">
                      ${Number(p.estimated_total).toLocaleString()}
                    </div>
                    <div className="results-moving-name">{p.name}</div>
                    <div className="results-moving-meta">
                      {p.crew_size} movers · {p.hours} hrs
                    </div>
                    <button
                      type="button"
                      className="results-mini-btn"
                      onClick={() =>
                        setSelectedMoving((prev) =>
                          prev && prev.id === id
                            ? null
                            : { id, cost: Number(p.estimated_total) }
                        )
                      }
                    >
                      {isSelected ? "Remove from total" : "Add to total +"}
                    </button>
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {/* Transport / rental / U-Haul / flights */}
        {(rentalBreakdown || uhaulChipCost !== null || flightOptions) && (
          <section className="results-card results-transport-section">
            <div className="results-card-header">
              <h3>Transportation Options</h3>
              <p>
                {isPlaneTravel
                  ? `Choose an airline estimate for your flight (${flightDistance?.toLocaleString() || '?'} miles).`
                  : formData.needsUhaul
                  ? "We estimated your U-Haul truck cost based on your driving distance."
                  : "We found these estimated rental costs by vehicle type."}
              </p>
            </div>

            <div className="results-rental-row">
              {/* Rental car vehicle breakdown */}
              {rentalBreakdown &&
                rentalBreakdown.map((opt) => {
                  const isSelected =
                    selectedRental && selectedRental.type === opt.type;
                  return (
                    <div key={opt.type} className="results-rental-chip">
                      <div className="results-rental-price">
                        ${opt.cost.toLocaleString()}
                      </div>
                      <div className="results-rental-label">
                        {opt.type === "suv"
                          ? "SUV"
                          : opt.type.charAt(0).toUpperCase() +
                            opt.type.slice(1)}
                      </div>
                      <button
                        type="button"
                        className="results-mini-btn"
                        onClick={() =>
                          setSelectedRental((prev) =>
                            prev && prev.type === opt.type
                              ? null
                              : { type: opt.type, cost: opt.cost }
                          )
                        }
                      >
                        {isSelected ? "Remove from total" : "Add to total +"}
                      </button>
                    </div>
                  );
                })}

              {/* Flight options */}
              {flightOptions &&
                flightOptions.map((opt) => {
                  const isSelected =
                    selectedFlight &&
                    selectedFlight.carrier === opt.carrier;
                  return (
                    <div key={opt.carrier} className="results-rental-chip">
                      <div className="results-rental-price">
                        ${opt.cost.toLocaleString()}
                      </div>
                      <div className="results-rental-label">
                        {opt.carrier}
                      </div>
                      <button
                        type="button"
                        className="results-mini-btn"
                        onClick={() =>
                          setSelectedFlight((prev) =>
                            prev && prev.carrier === opt.carrier
                              ? null
                              : { carrier: opt.carrier, cost: opt.cost }
                          )
                        }
                      >
                        {isSelected ? "Remove from total" : "Add to total +"}
                      </button>
                    </div>
                  );
                })}

              {/* U-Haul truck chip */}
              {uhaulChipCost !== null && (
                <div className="results-rental-chip">
                  <div className="results-rental-price">
                    ${uhaulChipCost.toLocaleString()}
                  </div>
                  <div className="results-rental-label">U-Haul truck</div>
                  <button
                    type="button"
                    className="results-mini-btn"
                    onClick={() => setUhaulSelected((prev) => !prev)}
                  >
                    {uhaulSelected ? "Remove from total" : "Add to total +"}
                  </button>
                </div>
              )}
            </div>
          </section>
        )}

        {/* Grand total */}
        <section className="results-grand">
          <h3 className="results-grand-title">Grand Total</h3>
          <div className="results-grand-grid">
            <div className="results-grand-pill">
              <span className="results-grand-label">Housing</span>
              <span className="results-grand-amount">
                ${housing.toLocaleString()}
              </span>
            </div>
            <div className="results-grand-pill">
              <span className="results-grand-label">Travel</span>
              <span className="results-grand-amount">
                ${travel.toLocaleString()}
              </span>
            </div>
            <div className="results-grand-pill">
              <span className="results-grand-label">Moving Truck</span>
              <span className="results-grand-amount">
                ${moving_truck.toLocaleString()}
              </span>
            </div>
            <div className="results-grand-pill">
              <span className="results-grand-label">Moving Help</span>
              <span className="results-grand-amount">
                ${moving_help.toLocaleString()}
              </span>
            </div>
          </div>

          <div className="results-grand-summary">
            <span>Total Cost:</span>
            <span className="results-grand-summary-amount">
              ${total.toLocaleString()}
            </span>
          </div>

          <div className="results-actions">
            <button className="secondary-btn" onClick={onBack}>
              Edit answers
            </button>
            <button className="ghost-btn" onClick={onRestart}>
              Start over
            </button>
            <button
              className="primary-btn results-save-btn"
              type="button"
              onClick={() => alert("Results saved for the demo!")}
            >
              Save results
            </button>
          </div>
        </section>
      </main>
    </div>
  );
}

export default ResultsPage;