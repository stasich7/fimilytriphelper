from __future__ import annotations

from abc import ABC, abstractmethod

from agents.hotel_search.models import HotelResult, SearchRequest


class AggregatorAdapter(ABC):
    name: str

    @abstractmethod
    def search(self, request: SearchRequest, area: str) -> list[HotelResult]:
        raise NotImplementedError
