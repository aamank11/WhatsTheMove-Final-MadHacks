# contains general helper methods for calculating distance

import csv
import math
import os

# CSV parameters
city_name_col = 0
city_state_col = 3
city_lat_col = 5
city_long_col = 6

script_dir = os.path.dirname(os.path.abspath(__file__))
    
csv_path = os.path.join(script_dir, 'datasets', 'uscities.csv')


# find the coordinates of a city
# - helper method
def fetch_coords(city):
    with open(csv_path, newline='') as csvfile:
        csvreader = csv.reader(csvfile, delimiter=',')
        next(csvreader)
        for row in csvreader:
            if(row[city_name_col] == city):
                currCoords = (row[city_lat_col], row[city_long_col])
                csvfile.close()
                return currCoords

def fetch_state(city):
    with open(csv_path, newline='') as csvfile:
        csvreader = csv.reader(csvfile, delimiter=',')
        next(csvreader)
        for row in csvreader:
            if(row[city_name_col] == city):
                csvfile.close()
                return row[city_state_col]

# calculate the flat distance using the Pythagorean Theorem
# - helper method
def calc_pyth_distance(coords1, coords2):
    return math.sqrt(math.pow( ( float(coords1[0]) - float(coords2[0]) ), 2 ) + math.pow( float(coords1[1]) - float(coords2[1]), 2 ) )
