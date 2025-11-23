# create helper methods to calculate the distance of a plane trip between two cities

import csv
from geopy import distance
import os
from . import distanceHelper

# CSV parameters
airport_city_name_col = 2
airport_state_name_col = 3
airport_city_lat_col = 5
airport_city_long_col = 6

script_dir = os.path.dirname(os.path.abspath(__file__))
    
csv_path = os.path.join(script_dir, 'datasets', 'airports.csv')

# find the city with an airport closest to entered city
# - helper method
def fetch_airport_city(city):
    # look for specified city first
    with open(csv_path, newline='') as csvfile:
        csvreader = csv.reader(csvfile, delimiter=',')
        next(csvreader)
        for row in csvreader:
            if(row[airport_city_name_col] == city):
                csvfile.close()
                return city

    cityCoords = distanceHelper.fetch_coords(city)
    cityState = distanceHelper.fetch_state(city)

    # look for adjacent aiport city in same state
    with open(csv_path, newline='') as csvfile:
        csvreader = csv.reader(csvfile, delimiter=',')
        next(csvreader)
        for row in csvreader:
            # for every city in the same state
            if (row[airport_state_name_col] == cityState):
                currCoords = (row[airport_city_lat_col], row[airport_city_long_col])
                if(distanceHelper.calc_pyth_distance(cityCoords, currCoords) < 50):
                    csvfile.close()
                    return city

    # look for adjacent aiport city in general
    with open(csv_path, newline='') as csvfile:
        csvreader = csv.reader(csvfile, delimiter=',')
        next(csvreader)
        for row in csvreader:
            # for every city within the 
            currCoords = (row[airport_city_lat_col], row[airport_city_long_col])
            if(distanceHelper.calc_pyth_distance(cityCoords, currCoords) < 150):
                csvfile.close()
                return city

# calculate the distance between two cities via flight
# - main flight distance method
def calc_flight_distance(city1, city2):
    acity1, acity2 = fetch_airport_city(city1), fetch_airport_city(city2)
    dgc = distance.great_circle(distanceHelper.fetch_coords(acity1), distanceHelper.fetch_coords(acity2))
    return dgc.miles