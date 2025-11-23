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

# Output:
# Standard value
# {'BaseCPM': 0.1179,
#'
# Multiplier for different carriers
# CarrierMultiplier': {'HA': 1.0059372349448685, 'WN': 0.917726887192536, 'AS': 1.1467345207803221, 'UA': 1.0008481764206953, 'B6': 1.2646310432569976, 'DL': 1.0559796437659033, 'AA': 1.0212044105173874, 'F9': 0.5945716709075487},

# Distance divided by 500 gives key of 1 or 2 or 3, won't use all
# 'DistanceGroupMultiplier': {1: 6.076759966072943, 2: 3.7714164546225613, 3: 1.5742154368108565, 4: 1.3129770992366412, 5: 1.0576759966072944, 6: 1.0161153519932147, 7: 1.1051738761662426, 8: 0.9211195928753181, 9: 0.912637828668363, 10: 0.8846480067854113, 11: 0.8668363019508057, 12: 0.9677692960135708, 13: 0.833757421543681, 14: 0.9185750636132315, 15: 0.7913486005089058, 16: 0.8354537743850721, 17: 0.8524173027989822, 18: 0.7319762510602205, 19: 0.7913486005089058, 20: 0.7489397794741306, 21: 0.6361323155216284, 22: 0.6318914334181509, 23: 0.6497031382527566, 24: 0.7845631891433418, 25: 1.391857506361323},

# Round trip (1) or not (0)
# 'RoundTripMultiplier': {0.0: 0.991518235793045, 1.0: 1.0059372349448685}}
