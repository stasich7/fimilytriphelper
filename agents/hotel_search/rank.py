from __future__ import annotations

from agents.hotel_search.models import HotelResult, SearchRequest


def rank_results(request: SearchRequest, results: list[HotelResult]) -> list[HotelResult]:
    for result in results:
        result.score = calculate_score(request, result)
    return sorted(results, key=lambda item: item.score, reverse=True)


def calculate_score(request: SearchRequest, result: HotelResult) -> float:
    area_match = 1.0 if result.area.strip().lower() in {area.strip().lower() for area in request.areas} else 0.0
    price_fit = _price_fit(request, result)
    amenities_fit = _amenities_fit(request, result)
    family_fit = _family_fit(request, result)
    rating_fit = _rating_fit(result)
    cancellation_fit = 1.0 if result.cancellation_terms.strip() else 0.0
    availability_fit = 1.0 if result.availability_confirmed else 0.0

    return round(
        area_match * 0.25
        + price_fit * 0.20
        + amenities_fit * 0.20
        + family_fit * 0.15
        + rating_fit * 0.10
        + cancellation_fit * 0.05
        + availability_fit * 0.05,
        4,
    )


def _price_fit(request: SearchRequest, result: HotelResult) -> float:
    nightly = result.price.nightly
    if nightly is None:
        return 0.0

    min_amount = request.price.min_amount
    max_amount = request.price.max_amount
    if min_amount is not None and nightly < min_amount:
        return 0.6
    if max_amount is not None and nightly > max_amount:
        return 0.0
    return 1.0


def _amenities_fit(request: SearchRequest, result: HotelResult) -> float:
    required = {item.lower() for item in request.required_amenities}
    if not required:
        return 1.0
    actual = {item.lower() for item in result.amenities}
    matched = len(required & actual)
    return matched / len(required)


def _family_fit(request: SearchRequest, result: HotelResult) -> float:
    score = 0.0
    if request.guests.children > 0 and any("family" in feature for feature in result.features):
        score += 0.5
    if result.room_option.strip():
        score += 0.3
    if result.availability_confirmed:
        score += 0.2
    return min(score, 1.0)


def _rating_fit(result: HotelResult) -> float:
    if result.rating.value is None:
        return 0.0
    return min(result.rating.value / 10.0, 1.0)
