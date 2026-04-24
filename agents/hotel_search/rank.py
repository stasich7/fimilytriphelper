from __future__ import annotations

from agents.hotel_search.models import HotelResult, SearchRequest


def rank_results(request: SearchRequest, results: list[HotelResult]) -> list[HotelResult]:
    for result in results:
        result.score = calculate_score(request, result)
    return sorted(results, key=lambda item: item.score, reverse=True)


def calculate_score(request: SearchRequest, result: HotelResult) -> float:
    area_fit = _area_fit(request, result)
    price_fit = _price_fit(request, result)
    amenities_fit = _amenities_fit(request, result)
    sleeping_fit = _sleeping_fit(request, result)
    transport_fit = _transport_fit(request, result)
    rating_fit = _rating_fit(result)
    cancellation_fit = 1.0 if result.cancellation_terms.strip() else 0.0
    availability_fit = 1.0 if result.availability_confirmed else 0.0
    category_fit = _category_fit(request, result)

    result.area_fit_score = area_fit
    result.sleeping_fit_score = sleeping_fit
    result.transport_score = transport_fit
    result.category_score = category_fit

    return round(
        area_fit * 0.20
        + availability_fit * 0.15
        + sleeping_fit * 0.20
        + price_fit * 0.15
        + transport_fit * 0.10
        + amenities_fit * 0.08
        + rating_fit * 0.07
        + cancellation_fit * 0.03
        + category_fit * 0.02,
        4,
    )


def _area_fit(request: SearchRequest, result: HotelResult) -> float:
    text = _result_text(result)
    best = 0.0
    for profile in request.area_profiles:
        score = 0.0
        if profile.name.lower() in text:
            score += 0.45
        if result.area.strip().lower() == profile.name.strip().lower():
            score += 0.35

        positive_needles = (
            profile.anchors
            + profile.nearby_landmarks
            + profile.transport_anchors
            + profile.positive_terms
        )
        if positive_needles:
            matched = sum(1 for item in positive_needles if item.lower() in text)
            score += min(matched / max(len(positive_needles), 1), 1.0) * 0.45

        if profile.negative_terms and any(item.lower() in text for item in profile.negative_terms):
            score -= 0.25
        best = max(best, score)

    if not request.area_profiles and result.area.strip().lower() in {area.strip().lower() for area in request.areas}:
        best = 1.0
    return max(0.0, min(best, 1.0))


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


def _sleeping_fit(request: SearchRequest, result: HotelResult) -> float:
    required_beds = request.guests.own_beds_required()
    if result.sleeping_places is None:
        return 0.55 if result.room_option.strip() else 0.0
    if result.sleeping_places >= required_beds:
        return 1.0
    if required_beds <= 0:
        return 1.0
    return max(0.0, result.sleeping_places / required_beds * 0.7)


def _transport_fit(request: SearchRequest, result: HotelResult) -> float:
    preferences = request.transport_preferences
    if not preferences.prefer_public_transport:
        return 1.0

    text = _result_text(result)
    score = 0.45
    public_markers = [
        "metro",
        "subway",
        "underground",
        "station",
        "tram",
        "bus",
        "public transport",
        "walking distance",
    ]
    if any(marker in text for marker in public_markers):
        score += 0.35
    if preferences.metro_nearby_bonus and any(marker in text for marker in ["metro", "subway", "underground"]):
        score += 0.20
    if preferences.avoid_taxi_dependency and any(
        marker in text for marker in ["taxi", "car required", "need a car", "far from public transport"]
    ):
        score -= 0.40
    return max(0.0, min(score, 1.0))


def _category_fit(request: SearchRequest, result: HotelResult) -> float:
    preferred = {item.lower() for item in request.accommodation_mix}
    if not preferred:
        return 1.0
    if result.category.lower() in preferred:
        return 1.0
    return 0.4 if result.category == "unknown" else 0.0


def _rating_fit(result: HotelResult) -> float:
    if result.rating.value is None:
        return 0.0
    return min(result.rating.value / 10.0, 1.0)


def _result_text(result: HotelResult) -> str:
    return " ".join(
        [
            result.name,
            result.area,
            result.location_summary,
            result.room_option,
            result.description,
            " ".join(result.amenities),
            " ".join(result.features),
        ]
    ).lower()
