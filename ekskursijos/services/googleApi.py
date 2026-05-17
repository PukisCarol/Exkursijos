import googlemaps
from django.conf import settings


class GoogleAPI:
    def __init__(self):
        key = getattr(settings, 'GOOGLE_MAPS_API_KEY', '')
        self.client = googlemaps.Client(key=key) if key else None

    def requestRecomendedObjects(self, addresses, criteria):
        if not self.client:
            return []
        place_types = criteria.get('place_types', [])
        max_results = criteria.get('max_places', 10) * 3

        results = []
        seen_ids = set()

        search_types = place_types if place_types else ['tourist_attraction']

        for lat, lng in addresses:
            for place_type in search_types:
                try:
                    response = self.client.places_nearby(
                        location=(lat, lng),
                        radius=5000,
                        type=place_type.lower(),
                    )
                    for item in response.get('results', []):
                        place_id = item.get('place_id', '')
                        if place_id in seen_ids:
                            continue
                        seen_ids.add(place_id)
                        results.append({
                            'name': item.get('name', ''),
                            'latitude': item['geometry']['location']['lat'],
                            'longitude': item['geometry']['location']['lng'],
                            'types': item.get('types', []),
                            'place_id': place_id,
                        })
                        if len(results) >= max_results:
                            break
                except Exception:
                    continue

            if len(results) >= max_results:
                break

        return results
