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
        self.base_cpm = self.df["ITIN_YIELD"].median() / 100.0
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
        # print("Top 8 carriers by passengers: ", self.top_8_carriers)

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

        # Show multipliers
        """for k, v in self.multipliers.items():
            print("\n---", k, "---")
            print(v)"""

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


# Runs only once per process:
air_model = AirModel()
if __name__ == "__main__":
    # When run directly, just print out the multipliers.
    print("\nMultipliers from AirModel (via getter):")
    print(air_model.get_all_multipliers())