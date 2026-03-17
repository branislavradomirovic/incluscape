import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class Geocoder:
    """Geocode place names to lat/lon using geopy Nominatim."""

    def __init__(self, user_agent: str = "incluscape-geocoder"):
        self._geolocator = None
        self.user_agent = user_agent

    def _get_geolocator(self):
        if self._geolocator is None:
            try:
                from geopy.geocoders import Nominatim
                from geopy.extra.rate_limiter import RateLimiter
                geolocator = Nominatim(user_agent=self.user_agent)
                self._geolocator = RateLimiter(geolocator.geocode, min_delay_seconds=1)
            except Exception as exc:
                logger.warning("geopy not available: %s", exc)
                self._geolocator = False
        return self._geolocator

    def geocode(self, place_name: str) -> Tuple[Optional[float], Optional[float]]:
        geocode_fn = self._get_geolocator()
        if not geocode_fn:
            return None, None
        try:
            location = geocode_fn(place_name)
            if location:
                return location.latitude, location.longitude
        except Exception as exc:
            logger.debug("Geocoding failed for '%s': %s", place_name, exc)
        return None, None

    def geocode_batch(self, locations: List[Dict]) -> List[Dict]:
        """Geocode a list of location dicts in-place."""
        from config import Config
        if not Config.ENABLE_GEOCODING:
            return locations
        for loc in locations:
            if not loc.get("geocoded"):
                lat, lon = self.geocode(loc["place_name"])
                if lat is not None:
                    loc["latitude"] = lat
                    loc["longitude"] = lon
                    loc["geocoded"] = 1
        return locations
