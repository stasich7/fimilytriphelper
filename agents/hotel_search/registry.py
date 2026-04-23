from __future__ import annotations

from agents.hotel_search.adapters.base import AggregatorAdapter
from agents.hotel_search.adapters.booking import BookingAdapter
from agents.hotel_search.adapters.ozon_travel import OzonTravelAdapter


def build_adapter_registry() -> dict[str, AggregatorAdapter]:
    adapters: list[AggregatorAdapter] = [
        BookingAdapter(),
        OzonTravelAdapter(),
    ]
    return {adapter.name: adapter for adapter in adapters}
