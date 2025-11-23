# backend/main_service.py

import json
from dataclasses import dataclass
from typing import Dict, Any
from datetime import datetime, timedelta

from typing import Dict, Any, Optional

from property_data.selector import find_top_apartments

from job_inspection.job_inspect_llm import analyze_job_url 
from uhaul_scraper import get_truck_options, get_moving_help_options

# Later we'll import real functions like:
# from uhaul_scraper.uhaul_scraper import estimate_uhaul_cost
# from property_data.neenah_seattle_data import get_apartments_for_city
# from transportation.getDistance import get_distance_miles
# from job_inspection.job_inspect_llm import analyze_job_posting





CITY_SLUG_MAP = {
    "madisonwi": "Madison, WI",
    "seattlewa": "Seattle, WA",
    "neenahwi": "Neenah, WI",
    # add more as you support them
}

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
    Convert 'madisonwi' -> 'Madison, WI' for U-Haul search.
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

    Return None if any input is missing or invalid.
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
    duration = compute_month_duration(start_month_num, start_year, end_month_num, end_year)
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
    flags: str            # "01000011"
    apartment_max_cost: int

    @property
    def no_transport_needed(self) -> bool:
        return self.flags[0] == "1"

    @property
    def use_uhaul_truck(self) -> bool:
        return self.flags[1] == "1"

    @property
    def use_own_car(self) -> bool:
        return self.flags[2] == "1"

    @property
    def need_rental_car(self) -> bool:
        return self.flags[3] == "1"

    @property
    def use_bus(self) -> bool:
        return self.flags[4] == "1"

    @property
    def use_plane(self) -> bool:
        return self.flags[5] == "1"

    @property
    def need_moving_help(self) -> bool:
        return self.flags[6] == "1"

    @property
    def need_housing(self) -> bool:
        return self.flags[7] == "1"


# ---------- URL parsing ----------

def parse_move_request_from_path(path: str) -> MoveRequest:
    """
    path example:
      "whatsthemove/madisonwi/seattlewa/june/august/01000011/1500"

    For now, this is just a plain string parser; later this will be tied to a real HTTP route.
    """
    # Strip leading/trailing slashes and split
    parts = path.strip("/").split("/")

    if len(parts) != 7:
        raise ValueError(f"Expected 7 path components, got {len(parts)}: {parts}")

    prefix, from_city, to_city, start_month, end_month, flags, max_cost_str = parts

    if prefix.lower() != "whatsthemove":
        raise ValueError(f"Invalid prefix '{prefix}', expected 'whatsthemove'")

    if len(flags) != 8 or any(c not in "01" for c in flags):
        raise ValueError(f"Flags must be an 8-character 0/1 string, got '{flags}'")

    try:
        max_cost = int(max_cost_str)
    except ValueError:
        raise ValueError(f"Apartment max cost must be an int, got '{max_cost_str}'")

    return MoveRequest(
        from_city_slug=from_city,
        to_city_slug=to_city,
        start_month=start_month,
        end_month=end_month,
        flags=flags,
        apartment_max_cost=max_cost,
    )


# ---------- Stub backend calls (to be replaced by your real code) ----------

def estimate_uhaul_truck_cost(req: MoveRequest) -> Dict[str, Any]:
    pickup_city = slug_to_city_state(req.from_city_slug)
    dropoff_city = slug_to_city_state(req.to_city_slug)

    # For hackathon demo: always use today's date so U-Haul actually returns options
    pickup_date_str = datetime.now().strftime("%m/%d/%Y")

    return get_truck_options(
        pickup=pickup_city,
        dropoff=dropoff_city,
        pickup_date_str=pickup_date_str,
    )



def estimate_moving_help_cost(req: MoveRequest) -> Dict[str, Any]:
    loading_address = slug_to_city_state(req.from_city_slug)
    unloading_address = slug_to_city_state(req.to_city_slug)

    # Same trick: use today + 1 day
    loading_dt = datetime.now()
    unloading_dt = loading_dt.replace(day=loading_dt.day + 1)  # quick hack

    loading_date_str = loading_dt.strftime("%m/%d/%Y")
    unloading_date_str = unloading_dt.strftime("%m/%d/%Y")

    loading_time = "Morning"
    unloading_time = "Afternoon"

    return get_moving_help_options(
        loading_address=loading_address,
        unloading_address=unloading_address,
        loading_date=loading_date_str,
        loading_time=loading_time,
        unloading_date=unloading_date_str,
        unloading_time=unloading_time,
    )



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
    TEMPORARY: will call your flight_ticket_estimation logic later.
    """
    return {
        "enabled": True,
        "description": "Placeholder plane ticket estimates",
        "example_economy_price": 320.0,
    }


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
        "flags": req.flags,
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



# Terminal entrypoint for now

if __name__ == "__main__":
    # 1) Ask user for job URL (for now; frontend will handle later)
    job_url = input("Paste a job posting URL (or leave blank to skip): ").strip()
    job_info = None

    if job_url:
        try:
            print("Analyzing job posting via LLM...")
            job_info = analyze_job_url(job_url)
        except Exception as e:
            print(f"Warning: job analysis failed: {e}")
            job_info = None

    # 2) For now, still use a hard-coded path example
    example_path = "whatsthemove.com/madisonwi/seattlewa/june/august/01000011/1500"
    req = parse_move_request_from_path(example_path)

    move_plan = build_move_plan(req, job_info=job_info)

    print(json.dumps(move_plan, indent=2))


