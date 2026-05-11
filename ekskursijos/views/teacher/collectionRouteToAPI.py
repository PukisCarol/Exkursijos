import googlemaps
from django.conf import settings


class CollectionRouteToAPI:
    def __init__(self):
        self.client = googlemaps.Client(key=settings.GOOGLE_MAPS_API_KEY)

    def getCoordinates(self, address):
        result = self.client.geocode(address)
        if result:
            location = result[0]['geometry']['location']
            return location['lat'], location['lng']
        return None

    def getDistance(self, origin, destination):
        result = self.client.distance_matrix(
            origins=[origin],
            destinations=[destination],
            mode='driving'
        )
        try:
            return result['rows'][0]['elements'][0]['distance']['value']
        except (KeyError, IndexError):
            return float('inf')
