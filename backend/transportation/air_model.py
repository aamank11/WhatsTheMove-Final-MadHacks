"""
https://www.transtats.bts.gov/DatabaseInfo.asp?QO_VQ=EFI&Yv0x=D

Air ticket cost model for DB1B data.

Loads DB1B tickets, computes price-per-mile multipliers,
and exposes them via an AirModel class and a global air_model.
"""

import pandas as pd
import numpy as np


class AirModel:
    """
    Air fare model wrapper for DB1B tickets.

    @param csv_path Path to DB1B ticket CSV.
    """

    # Carrier code, human readable name (top 8)
    carrier_names = {
        "HA": "Hawaiian Airlines",
        "WN": "Southwest Airlines",
        "AS": "Alaska Airlines",
        "UA": "United Airlines",
        "B6": "JetBlue Airways",
        "DL": "Delta Air Lines",
        "AA": "American Airlines",
        "F9": "Frontier Airlines",
    }

    def __init__(self, csv_path: str = "T_DB1B_TICKET.csv"):
        """
        Load CSV, clean DB1B data, and compute all multipliers.
        """

        # Load data
        df = pd.read_csv(csv_path)

        # Clean Data
        df = df[
            (df["DOLLAR_CRED"] == 1) &
            (df["BULK_FARE"] == 0) &
            (df["ITIN_FARE"] > 0) &
            (df["MILES_FLOWN"] > 0) &
            (df["ITIN_GEO_TYPE"] == 1) &
            (df["ONLINE"] == 1)
        ].copy()

        # Ensure numeric types
        numeric_cols = ["ITIN_YIELD", "ITIN_FARE", "MILES_FLOWN", "DISTANCE", "DISTANCE_GROUP"]
        df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")

        # Drop any row with null in main fields
        df = df.dropna(subset=["ITIN_YIELD", "MILES_FLOWN"])

        # Save cleaned df on the instance
        self.df = df

        # Compute Base CPM (dollars per mile)
        # NOTE: ITIN_YIELD is already fare per mile; do NOT divide by 100.
        self.base_cpm = self.df["ITIN_YIELD"].median()
        print("BaseCPM:", self.base_cpm)

        # Carrier multipliers (all carriers first)
        self.carrier_mult_full = self.make_multiplier("REPORTING_CARRIER")

        # Get top 8 carriers based off passengers
        carrier_counts = (
            self.df.groupby("REPORTING_CARRIER")["PASSENGERS"]
                  .sum()
                  .sort_values(ascending=False)
        )

        self.top_8_carriers = list(carrier_counts.head(8).index)
        print("Top 8 carriers by passengers: ", self.top_8_carriers)

        # Filter carrier_mult to only top 8
        self.carrier_mult = {}
        for carrier in self.top_8_carriers:
            self.carrier_mult[carrier] = self.carrier_mult_full.get(carrier)

        # Distance group multiplier, dist/500
        self.dist_mult = self.make_multiplier("DISTANCE_GROUP")

        # Roundtrip (0 = OW, 1 = RT)
        self.roundtrip_mult = self.make_multiplier("ROUNDTRIP")

        # Origin market multiplier (optional)
        # origin_market_mult = make_multiplier("ORIGIN_CITY_MARKET_ID")

        # Put multipliers into a dictionary
        self.multipliers = {
            "BaseCPM": self.base_cpm,
            "CarrierMultiplier": self.carrier_mult,
            "DistanceGroupMultiplier": self.dist_mult,
            "RoundTripMultiplier": self.roundtrip_mult,
            # "OriginMarketMultiplier": origin_market_mult
        }

        # Show multipliers (optional)
        """
        for k, v in self.multipliers.items():
            print("\n---", k, "---")
            print(v)
        """

    def make_multiplier(self, field_name: str) -> dict:
        """
        Compute median ITIN_YIELD/BaseCPM by field.

        @param field_name Column to group by.
        @return Dict of {field_value: multiplier}.
        """
        grouped = self.df.groupby(field_name)["ITIN_YIELD"].median()
        return (grouped / self.base_cpm).to_dict()

    # Getter

    def get_all_multipliers(self) -> dict:
        """
        Get all multipliers in one dict.

        @return Dict with BaseCPM and all multiplier maps.
        """
        return {
            "BaseCPM": float(self.base_cpm),
            "CarrierMultiplier": dict(self.carrier_mult),
            "DistanceGroupMultiplier": dict(self.dist_mult),
            "RoundTripMultiplier": dict(self.roundtrip_mult),
        }

    def price_for_distance(self, max_distance: int = 6000) -> dict:
        """
        Estimate price-per-mile multipliers for 500-mile distance bands
        for each of the top 8 carriers, up to max_distance miles.

        Bands:
          0-499, 500-999, 1000-1499, ..., up to covering max_distance.

        @param max_distance Maximum distance in miles (e.g. 6000).
        @return Dict mapping distance_range_str -> {carrier_name: multiplier}.
        """

        # Number of 500-mile groups needed to cover max_distance
        # e.g. 6000 -> 12 groups (0-499 ... 5500-5999)
        num_groups = max(1, int((max_distance - 1) // 500) + 1)

        results = {}

        for group in range(1, num_groups + 1):
            # Compute label like "0-499", "500-999", ...
            low = (group - 1) * 500
            high = group * 500 - 1
            range_label = f"{low}-{high}"

            # Get multiplier for that distance group (default to 1.0 if missing)
            dist_mult_val = self.dist_mult.get(group, 1.0)

            carrier_results = {}

            for carrier in self.top_8_carriers:
                carrier_name = self.carrier_names.get(carrier, carrier)
                carrier_mult_val = self.carrier_mult.get(carrier, 1.0)

                # Basic per-mile estimate: base_cpm * distance_mult * carrier_mult
                multiplier = self.base_cpm * dist_mult_val * carrier_mult_val

                carrier_results[carrier_name] = multiplier

            results[range_label] = carrier_results

        return results


# Runs only once per process:
air_model = AirModel()

if __name__ == "__main__":
    # Compute multipliers for distance bands up to 6000 miles
    prices_by_band = air_model.price_for_distance(max_distance=6000)

    # Flatten into rows for CSV
    rows = []
    for band_label, carrier_dict in prices_by_band.items():
        for carrier_name, mult in carrier_dict.items():
            rows.append({
                "distance_band": band_label,   # e.g. "0-499"
                "carrier": carrier_name,       # e.g. "Delta Air Lines"
                "multiplier": mult             # price-per-mile multiplier
            })

    df = pd.DataFrame(rows)

    # Write to CSV
    df.to_csv("air_price_multipliers_by_band.csv", index=False)

    print("Saved CSV to air_price_multipliers_by_band.csv")