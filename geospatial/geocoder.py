import logging
from typing import Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class Geocoder:
    """Geocode place names to lat/lon using free geocoding providers."""

    def __init__(self, user_agent: str = "sipmt-geocoder"):
        self._providers = None
        self.user_agent = user_agent

    def _get_providers(self) -> List[Tuple[str, Callable[[str], object]]]:
        if self._providers is None:
            providers: List[Tuple[str, Callable[[str], object]]] = []
            try:
                from geopy.geocoders import ArcGIS, Nominatim, Photon
                from geopy.extra.rate_limiter import RateLimiter

                nominatim = Nominatim(user_agent=self.user_agent)
                photon = Photon(user_agent=self.user_agent)
                arcgis = ArcGIS(user_agent=self.user_agent)

                # Use free providers in a fallback chain for better coordinate coverage.
                providers.append(("nominatim", RateLimiter(nominatim.geocode, min_delay_seconds=1.0)))
                providers.append(("photon", RateLimiter(photon.geocode, min_delay_seconds=0.7)))
                providers.append(("arcgis", RateLimiter(arcgis.geocode, min_delay_seconds=0.5)))
            except Exception as exc:
                logger.warning("geopy not available: %s", exc)
            self._providers = providers
        return self._providers or []

    @staticmethod
    def _candidate_queries(place_name: str) -> List[str]:
        base = (place_name or "").strip()
        if not base:
            return []
        queries = [base]
        if "," not in base:
            queries.append(f"{base}, Serbia")
        return queries

    def geocode(self, place_name: str) -> Tuple[Optional[float], Optional[float]]:
        providers = self._get_providers()
        if not providers:
            return None, None

        for query in self._candidate_queries(place_name):
            for provider_name, geocode_fn in providers:
                try:
                    location = geocode_fn(query)
                    if location:
                        return location.latitude, location.longitude
                except Exception as exc:
                    logger.debug(
                        "Geocoding failed for '%s' with provider '%s': %s",
                        query,
                        provider_name,
                        exc,
                    )
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
