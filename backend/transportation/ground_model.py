"""
https://newsroom.aaa.com/wp-content/uploads/2024/08/YDC-Brochure-FINAL-9.2024.pdf
https://www.caee.utexas.edu/prof/kockelman/public_html/TRB26LongDistanceBus.pdf
https://www.kaggle.com/datasets/kushleshkumar/cornell-car-rental-dataset?resource=download


Ground transportation cost model for rental cars and bus.
"""

import pandas as pd
import math


class GroundModel:
    """
    Holds ground transportation cost multipliers.

    @param csv_path Path to rental car CSV with 'vehicle.type' and 'rate.daily'.
    """

    def __init__(self, csv_path: str = "backend/transportation/datasets/CarRentalData.csv"):
        """Load CSV and precompute median daily rate and other cost data."""
        self.daily_rate_by_type = {}

        df = pd.read_csv(csv_path)

        # Only need two columns
        df = df[["vehicle.type", "rate.daily"]].copy()

        # Ensure rate.daily is numeric and drop missing
        df["rate.daily"] = pd.to_numeric(df["rate.daily"])
        df = df.dropna(subset=["vehicle.type", "rate.daily"])

        # Median daily rate for each vehicle.type
        grouped = df.groupby("vehicle.type")["rate.daily"].median()
        daily_rental = grouped.to_dict()

        # print("[RentalModel] Loaded types:", sorted(self.daily_rate_by_type.keys()))

        fuel_cpm = {
            "Small Sedan":          11.12,
            "Medium Sedan":         12.54,
            "Subcompact SUV":       13.37,
            "Compact SUV (FWD)":    12.70,
            "Medium SUV (4WD)":     16.46,
            "Midsize Pickup":       18.81,
            "1/2 Ton Pickup":       22.16,
        }

        maint_cpm = {
            "Small Sedan":          9.55,
            "Medium Sedan":         10.89,
            "Subcompact SUV":       10.06,
            "Compact SUV (FWD)":    10.87,
            "Medium SUV (4WD)":     11.10,
            "Midsize Pickup":       10.88,
            "1/2 Ton Pickup":       9.88,
        }

        # Helper: average cents-per-mile over a set of AAA types, return dollars/mile
        def avg_dollars_per_mile(keys, cpm_dict):
            """
            Average cents-per-mile for keys, returned in dollars-per-mile.

            @param keys AAA vehicle type keys.
            @param cpm_dict Mapping from type to cents-per-mile.
            @return Average cost in dollars-per-mile.
            """
            return sum(cpm_dict[k] for k in keys) / len(keys) / 100.0

        # Groupings for your simple classes
        car_keys = ["Small Sedan", "Medium Sedan"]
        minivan_suv_keys = ["Subcompact SUV", "Compact SUV (FWD)", "Medium SUV (4WD)"]
        truck_keys = ["Midsize Pickup", "1/2 Ton Pickup"]

        # Take values in translate to case for car, minivan, suv, truck, and van
        fuel_per_mile = {
            "car":     avg_dollars_per_mile(car_keys,  fuel_cpm),
            "minivan": avg_dollars_per_mile(minivan_suv_keys,  fuel_cpm),
            "suv":     avg_dollars_per_mile(minivan_suv_keys,  fuel_cpm),
            "truck":   avg_dollars_per_mile(truck_keys, fuel_cpm),
            "van":     avg_dollars_per_mile(truck_keys, fuel_cpm),
        }

        # distance/500 = key, corresponds to specific multiplier
        BUS_CPM_BY_BUCKET = {
            0: 0.2794,
            1: 0.2413,
            2: 0.1905,
        }

        maintenance_per_mile = {
            "car":     avg_dollars_per_mile(car_keys,  maint_cpm),
            "minivan": avg_dollars_per_mile(minivan_suv_keys,  maint_cpm),
            "suv":     avg_dollars_per_mile(minivan_suv_keys,  maint_cpm),
            "truck":   avg_dollars_per_mile(truck_keys, maint_cpm),
            "van":     avg_dollars_per_mile(truck_keys, maint_cpm),
        }

        self.rental_multipliers = {
            "DailyRental":        daily_rental,
            "FuelPerMile":        fuel_per_mile,
            "MaintenancePerMile": maintenance_per_mile,
            "BusCPM":             BUS_CPM_BY_BUCKET
        }

    def get_all_multipliers(self) -> dict:
        """
        Get all ground cost multipliers.

        @return Shallow copy of rental_multipliers dict.
        """
        return dict(self.rental_multipliers)


# Global instance
ground_model = GroundModel()

if __name__ == "__main__":
    # When run directly, just print out the multipliers.
    print("\nMultipliers from RentalModel (via getter):")
    print(ground_model.get_all_multipliers())