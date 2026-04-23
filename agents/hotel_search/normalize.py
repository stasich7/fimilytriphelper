from __future__ import annotations

from agents.hotel_search.browser.extract import clean_text, normalize_token
from agents.hotel_search.models import HotelResult, SearchRequest


def normalize_results(request: SearchRequest, results: list[HotelResult]) -> list[HotelResult]:
    normalized: list[HotelResult] = []
    for result in results:
        result.name = clean_text(result.name)
        result.area = clean_text(result.area)
        result.city = clean_text(result.city) or request.trip_city
        result.location_summary = clean_text(result.location_summary)
        result.description = clean_text(result.description)
        result.amenities = _normalize_values(result.amenities)
        result.features = _normalize_values(result.features)
        result.images = [image for image in result.images if clean_text(image.url)]
        if not result.price.currency:
            result.price.currency = request.price.currency
        if not result.dedupe_key:
            result.dedupe_key = build_dedupe_key(result.name, result.area, result.city)
        normalized.append(result)
    return normalized


def build_dedupe_key(name: str, area: str, city: str) -> str:
    return "|".join(
        [
            normalize_token(city),
            normalize_token(area),
            normalize_token(name),
        ]
    )


def _normalize_values(values: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = clean_text(value)
        if not cleaned:
            continue
        lowered = cleaned.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        deduped.append(lowered)
    return deduped
