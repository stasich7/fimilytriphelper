from __future__ import annotations

from agents.hotel_search.adapters.base import AggregatorAdapter
from agents.hotel_search.errors import AdapterUnavailableError
from agents.hotel_search.models import HotelResult, SearchRequest


class OzonTravelAdapter(AggregatorAdapter):
    name = "ozon_travel"

    def search(self, request: SearchRequest, area: str) -> list[HotelResult]:
        _ = (request, area)
        raise AdapterUnavailableError(
            "ozon_travel adapter is not implemented yet. Current blocker: anti-bot flow requires dedicated browser automation."
        )
