"""
Music API module for interacting with iTunes Search API.
Provides functions to search for songs and retrieve track details.
"""

import requests
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

ITUNES_SEARCH_URL = "https://itunes.apple.com/search"
ITUNES_LOOKUP_URL = "https://itunes.apple.com/lookup"


def search_songs(query: str, limit: int = 10) -> List[Dict]:
    """
    Search for songs using iTunes Search API.

    Args:
        query: Search query string (e.g., artist name, song title)
        limit: Maximum number of results to return (default: 10)

    Returns:
        List of dictionaries containing track information with keys:
        - track_id: iTunes track ID
        - track_name: Song title
        - artist_name: Artist name
        - collection_name: Album name
        - duration_ms: Track duration in milliseconds
        - primary_genre_name: Genre name
        - preview_url: URL to audio preview
        - track_view_url: URL to track page on iTunes
        - artwork_url_100: URL to album artwork (100x100)

    Raises:
        requests.RequestException: If API request fails
    """
    params = {
        "term": query,
        "media": "music",
        "entity": "song",
        "limit": limit,
        "country": "US"
    }

    try:
        response = requests.get(ITUNES_SEARCH_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        results = []
        for track in data.get("results", []):
            duration_ms = track.get("trackTimeMillis", 0)
            duration_sec = duration_ms // 1000 if duration_ms else 0
            minutes = duration_sec // 60
            seconds = duration_sec % 60
            duration_str = f"{minutes}:{seconds:02d}"

            result = {
                "track_id": str(track.get("trackId", "")),
                "track_name": track.get("trackName", ""),
                "artist_name": track.get("artistName", ""),
                "collection_name": track.get("collectionName", ""),
                "duration_ms": duration_ms,
                "duration_sec": duration_sec,
                "duration_str": duration_str,
                "primary_genre_name": track.get("primaryGenreName", ""),
                "preview_url": track.get("previewUrl", ""),
                "track_view_url": track.get("trackViewUrl", ""),
                "artwork_url_100": track.get("artworkUrl100", ""),
            }
            results.append(result)

        return results

    except requests.RequestException as e:
        logger.error(f"iTunes API request failed: {e}")
        raise
    except (KeyError, ValueError) as e:
        logger.error(f"Failed to parse iTunes API response: {e}")
        raise


def get_track_details(track_id: str) -> Dict:
    """
    Lookup specific track by iTunes track ID.

    Args:
        track_id: iTunes track ID

    Returns:
        Dictionary containing track information with same structure as search_songs

    Raises:
        requests.RequestException: If API request fails
        ValueError: If track_id is invalid or track not found
    """
    params = {
        "id": track_id,
        "media": "music",
        "entity": "song"
    }

    try:
        response = requests.get(ITUNES_LOOKUP_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get("resultCount", 0) == 0:
            raise ValueError(f"Track with ID {track_id} not found")

        track = data["results"][0]

        duration_ms = track.get("trackTimeMillis", 0)
        duration_sec = duration_ms // 1000 if duration_ms else 0
        minutes = duration_sec // 60
        seconds = duration_sec % 60
        duration_str = f"{minutes}:{seconds:02d}"

        return {
            "track_id": str(track.get("trackId", "")),
            "track_name": track.get("trackName", ""),
            "artist_name": track.get("artistName", ""),
            "collection_name": track.get("collectionName", ""),
            "duration_ms": duration_ms,
            "duration_sec": duration_sec,
            "duration_str": duration_str,
            "primary_genre_name": track.get("primaryGenreName", ""),
            "preview_url": track.get("previewUrl", ""),
            "track_view_url": track.get("trackViewUrl", ""),
            "artwork_url_100": track.get("artworkUrl100", ""),
        }

    except requests.RequestException as e:
        logger.error(f"iTunes API request failed: {e}")
        raise
    except (KeyError, IndexError, ValueError) as e:
        logger.error(f"Failed to get track details: {e}")
        raise
