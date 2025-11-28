import sqlite3
import folium
from folium.plugins import HeatMap
import pandas as pd
import math


def plot_all_points():
    # Connect to the SQLite database
    conn = sqlite3.connect('travel_info.db')
    cursor = conn.cursor()

    # Query to get the data including address
    cursor.execute('SELECT latitude, longitude, transit_duration, street FROM travel_info')
    data = cursor.fetchall()

    # Close the database connection
    conn.close()

    # Create a base map
    m = folium.Map(location=[52.2297, 21.0122], zoom_start=12)

    min_time_green = 10
    mid_time_yellow = 25
    mid_time_red = 40
    max_time_black = 55
    max_color_val=204

    for lat, lon, travel_time, address in data:
        if travel_time is not None:
            # Determine color based on travel time
            if travel_time < min_time_green:
                color = '#0c0'
            elif travel_time > max_time_black:
                color = 'black'
            elif travel_time > mid_time_red:
                # Red to black
                color_value = int((travel_time - mid_time_red) / (max_time_black - mid_time_red) * max_color_val)
                color = f'#{max_color_val - color_value:02x}0000'
            elif travel_time > mid_time_yellow:
                # Yellow to red
                color_value = int((travel_time - mid_time_yellow) / (mid_time_red - mid_time_yellow) * max_color_val)
                color = f'#{max_color_val:02x}{max_color_val - color_value:02x}00'
            else:
                # Green to yellow
                color_value = int((travel_time - min_time_green) / (mid_time_yellow - min_time_green) * max_color_val)
                color = f'#{color_value:02x}{max_color_val:02x}00'
        else:
            color = 'gray'  # Neutral color for missing data
        # Add a label with address and travel time
        label = f"Address: {address} ({travel_time if travel_time is not None else 'N/A'} min)"
        folium.CircleMarker(location=[lat, lon], radius=4, color=color, fill=True, fill_opacity=0.7, popup=label).add_to(m)

    m.save('static/public_transport.html')


def plot_points_short_time():
    # Connect to the SQLite database
    conn = sqlite3.connect('travel_info.db')
    cursor = conn.cursor()

    # Query to get the data including address
    cursor.execute('SELECT latitude, longitude, transit_duration, street FROM travel_info WHERE transit_duration < 25')
    data = cursor.fetchall()

    # Close the database connection
    conn.close()

    # Create a base map
    m = folium.Map(location=[52.2297, 21.0122], zoom_start=12)

    # Prepare data for heatmap
    heat_data = [[lat, lon] for lat, lon, travel_time, address in data]

    # Add heatmap to the map
    HeatMap(heat_data).add_to(m)

    m.save('static/short_transport.html')


def plot_heatmap_with_metro_stations():
    # Connect to the SQLite database
    conn = sqlite3.connect('travel_info.db')
    cursor = conn.cursor()

    # Query to get the data including address
    cursor.execute('SELECT latitude, longitude, transit_duration, street FROM travel_info WHERE transit_duration < 25')
    data = cursor.fetchall()

    # Close the database connection
    conn.close()

    # Create a base map
    m = folium.Map(location=[52.2297, 21.0122], zoom_start=12)

    # Prepare data for heatmap
    heat_data = [[lat, lon] for lat, lon, travel_time, address in data]

    # Add heatmap to the map
    HeatMap(heat_data).add_to(m)

    # Read metro stations from CSV and add as blue circles
    metro_df = pd.read_csv('metro-stations.csv')

    for index, row in metro_df.iterrows():
        folium.CircleMarker(
            location=[row['Latitude'], row['Longitude']],
            radius=5,
            popup=f"{row['Name']} ({row['Line']})",
            color='blue',
            fill=True,
            fillColor='blue',
            fillOpacity=0.7,
            weight=2
        ).add_to(m)

    m.save('static/heatmap_with_metro.html')


def plot_transfer_analysis():
    """
    Creates a map showing public transport connections/transfers needed.
    Uses color coding where fewer transfers are better:
    - Green: 0 transfers (direct connection)
    - Yellow: 1 transfer
    - Orange: 2 transfers
    - Red: 3+ transfers (though none exist in current data)
    """
    # Connect to the SQLite database
    conn = sqlite3.connect('travel_info.db')
    cursor = conn.cursor()

    # Query to get data with transfer information
    cursor.execute('''
        SELECT latitude, longitude, transit_duration, transfers, street
        FROM travel_info
        WHERE transfers IS NOT NULL
        AND latitude IS NOT NULL
        AND longitude IS NOT NULL
    ''')
    data = cursor.fetchall()
    conn.close()

    # Create a base map centered on Warsaw
    m = folium.Map(location=[52.2297, 21.0122], zoom_start=12)

    # Color palette for transfers (fewer is better)
    transfer_colors = {
        0: '#2d8030',    # Deep green (excellent - no transfers)
        1: '#ffd700',    # Gold/yellow (good - 1 transfer)
        2: '#ff8c00',    # Dark orange (moderate - 2 transfers)
        3: '#dc143c'     # Crimson red (poor - 3+ transfers, if any)
    }

    def get_transfer_color(transfers):
        """Get color based on number of transfers"""
        if transfers in transfer_colors:
            return transfer_colors[transfers]
        elif transfers >= 3:
            return transfer_colors[3]  # Use red for 3+ transfers
        else:
            return '#808080'  # Gray for unknown/null values

    def get_transfer_text(transfers):
        """Get descriptive text for transfer count"""
        if transfers == 0:
            return "🚊 Direct connection (no transfers)"
        elif transfers == 1:
            return "🔄 1 transfer required"
        elif transfers == 2:
            return "🔄🔄 2 transfers required"
        else:
            return f"🔄 {transfers} transfers required"

    # Plot points on the map
    for lat, lon, transit_time, transfers, address in data:
        color = get_transfer_color(transfers)
        transfer_desc = get_transfer_text(transfers)

        # Create popup with detailed information
        popup_text = f"""
        <b>{address}</b><br>
        🚊 Transit time: {transit_time:.1f} min<br>
        {transfer_desc}<br>
        """

        # Add circle marker with size based on transit time
        radius = min(10, max(4, 4 + (transit_time or 0) / 10))

        folium.CircleMarker(
            location=[lat, lon],
            radius=radius,
            weight=0,
            fill=True,
            fillColor=color,
            fillOpacity=0.8,
            popup=folium.Popup(popup_text, max_width=300)
        ).add_to(m)

    # Add a legend
    legend_html = f'''
    <div style="position: fixed;
                bottom: 50px; left: 50px; width: 220px; height: 150px;
                background-color: white; border:2px solid grey; z-index:9999;
                font-size:14px; padding: 10px">
    <p><b>Transfer Analysis</b></p>
    <p><i class="fa fa-circle" style="color:{transfer_colors[0]}"></i> 0 transfers (direct)</p>
    <p><i class="fa fa-circle" style="color:{transfer_colors[1]}"></i> 1 transfer</p>
    <p><i class="fa fa-circle" style="color:{transfer_colors[2]}"></i> 2 transfers</p>
    <p><i class="fa fa-circle" style="color:{transfer_colors[3]}"></i> 3+ transfers</p>
    <p><small>Fewer transfers = better service</small></p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))

    # Save the map
    m.save('static/transfer_analysis.html')
    print("🔄 Transfer analysis map saved to static/transfer_analysis.html")
    print("📊 Transfer distribution:")

    # Print transfer statistics
    conn = sqlite3.connect('travel_info.db')
    cursor = conn.cursor()
    cursor.execute("SELECT transfers, COUNT(*) FROM travel_info GROUP BY transfers ORDER BY transfers")
    stats = cursor.fetchall()
    conn.close()

    for transfers, count in stats:
        if transfers is not None:
            print(f"   {transfers} transfers: {count} locations")


def plot_transport_comparison():
    """
    Creates a map showing comparison between car and public transport times.
    Uses a creative color palette:
    - Deep emerald green: Public transport faster (negative difference)
    - Light sage green: Public transport slightly slower but acceptable (0-5 min)
    - Warm amber: Moderate difference (5-25 min) - still positive neutral
    - Sunset orange: Significant difference (25-40 min)
    - Deep crimson: Very poor public transport (40-60 min)
    - Black: Extremely poor public transport (60+ min)
    """
    # Connect to the SQLite database
    conn = sqlite3.connect('travel_info.db')
    cursor = conn.cursor()

    # Query to get data where both car and transit durations exist
    cursor.execute('''
        SELECT latitude, longitude, transit_duration, car_duration_avg, street
        FROM travel_info
        WHERE transit_duration IS NOT NULL
        AND car_duration_avg IS NOT NULL
    ''')
    data = cursor.fetchall()
    conn.close()

    # Create a base map centered on Warsaw
    m = folium.Map(location=[52.2297, 21.0122], zoom_start=12)

    # Color palette thresholds (difference = transit_time - car_time)
    thresholds = {
        'excellent': 0,      # Public transport faster (green)
        'good': 10,         # Slightly slower (0-10 min) (light green)
        'acceptable': 15,   # Moderate difference (10-15 min) (amber)
        'poor': 20,         # Significant difference (15-20 min) (orange)
        'very_poor': 100    # Very poor (20+ min) (red to black)
    }

    # Creative color palette inspired by Warsaw nature and urban themes
    colors = {
        'excellent': '#006837',     # Deep forest green (Łazienki Park)
        'good': '#31a354',          # Sage green (Vistula riverbank)
        'acceptable': '#feb24c',     # Warm amber (Warsaw sunset)
        'poor': '#fd8d3c',          # Sunset orange
        'very_poor': '#bd0026',     # Deep crimson (Palace of Culture red brick)
        'extreme': '#000000'        # Black (coal/industry)
    }

    def get_color(time_diff):
        """Get color based on time difference (transit - car)"""
        if time_diff < thresholds['excellent']:
            return colors['excellent']
        elif time_diff < thresholds['good']:
            # Gradient from excellent to good
            ratio = time_diff / thresholds['good']
            return interpolate_color(colors['excellent'], colors['good'], ratio)
        elif time_diff < thresholds['acceptable']:
            # Gradient from good to acceptable
            ratio = (time_diff - thresholds['good']) / (thresholds['acceptable'] - thresholds['good'])
            return interpolate_color(colors['good'], colors['acceptable'], ratio)
        elif time_diff < thresholds['poor']:
            # Gradient from acceptable to poor
            ratio = (time_diff - thresholds['acceptable']) / (thresholds['poor'] - thresholds['acceptable'])
            return interpolate_color(colors['acceptable'], colors['poor'], ratio)
        elif time_diff < thresholds['very_poor']:
            # Gradient from poor to very poor
            ratio = (time_diff - thresholds['poor']) / (thresholds['very_poor'] - thresholds['poor'])
            return interpolate_color(colors['poor'], colors['very_poor'], ratio)
        else:
            # Gradient from very poor to extreme (black)
            ratio = min(1.0, (time_diff - 20) / 20)  # Cap at 40 min total diff (20 + 20)
            return interpolate_color(colors['very_poor'], colors['extreme'], ratio)

    def interpolate_color(color1, color2, ratio):
        """Interpolate between two hex colors"""
        # Convert hex to RGB
        r1, g1, b1 = int(color1[1:3], 16), int(color1[3:5], 16), int(color1[5:7], 16)
        r2, g2, b2 = int(color2[1:3], 16), int(color2[3:5], 16), int(color2[5:7], 16)

        # Interpolate
        r = int(r1 + (r2 - r1) * ratio)
        g = int(g1 + (g2 - g1) * ratio)
        b = int(b1 + (b2 - b1) * ratio)

        return f'#{r:02x}{g:02x}{b:02x}'

    def get_status_text(time_diff):
        """Get descriptive text for the time difference"""
        if time_diff < 0:
            return f"🚊 Public transport faster by {abs(time_diff):.1f} min"
        elif time_diff < 10:
            return f"🚊 Public transport slightly slower by {time_diff:.1f} min"
        elif time_diff < 15:
            return f"🚗 Car moderately faster by {time_diff:.1f} min"
        elif time_diff < 20:
            return f"🚗 Car significantly faster by {time_diff:.1f} min"
        else:
            return f"🚗 Car much faster by {time_diff:.1f} min"

    # Plot points on the map
    for lat, lon, transit_time, car_time, address in data:
        time_diff = transit_time - car_time
        color = get_color(time_diff)
        status = get_status_text(time_diff)

        # Create popup with detailed information
        popup_text = f"""
        <b>{address}</b><br>
        🚊 Public transport: {transit_time:.1f} min<br>
        🚗 Car: {car_time:.1f} min<br>
        <b>{status}</b>
        """

        # Add circle marker with size based on difference magnitude
        radius = min(12, max(6, 6 + abs(time_diff) / 8))

        folium.CircleMarker(
            location=[lat, lon],
            radius=radius,
            weight=0,
            fill=True,
            fillColor=color,
            fillOpacity=0.9,
            popup=folium.Popup(popup_text, max_width=300)
        ).add_to(m)

    # Add a legend
    legend_html = f'''
    <div style="position: fixed;
                bottom: 50px; left: 50px; width: 200px; height: 180px;
                background-color: white; border:2px solid grey; z-index:9999;
                font-size:14px; padding: 10px">
    <p><b>Transport Comparison</b></p>
    <p><i class="fa fa-circle" style="color:{colors['excellent']}"></i> Public transport faster</p>
    <p><i class="fa fa-circle" style="color:{colors['good']}"></i> Slightly slower (0-10 min)</p>
    <p><i class="fa fa-circle" style="color:{colors['acceptable']}"></i> Moderate difference (10-15 min)</p>
    <p><i class="fa fa-circle" style="color:{colors['poor']}"></i> Significant difference (15-20 min)</p>
    <p><i class="fa fa-circle" style="color:{colors['very_poor']}"></i> Very poor (20+ min)</p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))

    # Save the map
    m.save('static/transport_comparison.html')
    print("🗺️  Transport comparison map saved to static/transport_comparison.html")
    print("🎨 Color palette:")
    print(f"   🟢 Green: Public transport competitive")
    print(f"   🟡 Amber: Moderate car advantage")
    print(f"   🔴 Red-Black: Poor public transport performance")


# Call the functions
plot_all_points()
plot_points_short_time()
plot_heatmap_with_metro_stations()
plot_transport_comparison()
plot_transfer_analysis()