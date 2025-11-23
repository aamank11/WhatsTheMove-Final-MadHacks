import csv
import requests

INPUT_CSV = "rentcast_neenah_seattle_rentals_with_url.csv"
OUTPUT_CSV = "rentcast_neenah_seattle_rentals_with_url_v2.csv"

GOOGLE_API_KEY = "key"
GOOGLE_CSE_ID = "id"

rate_limit_hit = False

def get_listing_website(formatted_address: str) -> str | None:
    global rate_limit_hit

    if rate_limit_hit or not formatted_address:
        return None

    query = f"{formatted_address} apartments for rent"
    params = {
        "key": GOOGLE_API_KEY,
        "cx": GOOGLE_CSE_ID,
        "q": query,
        "num": 1,
    }

    try:
        resp = requests.get(
            "https://www.googleapis.com/customsearch/v1",
            params=params,
            timeout=10,
        )

        if resp.status_code == 429:
            print("Hit search API quota, stopping further lookups.")
            rate_limit_hit = True
            return None

        resp.raise_for_status()
        data = resp.json()
        items = data.get("items")
        if not items:
            return None

        return items[0].get("link")
    except Exception as e:
        print(f"Search error for '{formatted_address}': {e}")
        return None


def main():
    with open(INPUT_CSV, newline="", encoding="utf-8") as f_in:
        reader = csv.DictReader(f_in)
        fieldnames = list(reader.fieldnames or [])

        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f_out:
            writer = csv.DictWriter(f_out, fieldnames=fieldnames)
            writer.writeheader()

            for i, row in enumerate(reader, start=1):
                # Only look up if missing
                if not row.get("listingWebsite"):
                    addr = row.get("formattedAddress", "") or ""
                    website = get_listing_website(addr)
                    row["listingWebsite"] = website or ""
                    print(f"[{i}] {addr} -> {website}")
                writer.writerow(row)


if __name__ == "__main__":
    main()
