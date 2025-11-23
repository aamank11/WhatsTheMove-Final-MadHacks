# Copy the following code and paste it into your site's <body> section, 
# where you want the search box and the search results to render.

#<script async src="https://cse.google.com/cse.js?cx=90e748ce127094279">
#</script>
#<div class="gcse-search"></div>

import csv
import requests

# CONFIG
INPUT_CSV = "rentcast_neenah_seattle_rentals.csv" 
OUTPUT_CSV = "rentcast_neenah_seattle_rentals_with_url.csv"

GOOGLE_API_KEY = "key"
GOOGLE_CSE_ID = "id"


def get_listing_website(formatted_address: str) -> str | None:
    if not formatted_address:
        return None

    query = f"{formatted_address} apartments for rent"

    params = {
        "key": GOOGLE_API_KEY,
        "cx": GOOGLE_CSE_ID,
        "q": query,
        "num": 1,  # top result only
    }

    try:
        resp = requests.get("https://www.googleapis.com/customsearch/v1",
                            params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items")
        if not items:
            return None

        url = items[0].get("link")

        return url
    except Exception as e:
        print(f"Search error for '{formatted_address}': {e}")
        return None


def main():
    with open(INPUT_CSV, newline="", encoding="utf-8") as f_in:
        reader = csv.DictReader(f_in)
        fieldnames = list(reader.fieldnames or [])

        # Add new column if not already present
        if "listingWebsite" not in fieldnames:
            fieldnames.append("listingWebsite")

        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f_out:
            writer = csv.DictWriter(f_out, fieldnames=fieldnames)
            writer.writeheader()

            for i, row in enumerate(reader, start=1):
                addr = row.get("formattedAddress", "") or ""
                website = get_listing_website(addr)
                row["listingWebsite"] = website or ""

                print(f"[{i}] {addr} -> {website}")
                writer.writerow(row)


if __name__ == "__main__":
    main()


