import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MapGenerator:
    """Build Folium maps from location data."""

    def __init__(self):
        from config import Config
        self.default_center = Config.DEFAULT_MAP_CENTER
        self.default_zoom = Config.DEFAULT_MAP_ZOOM

    def build_map(
        self,
        locations: List[Dict[str, Any]],
        center: Optional[List[float]] = None,
        zoom: Optional[int] = None,
    ):
        """Return a folium.Map with markers for each geocoded location."""
        try:
            import folium
        except ImportError:
            logger.error("folium is not installed. Run: pip install folium")
            return None

        m = folium.Map(
            location=center or self.default_center,
            zoom_start=zoom or self.default_zoom,
            tiles="OpenStreetMap",
        )

        for loc in locations:
            lat = loc.get("latitude")
            lon = loc.get("longitude")
            if lat is None or lon is None:
                continue
            place_name = loc.get("place_name", "Unknown")
            location_type = loc.get("location_type", "")
            context = (loc.get("context", "") or "")[:220]
            popup_html = (
                "<div style='font-size:15px;line-height:1.45;min-width:280px;max-width:420px;'>"
                f"<div style='font-size:18px;font-weight:700;margin-bottom:4px'>{place_name}</div>"
                f"<div style='font-size:14px;margin-bottom:6px'><b>Type:</b> {location_type or 'general'}</div>"
                f"<div style='font-size:14px;white-space:normal;word-wrap:break-word'>{context}</div>"
                "</div>"
            )
            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup(popup_html, max_width=460),
                tooltip=place_name,
                icon=folium.Icon(color="blue", icon="info-sign"),
            ).add_to(m)

        return m
