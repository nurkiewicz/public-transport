#! /usr/bin/env python3

import requests
import time
from datetime import datetime, timedelta
import csv
import random
import os
import sqlite3


def convert_duration_to_minutes(duration_text):
    duration_parts = duration_text.split()
    total_minutes = 0
    for i in range(0, len(duration_parts), 2):
        value = int(duration_parts[i])
        unit = duration_parts[i + 1]
        if 'hour' in unit:
            total_minutes += value * 60
        elif 'min' in unit:
            total_minutes += value
    return total_minutes


def get_transit_info(api_key, origin, destination):
    endpoint = "https://maps.googleapis.com/maps/api/directions/json"
    now = datetime.now()
    # Calculate the number of days until next Monday
    days_until_monday = (7 - now.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7
    next_monday = now + timedelta(days=days_until_monday)
    eight_am_next_monday = datetime(next_monday.year, next_monday.month, next_monday.day, 8, 0)
    departure_time = int(eight_am_next_monday.timestamp())

    params = {
        "origin": origin + ", Warsaw",
        "destination": destination + ", Warsaw",
        "mode": "transit",
        "departure_time": departure_time,
        "key": api_key
    }
    response = requests.get(endpoint, params=params)
    if response.status_code == 200:
        data = response.json()
        if data['routes']:
            # Sort routes by shortest total travel time
            sorted_routes = sorted(data['routes'], key=lambda r: r['legs'][0]['duration']['value'])
            fastest_route = sorted_routes[0]
            duration = fastest_route['legs'][0]['duration']['text']
            total_minutes = convert_duration_to_minutes(duration)
            steps = fastest_route['legs'][0]['steps']
            
            # Extract route and count transfers
            route_info = []
            transfers = 0
            for step in steps:
                travel_mode = step['travel_mode']
                if travel_mode == 'TRANSIT':
                    transit_details = step['transit_details']
                    if 'name' in transit_details['line']:
                        line_name = transit_details['line']['name']
                        vehicle_type = transit_details['line']['vehicle']['type']
                        route_info.append(f"Take {vehicle_type} {line_name}")
                    else:
                        route_info.append(step['transit_details'])
                    transfers += 1
                else:
                    route_info.append(f"Walk {step['distance']['text']}")
            # Adjust transfers count (transfers are one less than the number of transit steps)
            transfers = max(0, transfers - 1)
            return total_minutes, transfers
        else:
            return "No routes found", 0
    else:
        return f"Error: {response.status_code}", 0

def get_car_travel_time(api_key, origin, destination):
    endpoint = "https://maps.googleapis.com/maps/api/directions/json"
    now = datetime.now()
    params = {
        "origin": origin + ", Warsaw",
        "destination": destination + ", Warsaw",
        "mode": "driving",
        "departure_time": "now",
        "traffic_model": "best_guess",
        "key": api_key
    }
    response = requests.get(endpoint, params=params)
    if response.status_code == 200:
        data = response.json()
        if data['routes']:
            # Sort routes by shortest total travel time
            sorted_routes = sorted(data['routes'], key=lambda r: r['legs'][0]['duration']['value'])
            fastest_route = sorted_routes[0]
            duration = fastest_route['legs'][0]['duration']['text']
            total_minutes = convert_duration_to_minutes(duration)
            # Check for duration in traffic
            if 'duration_in_traffic' in fastest_route['legs'][0]:
                duration_in_traffic = fastest_route['legs'][0]['duration_in_traffic']['text']
                max_duration_minutes = convert_duration_to_minutes(duration_in_traffic)
                return total_minutes, max_duration_minutes
            return total_minutes, None
        else:
            return "No routes found", None
    else:
        return f"Error: {response.status_code}", None

def initialize_database(db_name):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS travel_info (
            street TEXT PRIMARY KEY,
            latitude REAL,
            longitude REAL,
            transit_duration REAL,
            transfers INTEGER,
            car_duration_avg REAL
        )
    ''')
    conn.commit()
    return conn

# Example usage
api_key = os.getenv('API_KEY')
# origin = "Elektry 1"
destination = "Metro Świętokrzyska"
# duration, transfers = get_transit_info(api_key, origin, destination)
# print(f"{origin}\t{transfers}\t{duration} minutes")

csv_file_path = 'Adres_uniwersalny_2022.02.08.csv'

# Initialize database
conn = initialize_database('travel_info.db')
cursor = conn.cursor()

# Print the number of records already in the database
cursor.execute("SELECT COUNT(*) FROM travel_info")
record_count = cursor.fetchone()[0]
print(f"Number of records already in the database: {record_count}")

with open(csv_file_path, newline='', encoding='utf-8') as csvfile:
    reader = csv.reader(csvfile, delimiter=';')
    count = 0
    for i, row in enumerate(reader):
        if i == 0:
            continue  # Skip header
        origin = f"{row[5]}, {row[6]}"  # Use columns 6 and 7 as origin
        
        # Check if the address already exists in the database
        cursor.execute("SELECT * FROM travel_info WHERE street = ?", (origin,))
        result = cursor.fetchone()
        if result is not None:
            continue
        if random.random() > 0.01:
            continue

        transit_duration, transfers = get_transit_info(api_key, origin, destination)
        car_duration, max_duration_minutes = get_car_travel_time(api_key, origin, destination)
        # Calculate average car duration
        car_duration_avg = (car_duration + max_duration_minutes) / 2
        # Extract latitude and longitude from the CSV file
        latitude = float(row[9].replace(',', '.'))
        longitude = float(row[10].replace(',', '.'))
        print(f"{origin}\t{latitude}\t{longitude}\t{transfers}\t{transit_duration}\t{car_duration_avg}")
        count += 1

        # Store the result in the database
        cursor.execute(
            "INSERT INTO travel_info (street, latitude, longitude, transit_duration, transfers, car_duration_avg) VALUES (?, ?, ?, ?, ?, ?)",
            (origin, latitude, longitude, transit_duration, transfers, car_duration_avg)
        )
        conn.commit()

# Close the database connection
conn.close()
