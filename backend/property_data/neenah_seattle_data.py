import requests
import csv
from typing import List, Dict

API_KEY = "b61457d683024d1dad19b13c4ca20926"

BASE_URL = "https://api.rentcast.io/v1/listings/rental/long-term"
HEADERS = {
    "Accept": "application/json",
    "X-Api-Key": API_KEY,
}

def fetch_rentals_for_city(city: str, state: str, max_results: int = 150, page_limit: int = 100) -> List[Dict]:
    listings: List[Dict] = []
    offset = 0

    while len(listings) < max_results:
        remaining = max_results - len(listings)
        limit = min(page_limit, remaining)

        params = {
            "city": city,
            "state": state,
            "status": "Active",  # only active rentals
            "limit": limit,
            "offset": offset,
        }

        resp = requests.get(BASE_URL, headers=HEADERS, params=params)
        resp.raise_for_status()
        batch = resp.json()

        # If no more results, break
        if not batch:
            break

        listings.extend(batch)
        offset += limit

        if len(batch) < limit:
            break

    return listings

def write_listings_to_csv(filename: str, listings: List[Dict]) -> None:
    # fields we care about
    fieldnames = [
        "id",
        "formattedAddress",
        "city",
        "state",
        "zipCode",
        "latitude",
        "longitude",
        "propertyType",
        "bedrooms",
        "bathrooms",
        "squareFootage",
        "yearBuilt",
        "status",
        "price",
        "listingType",
        "listedDate",
        "daysOnMarket",
    ]

    with open(filename, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for listing in listings:
            row = {key: listing.get(key) for key in fieldnames}
            writer.writerow(row)


def main():
    # Tweak this to how many we need
    max_per_city = 200

    neenah_listings = fetch_rentals_for_city("Neenah", "WI", max_results=max_per_city)
    print(f"Fetched {len(neenah_listings)} rental listings for Neenah, WI")

    seattle_listings = fetch_rentals_for_city("Seattle", "WA", max_results=max_per_city)
    print(f"Fetched {len(seattle_listings)} rental listings for Seattle, WA")

    # Combine into one dataset
    all_listings = neenah_listings + seattle_listings

    write_listings_to_csv("rentcast_neenah_seattle_rentals.csv", all_listings)
    print("Saved to rentcast_neenah_seattle_rentals.csv")


if __name__ == "__main__":
    main()
