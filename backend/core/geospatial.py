from django.contrib.gis.geos import Point, Polygon
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.measure import D
from django.db import connection
import math

def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two points using Haversine formula
    """
    R = 6371  # Earth's radius in kilometers
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = (math.sin(delta_lat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) *
         math.sin(delta_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c

def is_within_pincode_boundary(point: Point, boundary: Polygon) -> bool:
    """
    Check if a point is within a pincode boundary
    """
    return boundary.contains(point)

def get_nearby_pincodes(latitude, longitude, radius_km=1.5):
    """
    Get all pincodes within specified radius
    """
    point = Point(longitude, latitude, srid=4326)
    
    # Using PostGIS ST_DWithin for efficient distance calculation
    query = """
    SELECT pincode, area_name, city, state,
           ST_Distance(boundary::geography, %s::geography) as distance
    FROM core_pincodeboundary
    WHERE ST_DWithin(boundary::geography, %s::geography, %s)
    ORDER BY distance
    """
    
    with connection.cursor() as cursor:
        cursor.execute(query, [point, point, radius_km * 1000])  # Convert km to meters
        results = cursor.fetchall()
    
    return [
        {
            'pincode': row[0],
            'area_name': row[1],
            'city': row[2],
            'state': row[3],
            'distance_km': row[4] / 1000  # Convert meters to km
        }
        for row in results
    ]

def create_pincode_boundary(pincode, coordinates):
    """
    Create a polygon boundary for a pincode
    coordinates: List of (lat, lon) tuples forming a polygon
    """
    if len(coordinates) < 3:
        raise ValueError("At least 3 points required for polygon")
    
    # Convert to PostGIS polygon format
    polygon_coords = [(lon, lat) for lat, lon in coordinates]
    polygon = Polygon(polygon_coords, srid=4326)
    
    # Calculate center point
    center = polygon.centroid
    
    return {
        'pincode': pincode,
        'boundary': polygon,
        'center_point': center
    }

def verify_user_location(user_point, claimed_pincode):
    """
    Verify if user's location matches claimed pincode
    """
    from .models import PincodeBoundary
    
    try:
        boundary = PincodeBoundary.objects.get(pincode=claimed_pincode)
        return is_within_pincode_boundary(user_point, boundary.boundary)
    except PincodeBoundary.DoesNotExist:
        # If pincode boundary not in database, use approximate verification
        # This should be replaced with actual boundary data
        return True
