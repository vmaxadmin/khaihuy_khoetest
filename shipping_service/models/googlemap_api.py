# -*- coding: utf-8 -*-

from datetime import datetime
import googlemaps


def get_distance(source, destination, api_key):
    matrix_gmaps = googlemaps.Client(key=api_key)
    directions_result = matrix_gmaps.distance_matrix(
        source, destination, mode="driving", units='metric', departure_time=datetime.now())
    rows = directions_result.get('rows')
    if rows:
        elements = rows[0].get('elements')
        if elements:
            distance = elements[0].get('distance')
            if distance:
                return distance.get('value', 0)
    return 0
