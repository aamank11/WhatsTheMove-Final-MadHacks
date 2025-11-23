# WhatsTheMove – Architecture Overview

WhatsTheMove is a web app that helps students and early-career professionals plan a move for internships, co-ops, or new jobs. It combines:

- **Move planning** (transportation + housing)  
- **Job posting analysis** (via an LLM)  

into a single, structured “move plan” JSON that the frontend turns into a clean, visual dashboard.

---

## Purpose & What the Product Does

### Core Idea

You paste in (or fill out):

- **Where you’re moving from**  
- **Where you’re moving to**  
- **When** you’re moving (start month → end month)  
- **How you want to travel** (U-Haul, own car, flight, etc.)  
- **Your budget** for housing  
- **Optionally: a job posting URL** (Amazon, Disney, etc.)

The app then:

1. **Analyzes the job listing** (title, company, location, internship dates, red flags, pay if mentioned).
2. **Estimates transportation options** based on your preferences:
   - Static / demo costs for U-Haul and moving help
   - Simple estimates for bus, rental car, own car
   - Flight distance between origin and destination city
3. **Looks up apartments** under your budget in the destination city.
4. Returns one unified JSON object that the frontend renders as:
   - A **job summary** section
   - **Transportation cards** (U-Haul, flight distance, etc.)
   - A **housing section** with apartments under your budget

The result: a quick, high-level snapshot of **“What’s the move?”** for a given job + relocation scenario.

---

## Overall Architecture

The project is split into:

- **Frontend**: Single-page app (SPA) that:
  - Collects user input
  - Encodes it into backend URLs / query params
  - Renders results into UI components

- **Backend**: FastAPI service that:
  - Parses the incoming request
  - Calls different modules (job analyzer, housing selector, transportation estimators)
  - Returns structured JSON

Communication is via **HTTP REST endpoints**.

---

## Backend Architecture

**Tech:** Python, FastAPI, Uvicorn, requests, BeautifulSoup, OpenAI SDK, geopy

**Key module:** `backend/main_service.py`

### Main Responsibilities

1. **Expose the API**
   - `/health` – simple health check
   - `/whatsthemove/...` – build a move plan
   - `/job-search` – analyze a job URL only

2. **Parse incoming move requests**
   - Extracts:
     - `from_city`
     - `to_city`
     - `start_month`
     - `end_month`
     - Transport/housing **flags**
     - `max_cost` (budget)
   - Wraps these into a `MoveRequest` dataclass.

3. **Orchestrate sub-services**
   - If `job_url` is present:
     - Calls **job inspector** → gets structured job data
     - Compresses that to a small `job_summary` block
   - Depending on flags:
     - Calls **U-Haul estimator** (static, no Selenium)
     - Calls **moving-help estimator** (static)
     - Adds simple blocks for:
       - bus
       - rental car
       - own car
     - If plane is selected:
       - Calls **flight distance module** to compute great-circle distance between origin and destination
   - If housing is enabled:
     - Calls **apartment selector** to return up to 10 apartments under budget

4. **Return unified JSON**

A typical response includes:

- `job_summary` (if job_url given)
- `request` (echo of inputs)
- `transportation` (only the options flagged on)
- `housing` (apartments or a “disabled” message)

---

### Backend Submodules

#### 1. Job Inspection – `backend/job_inspection/job_inspect_llm.py`

- Fetches the job posting HTML via `requests`.
- Strips scripts/styles, extracts plain text with BeautifulSoup.
- Sends the text to the OpenAI API with a carefully designed prompt.
- Forces a strict JSON output with fields like:
  - `job_title`, `company_name`, `location`
  - `employment_type`, `work_model`
  - `salary_min`, `salary_max`
  - `job_start_month/year`, `job_end_month/year`
  - `red_flags`, `quick_summary`
- `main_service.py` then condenses this into a human-friendly `job_summary`.

#### 2. Housing / Apartments – `backend/property_data/selector.py`

- Reads from an enriched apartments dataset (CSV).
- Filters by:
  - Destination city
  - Max price
- Returns a list of up to 10 apartments, which are added to the response.

#### 3. Transportation – `backend/transportation/getFlightDistance.py` and helpers

- Uses `airports.csv` + geocoding helpers to:
  - Map a city name to the nearest airport city.
  - Compute great-circle distance between two airports using `geopy.distance.great_circle`.
- `main_service.estimate_plane_cost` uses this distance to populate the `"plane"` block.

#### 4. Static Cost Estimators (Demo)

To keep things Fly.io-friendly (no headless Chrome):

- **U-Haul & moving help** are hardcoded/heuristic:
  - “Local” moves vs “Long-distance” moves produce different ballpark costs.
  - Clearly labeled as *demo* / *not live prices*.
- **Bus, rental car, own car** get simple placeholder estimates.

---

## Frontend Architecture (Conceptual)

**Tech:** React, Vite, Javascript, hitting the backend’s REST API

### Main Responsibilities

1. **Collect user input**
   - Origin city (e.g. “Madison, WI”)
   - Destination city (e.g. “Seattle, WA”)
   - Start month / end month (e.g. June → August)
   - Toggle switches / checkboxes for:
     - Already have arrangements
     - Use own car
     - Moving truck / U-Haul
     - Rental car
     - Train/bus
     - Plane
   - Housing budget slider (e.g. up to $1500)
   - Optional job posting URL

2. **Encode into backend calls**
   - Convert city names to slugs the backend understands (e.g. `madisonwi`, `seattlewa`) or URL form it expects.
   - Convert toggle states into **bit flags** (string like `"01000011"`).
   - Compose URLs for:
     - `/whatsthemove/...`  → full move plan
     - `/job-search?job_url=...` → job inspector only

3. **Render the JSON into UI**
   - **Job Summary Card**
     - Title, company, location, term dates, red flags
   - **Transportation Section**
     - One card per active transport mode (U-Haul, plane, bus, etc.)
     - Display distance, price estimates, notes
   - **Housing Section**
     - List or grid of apartment cards:
       - Name
       - Monthly rent
       - Link to listing
   - Handle loading states, error messages, and “no data” scenarios gracefully.

---

Together, they provide a fast, “snapshot” of what relocating for a given job might look like—costs, distance, housing, and potential red flags—all in one place.

## You land the J*b, we'll do the rest!
