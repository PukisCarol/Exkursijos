from ..models import Place 
import urllib.parse 
import googlemaps
from django.conf import settings


class RouteToAPI:
    def __init__(self):
        key = getattr(settings, 'GOOGLE_MAPS_API_KEY', '')
        self.client = googlemaps.Client(key=key) if key else None

    def getDistancesAndTimes(self, places):
        """
        Returns a dict of (i, j) -> {'distance': meters, 'duration': seconds}
        for all pairs of places.
        """
        if not self.client or not places:
            return {}

        coords = [(p.latitude, p.longitude) for p in places]
        n = len(coords)
        result = {}

        try:
            matrix = self.client.distance_matrix(
                origins=coords,
                destinations=coords,
                mode='driving',
            )
            for i in range(n):
                for j in range(n):
                    if i == j:
                        continue
                    element = matrix['rows'][i]['elements'][j]
                    if element.get('status') == 'OK':
                        result[(i, j)] = {
                            'distance': element['distance']['value'],
                            'duration': element['duration']['value'],
                        }
                    else:
                        result[(i, j)] = {'distance': float('inf'), 'duration': float('inf')}
        except Exception:
            for i in range(n):
                for j in range(n):
                    if i != j:
                        result[(i, j)] = {'distance': float('inf'), 'duration': float('inf')}

        return result

    def getDistanceAndTime(self, origin, destination):
        """
        Returns {'distance': meters, 'duration': seconds} between two (lat, lng) tuples.
        """
        if not self.client:
            return {'distance': float('inf'), 'duration': float('inf')}

        try:
            matrix = self.client.distance_matrix(
                origins=[origin],
                destinations=[destination],
                mode='driving',
            )
            element = matrix['rows'][0]['elements'][0]
            if element.get('status') == 'OK':
                return {
                    'distance': element['distance']['value'],
                    'duration': element['duration']['value'],
                }
        except Exception:
            pass

        return {'distance': float('inf'), 'duration': float('inf')}

    def getMap2(self, places):
        """
        Returns a Google Static Maps URL showing the route through the given places in order.
        """
        if not places:
            return ''

        base = 'https://maps.googleapis.com/maps/api/staticmap'
        key = getattr(settings, 'GOOGLE_MAPS_API_KEY', '')

        markers = '&'.join(
            f'markers=color:red%7Clabel:{i + 1}%7C{p.latitude},{p.longitude}'
            for i, p in enumerate(places)
        )

        path_points = '%7C'.join(f'{p.latitude},{p.longitude}' for p in places)
        path = f'path=color:0x0000ffff%7Cweight:5%7C{path_points}'

        url = f'{base}?size=600x400&{markers}&{path}&key={key}'
        return url
    
    def getMap(self, places):
        """
        Returns a Google Static Maps URL showing the route through the given places in order.
        """
        if not places:
            return ''

        # Fallback to an empty string if settings doesn't have it
        key = getattr(settings, 'GOOGLE_MAPS_API_KEY', '')

        base_url = 'https://maps.googleapis.com/maps/api/staticmap' #'[https://maps.googleapis.com/maps/api/staticmap](https://maps.googleapis.com/maps/api/staticmap)'

        # Start with core URL parameters
        params = {
            'size': '600x400',
        }
        
        # Only add the key parameter if it actually contains a value
        if key:
            params['key'] = key
            
        query_parts = [urllib.parse.urlencode(params)]

        # Add individual markers safely
        for i, p in enumerate(places):
            marker_str = f"color:red|label:{i + 1}|{p.latitude},{p.longitude}"
            query_parts.append(f"markers={urllib.parse.quote(marker_str)}")

        # Add the polyline path connecting them
        path_points = "|".join(f"{p.latitude},{p.longitude}" for p in places)
        path_str = f"color:0x0000ffff|weight:5|{path_points}"
        query_parts.append(f"path={urllib.parse.quote(path_str)}")

        # Join all parameters cleanly with single ampersands
        return f"{base_url}?{'&'.join(query_parts)}"
    
    def createPlaceFromAddress(self, address_string):
        """
        Geocodes an address string and creates a Place record with real coordinates.
        """
        if not self.client:
            print("Google Maps client is not initialized.")
            return None

        try:
            # Call Google Geocoding API
            geocode_result = self.client.geocode(address_string)

            if geocode_result:
                # Extract latitude and longitude from the response payload
                location = geocode_result[0]['geometry']['location']
                lat = location['lat']
                lng = location['lng']

                # Create your database object with real coordinates
                place = Place.objects.create(
                    name=address_string.split(',')[0],  # Uses the first part of address as a name
                    latitude=lat,
                    longitude=lng
                )
                print(f"Successfully created: {address_string} ({lat}, {lng})")
                return place
            else:
                print(f"Could not find coordinates for address: {address_string}")
        except Exception as e:
            print(f"Geocoding failed due to an error: {e}")
        
        return None
