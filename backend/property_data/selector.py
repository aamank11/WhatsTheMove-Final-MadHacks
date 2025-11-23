import csv
import os
from typing import List, Dict, Any, Tuple


CSV_FILENAME = os.path.join(
    os.path.dirname(__file__),
    "neenah_seattle_datasets",
    "rentcast_neenah_seattle_rentals_with_url.csv",
)

OUTPUT_FIELDS = [
    "id",
    "formattedAddress",
    "city",
    "state",
    "zipCode",
    "propertyType",
    "bedrooms",
    "bathrooms",
    "squareFootage",
    "yearBuilt",
    "status",
    "price",
    "listingWebsite",
]


def _normalize_city_state_input(city_input: str) -> Tuple[str, str]:
    city_input = city_input.strip()
    if "," in city_input:
        city_part, state_part = city_input.split(",", 1)
        return city_part.strip().lower(), state_part.strip().upper()
    else:
        return city_input.lower(), ""


def _load_listings(csv_path: str = CSV_FILENAME) -> List[Dict[str, Any]]:
    if not os.path.exists(csv_path):
        raise FileNotFoundError(
            f"CSV file not found at {csv_path}. "
            "Make sure you've generated the CSV and placed it in property_data/."
        )

    listings: List[Dict[str, Any]] = []
    with open(csv_path, mode="r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            listings.append(row)
    return listings


def find_top_apartments(
    destination_city: str,
    max_price: float,
    csv_path: str = CSV_FILENAME,
    max_results: int = 10,
) -> List[Dict[str, Any]]:
    """
    Find up to max_results apartments in the given city with price <= max_price,
    using the local CSV.

    destination_city: "Seattle" or "Seattle, WA"
    """
    city_filter, state_filter = _normalize_city_state_input(destination_city)
    all_listings = _load_listings(csv_path)

    filtered: List[Dict[str, Any]] = []

    for row in all_listings:
        row_city = (row.get("city") or "").strip().lower()
        row_state = (row.get("state") or "").strip().upper()

        if row_city != city_filter:
            continue
        if state_filter and row_state != state_filter:
            continue

        # parse price
        try:
            price_val = float(row.get("price", 0))
        except (TypeError, ValueError):
            continue

        if price_val <= max_price:
            row_copy = dict(row)
            row_copy["price"] = price_val  # keep numeric for sorting
            filtered.append(row_copy)

    # sort by price ascending
    filtered.sort(key=lambda r: r["price"])

    top = filtered[:max_results]
    output: List[Dict[str, Any]] = []

    for row in top:
        entry: Dict[str, Any] = {}
        for field in OUTPUT_FIELDS:
            value = row.get(field)

            # Convert blank/None to "NA"
            if value is None or (isinstance(value, str) and value.strip() == ""):
                entry[field] = "NA"
            else:
                # keep price as a number if present
                if field == "price":
                    try:
                        entry[field] = float(value)
                    except (TypeError, ValueError):
                        entry[field] = "NA"
                else:
                    entry[field] = value
        output.append(entry)

    return output


if __name__ == "__main__":
    city = "Seattle, WA"
    max_rent = 1500
    apartments = find_top_apartments(city, max_rent)
    print(f"Top {len(apartments)} apartments in {city} under ${max_rent}:")
    for apt in apartments:
        print(
            f"- {apt['formattedAddress']} | ${apt['price']}/mo | "
            f"{apt['bedrooms']} bd / {apt['bathrooms']} ba | website: {apt['listingWebsite']}"
        )
