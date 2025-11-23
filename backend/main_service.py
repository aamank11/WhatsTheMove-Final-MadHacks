# backend/main_service.py

import json
from dataclasses import dataclass
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .property_data.selector import find_top_apartments
from .job_inspection.job_inspect_llm import analyze_job_url
from .transportation.getFlightDistance import calc_flight_distance

# ---------- FastAPI app setup ----------

app = FastAPI(
    title="WhatsTheMove Backend",
    description="Move planning API (transportation, housing, job summary)",
    version="0.1.0",
)

# CORS - adjust allowed origins as needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "https://whatsthemove.com",
        "https://whatsthemove-final-madhacks.fly.dev/",
        "https://whatsthemove-final-madhacks.fly.dev",
        "http://localhost:5175"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Constants / helpers ----------

def build_city_slug_map() -> dict[str, str]:
    """
    Build a map like:
      "madisonwi" -> "Madison, WI"
      "seattlewa" -> "Seattle, WA"
    from a list of canonical city names.
    """
    city_names = [
        "Madison, WI",
        "Seattle, WA",
        "Neenah, WI",
        # add more here
    ]

    mapping: dict[str, str] = {}
    for full in city_names:
        city, state = [part.strip() for part in full.split(",")]
        # "Madison, WI" -> "madisonwi"
        slug = f"{city.lower().replace(' ', '')}{state.lower()}"
        mapping[slug] = full
    return mapping


CITY_SLUG_MAP = build_city_slug_map()


MONTH_NAME_TO_NUM = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


def slug_to_city_state(slug: str) -> str:
    """
    Convert 'madisonwi' -> 'Madison, WI' for display / estimates.
    Falls back to the raw slug if unknown.
    """
    return CITY_SLUG_MAP.get(slug.lower(), slug)


def choose_move_dates(start_month: str, end_month: str):
    """
    Pick concrete dates from month names.

    For now:
      - loading/pickup = 1st of start_month this year
      - unloading      = loading + 1 day
    Returns three strings in MM/DD/YYYY format:
      pickup_date_str, loading_date_str, unloading_date_str
    """
    year = datetime.now().year

    start_num = MONTH_NAME_TO_NUM.get(start_month.lower(), datetime.now().month)
    # if end month missing/invalid, just use start month
    end_num = MONTH_NAME_TO_NUM.get(end_month.lower(), start_num)

    pickup_dt = datetime(year, start_num, 1)
    loading_dt = pickup_dt
    unloading_dt = pickup_dt + timedelta(days=1)

    pickup_str = pickup_dt.strftime("%m/%d/%Y")
    loading_str = loading_dt.strftime("%m/%d/%Y")
    unloading_str = unloading_dt.strftime("%m/%d/%Y")

    return pickup_str, loading_str, unloading_str


def compute_month_duration(
    start_month: Optional[int],
    start_year: Optional[int],
    end_month: Optional[int],
    end_year: Optional[int],
) -> Optional[int]:
    """
    Compute month difference like:
    5/2026 -> 8/2026  => 3 months
    using: (end_year - start_year)*12 + (end_month - start_month)

    Return None if any input is missing, or a computation error occurs.
    """
    try:
        if (
            start_month is None
            or start_year is None
            or end_month is None
            or end_year is None
        ):
            return None

        return (end_year - start_year) * 12 + (end_month - start_month)
    except Exception:
        return None


def build_job_summary(job_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a compact summary from the LLM result.
    Fields:
      - job_title
      - move_to_destination
      - start_month
      - end_month
      - duration_months
    Replace missing fields with "NA".
    """
    # Raw values from LLM
    raw_title = job_data.get("job_title")
    raw_location = job_data.get("location")
    start_month_num = job_data.get("job_start_month")
    start_year = job_data.get("job_start_year")
    end_month_num = job_data.get("job_end_month")
    end_year = job_data.get("job_end_year")

    # Format start/end as M/YYYY or NA
    if start_month_num and start_year:
        start_month_str = f"{start_month_num}/{start_year}"
    else:
        start_month_str = "NA"

    if end_month_num and end_year:
        end_month_str = f"{end_month_num}/{end_year}"
    else:
        end_month_str = "NA"

    # Duration in months
    duration = compute_month_duration(
        start_month_num, start_year, end_month_num, end_year
    )
    if duration is None:
        duration_str = "NA"
    else:
        duration_str = str(duration)

    # Normalize title & location with NA if missing
    job_title = raw_title if raw_title else "NA"
    move_to_destination = raw_location if raw_location else "NA"

    # IMPORTANT: insertion order here controls JSON key order
    summary: Dict[str, Any] = {}
    summary["job_title"] = job_title
    summary["move_to_destination"] = move_to_destination
    summary["start_month"] = start_month_str
    summary["end_month"] = end_month_str
    summary["duration_months"] = duration_str

    return summary


# ---------- Data model ----------


@dataclass
class MoveRequest:
    from_city_slug: str
    to_city_slug: str
    start_month: str
    end_month: str
    # "##" -> 1st bit = U-Haul, 2nd bit = moving service
    uhaul_and_moving_flags: str
    # "######" -> have-arrangements, drive-own-car, moving-truck, rental-car, train-bus, plane
    transport_flags: str
    apartment_max_cost: int

    # 2-bit segment: "##"
    @property
    def use_uhaul_truck(self) -> bool:
        # 1st bit = U-Haul? (1 yes, 0 no)
        return self.uhaul_and_moving_flags[0] == "1"

    @property
    def need_moving_help(self) -> bool:
        # 2nd bit = moving service? (1 yes, 0 no)
        return self.uhaul_and_moving_flags[1] == "1"

    # 6-bit segment: "######"
    @property
    def no_transport_needed(self) -> bool:
        # 1st bit = have-arrangements
        return self.transport_flags[0] == "1"

    @property
    def use_own_car(self) -> bool:
        # 2nd bit = drive-own-car
        return self.transport_flags[1] == "1"

    @property
    def use_moving_truck_mode(self) -> bool:
        # 3rd bit = moving-truck (if you ever want a separate mode)
        return self.transport_flags[2] == "1"

    @property
    def need_rental_car(self) -> bool:
        # 4th bit = rental-car
        return self.transport_flags[3] == "1"

    @property
    def use_bus(self) -> bool:
        # 5th bit = train-bus
        return self.transport_flags[4] == "1"

    @property
    def use_plane(self) -> bool:
        # 6th bit = plane
        return self.transport_flags[5] == "1"

    @property
    def need_housing(self) -> bool:
        # In this URL scheme there is no explicit housing bit,
        # so we treat housing as always enabled.
        return True


# ---------- URL parsing ----------


def parse_move_request(
    from_city: str,
    to_city: str,
    start_month: str,
    end_month: str,
    uhaul_and_moving_flags: str,  # "##"
    transport_flags: str,         # "######"
    max_cost_str: str,
) -> MoveRequest:
    """
    URL pattern (behind /whatsthemove prefix):

      {from_city_slug}/
      {to_city_slug}/
      {start_month}/
      {end_month}/
      {uh_mv_flags}/      # "##"
      {transport_flags}/  # "######"
      {price}

    ##:
      bit0 = U-Haul? (1 yes, 0 no)
      bit1 = moving service? (1 yes, 0 no)

    ###### (left → right):
      bit0 = have-arrangements
      bit1 = drive-own-car
      bit2 = moving-truck
      bit3 = rental-car
      bit4 = train-bus
      bit5 = plane
    """
    if len(uhaul_and_moving_flags) != 2 or any(c not in "01" for c in uhaul_and_moving_flags):
        raise ValueError(
            f"uhaul_and_moving_flags must be a 2-character 0/1 string, got '{uhaul_and_moving_flags}'"
        )

    if len(transport_flags) != 6 or any(c not in "01" for c in transport_flags):
        raise ValueError(
            f"transport_flags must be a 6-character 0/1 string, got '{transport_flags}'"
        )

    try:
        max_cost = int(max_cost_str)
    except ValueError:
        raise ValueError(f"Apartment max cost must be an int, got '{max_cost_str}'")

    return MoveRequest(
        from_city_slug=from_city,
        to_city_slug=to_city,
        start_month=start_month,
        end_month=end_month,
        uhaul_and_moving_flags=uhaul_and_moving_flags,
        transport_flags=transport_flags,
        apartment_max_cost=max_cost,
    )


# ---------- Backend calls / adapters ----------


def estimate_uhaul_truck_cost(req: MoveRequest) -> Dict[str, Any]:
    """
    Hardcoded / heuristic U-Haul truck estimates for demo.
    This avoids Selenium/ChromeDriver so it works on Fly.
    """
    pickup_city = slug_to_city_state(req.from_city_slug)
    dropoff_city = slug_to_city_state(req.to_city_slug)

    # Simple heuristic based on "is this a long-distance move?"
    long_distance = pickup_city != dropoff_city

    if long_distance:
        options = [
            {
                "truck_type": "10-foot truck",
                "estimated_base_rate": 450.0,
                "estimated_mileage_fees": 220.0,
                "estimated_total": 670.0,
            },
            {
                "truck_type": "15-foot truck",
                "estimated_base_rate": 520.0,
                "estimated_mileage_fees": 240.0,
                "estimated_total": 760.0,
            },
        ]
    else:
        options = [
            {
                "truck_type": "10-foot truck",
                "estimated_base_rate": 45.0,
                "estimated_mileage_fees": 40.0,
                "estimated_total": 85.0,
            },
            {
                "truck_type": "15-foot truck",
                "estimated_base_rate": 55.0,
                "estimated_mileage_fees": 45.0,
                "estimated_total": 100.0,
            },
        ]

    return {
        "enabled": True,
        "note": (
            "Demo U-Haul cost estimates (static). "
            "Not live prices; for hackathon/demo purposes only."
        ),
        "pickup_city": pickup_city,
        "dropoff_city": dropoff_city,
        "options": options,
    }


def estimate_moving_help_cost(req: MoveRequest) -> Dict[str, Any]:
    """
    Hardcoded moving-help style estimates for demo.
    """
    loading_address = slug_to_city_state(req.from_city_slug)
    unloading_address = slug_to_city_state(req.to_city_slug)

    loading_dt = datetime.now()
    unloading_dt = loading_dt + timedelta(days=1)

    loading_date_str = loading_dt.strftime("%m/%d/%Y")
    unloading_date_str = unloading_dt.strftime("%m/%d/%Y")

    return {
        "enabled": True,
        "note": (
            "Demo moving-help estimates (static). "
            "Not live pricing."
        ),
        "loading_address": loading_address,
        "unloading_address": unloading_address,
        "loading_date": loading_date_str,
        "unloading_date": unloading_date_str,
        "providers": [
            {
                "name": "QuickMove Helpers",
                "hours": 2,
                "crew_size": 2,
                "estimated_total": 220.0,
            },
            {
                "name": "College Movers Co.",
                "hours": 3,
                "crew_size": 2,
                "estimated_total": 310.0,
            },
        ],
    }


def get_housing_options(req: MoveRequest) -> Dict[str, Any]:
    """
    Use the enriched CSV (via apartment_selector.find_top_apartments)
    to get up to 10 apartments in the destination city under the user's max rent.
    """
    destination_city_str = slug_to_city_state(req.to_city_slug)  # e.g. "Seattle, WA"

    apartments = find_top_apartments(
        destination_city=destination_city_str,
        max_price=req.apartment_max_cost,
        max_results=10,
    )

    return {
        "enabled": True,
        "destination_city": destination_city_str,
        "max_price": req.apartment_max_cost,
        "results_count": len(apartments),
        "apartments": apartments,
    }


def estimate_plane_cost(req: MoveRequest) -> Dict[str, Any]:
    """
    Use calc_flight_distance helper to compute great-circle distance
    between the nearest airports to the origin and destination cities,
    and include that in the JSON response.
    """
    # Convert slugs like "madisonwi" -> "Madison, WI"
    origin_full = slug_to_city_state(req.from_city_slug)   # e.g. "Madison, WI"
    dest_full = slug_to_city_state(req.to_city_slug)       # e.g. "Seattle, WA"

    origin_city = origin_full.split(",")[0].strip()
    dest_city = dest_full.split(",")[0].strip()

    distance_miles = None
    error = None

    try:
        distance_miles = calc_flight_distance(origin_city, dest_city)
    except Exception as e:
        error = str(e)

    plane_info: Dict[str, Any] = {
        "enabled": True,
        "origin_city": origin_full,
        "destination_city": dest_full,
        "distance_miles": distance_miles,
        "description": "Great-circle distance between nearest airports to origin and destination.",
    }

    if distance_miles is not None:
        plane_info["distance_km"] = round(distance_miles * 1.60934, 1)

    if error is not None:
        plane_info["error"] = error

    return plane_info


def estimate_bus_cost(req: MoveRequest) -> Dict[str, Any]:
    return {
        "enabled": True,
        "description": "Placeholder bus estimate",
        "example_price": 120.0,
    }


def estimate_rental_car_cost(req: MoveRequest) -> Dict[str, Any]:
    return {
        "enabled": True,
        "description": "Placeholder rental car estimate",
        "example_price": 600.0,
    }


def estimate_own_car_cost(req: MoveRequest) -> Dict[str, Any]:
    return {
        "enabled": True,
        "description": "Placeholder own-car gas estimate",
        "example_price": 300.0,
    }


# ---------- High-level orchestrator ----------


def build_move_plan(
    req: MoveRequest,
    job_info: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Master function: looks at the MoveRequest and conditionally calls
    each backend. Returns a single JSON-serializable dict.

    If job_info is provided (output from the job LLM), a 'job_summary'
    block is added FIRST in the output, with:
      - job_title
      - move_to_destination
      - start_month
      - end_month
      - duration_months
    and any missing values represented as "NA".
    """

    result: Dict[str, Any] = {}

    # --- 1) Job summary (first in output) ---
    if job_info is not None:
        result["job_summary"] = build_job_summary(job_info)

    # --- 2) Original request metadata ---
    result["request"] = {
        "from_city": req.from_city_slug,
        "to_city": req.to_city_slug,
        "start_month": req.start_month,
        "end_month": req.end_month,
        "flags": {
            "uhaul_and_moving": req.uhaul_and_moving_flags,  # "##"
            "transport": req.transport_flags,                # "######"
        },
        "apartment_max_cost": req.apartment_max_cost,
    }

    # --- 3) Transportation ---
    result["transportation"] = {}
    if req.no_transport_needed:
        result["transportation"]["skipped"] = True
        result["transportation"]["reason"] = (
            "User indicated they already have travel arrangements."
        )
    else:
        result["transportation"]["skipped"] = False

        if req.use_uhaul_truck:
            result["transportation"]["uhaul_truck"] = estimate_uhaul_truck_cost(req)

        if req.use_own_car:
            result["transportation"]["own_car"] = estimate_own_car_cost(req)

        if req.need_rental_car:
            result["transportation"]["rental_car"] = estimate_rental_car_cost(req)

        if req.use_bus:
            result["transportation"]["bus"] = estimate_bus_cost(req)

        if req.use_plane:
            result["transportation"]["plane"] = estimate_plane_cost(req)

        if req.need_moving_help:
            result["transportation"]["moving_help"] = estimate_moving_help_cost(req)

    # --- 4) Housing ---
    if req.need_housing:
        result["housing"] = get_housing_options(req)
    else:
        result["housing"] = {
            "enabled": False,
            "reason": "User indicated they do not need housing help.",
        }

    return result


# ---------- API routes ----------


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """
    Simple health check for Fly / monitoring.
    """
    return {"status": "ok"}


@app.get(
    "/whatsthemove/{from_city_slug}/{to_city_slug}/{start_month}/{end_month}/{uh_mv_flags}/{transport_flags}/{max_cost}"
)
async def get_move_plan(
    from_city_slug: str,
    to_city_slug: str,
    start_month: str,
    end_month: str,
    uh_mv_flags: str,       # "##"
    transport_flags: str,   # "######"
    max_cost: int,
    job_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Main endpoint.

    URL pattern (after hostname):

      /whatsthemove/
        {from_city_slug}/
        {to_city_slug}/
        {start_month}/
        {end_month}/
        {uh_mv_flags}/      # 2 bits
        {transport_flags}/  # 6 bits
        {max_cost}

    uh_mv_flags (2 bits, left → right):
      [0] U-Haul? (1 yes, 0 no)
      [1] moving service? (1 yes, 0 no)

    transport_flags (6 bits, left → right):
      [0] have-arrangements
      [1] drive-own-car
      [2] moving-truck
      [3] rental-car
      [4] train-bus
      [5] plane
    """
    try:
        req = parse_move_request(
            from_city=from_city_slug,
            to_city=to_city_slug,
            start_month=start_month,
            end_month=end_month,
            uhaul_and_moving_flags=uh_mv_flags,
            transport_flags=transport_flags,
            max_cost_str=str(max_cost),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Optional job analysis via LLM
    job_info: Optional[Dict[str, Any]] = None
    if job_url:
        try:
            job_info = analyze_job_url(job_url)
        except Exception as e:
            # Don't fail the whole request if job analysis breaks
            job_info = {
                "job_title": None,
                "location": None,
                "job_start_month": None,
                "job_start_year": None,
                "job_end_month": None,
                "job_end_year": None,
                "job_analysis_error": str(e),
            }

    move_plan = build_move_plan(req, job_info=job_info)
    return move_plan


@app.get("/job-search")
async def job_search(job_url: str) -> Dict[str, Any]:
    job_url = job_url.strip()

    if not (job_url.startswith("http://") or job_url.startswith("https://")):
        raise HTTPException(
            status_code=400,
            detail="Job URL must start with http:// or https://",
        )

    try:
        analysis = analyze_job_url(job_url)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing job URL: {str(e)}",
        )

    return analysis
