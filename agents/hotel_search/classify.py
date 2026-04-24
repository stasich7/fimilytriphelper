from __future__ import annotations

import re

from agents.hotel_search.models import HotelResult, SearchRequest


def classify_results(request: SearchRequest, results: list[HotelResult]) -> list[HotelResult]:
    for result in results:
        result.category = classify_category(result)
        result.sleeping_places = infer_sleeping_places(result)
        result.risk_flags = build_risk_flags(request, result)
    return results


def classify_category(result: HotelResult) -> str:
    text = _result_text(result)
    name = result.name.lower()
    if _contains_any(text, ["aparthotel", "apart hotel", "serviced apartment", "residence hotel"]):
        return "aparthotel"
    if _contains_any(name, ["hotel", "resort", "inn"]):
        return "hotel"
    if _matches_any_phrase(
        text,
        [
            "apartment",
            "guest house",
            "guesthouse",
            "holiday home",
            "villa",
            "self catering",
            "homestay",
        ],
    ):
        return "private"
    if _contains_any(text, ["hotel", "resort", "inn"]):
        return "hotel"
    if result.aggregator == "booking" and _contains_any(result.room_option.lower(), ["room", "suite"]):
        return "hotel"
    return "unknown"


def infer_sleeping_places(result: HotelResult) -> int | None:
    text = _bedding_text(result)
    if not text.strip():
        return None

    places = 0
    patterns = [
        (r"([0-9]+)\s*(?:x|×)?\s*sofa(?:\s+beds?)?", 1),
        (r"([0-9]+)\s*(?:x|×)?\s*single(?:\s+beds?)?", 1),
        (r"([0-9]+)\s*(?:x|×)?\s*(?:extra-large|large)?\s*double(?:\s+beds?)?", 2),
    ]
    for pattern, multiplier in patterns:
        for match in re.finditer(pattern, text):
            places += int(match.group(1)) * multiplier

    if "sofa bed" in text and not re.search(r"[0-9]+\s*(?:x|×)?\s*sofa(?:\s+beds?)?", text):
        places += 1
    if "double bed" in text and not re.search(r"[0-9]+\s*(?:x|×)?\s*(?:extra-large|large)?\s*double(?:\s+beds?)?", text):
        places += 2
    if "single bed" in text and not re.search(r"[0-9]+\s*(?:x|×)?\s*single(?:\s+beds?)?", text):
        places += 1

    bedrooms_match = re.search(r"([0-9]+)\s*bedrooms?", text)
    if bedrooms_match and places == 0:
        places = int(bedrooms_match.group(1)) * 2

    return places or None


def build_risk_flags(request: SearchRequest, result: HotelResult) -> list[str]:
    flags: list[str] = []
    if not result.availability_confirmed:
        flags.append("availability_not_confirmed")
    if result.price.nightly is None and result.price.total is None:
        flags.append("no_price")
    if result.rating.value is None:
        flags.append("no_rating")
    if result.rating.count is not None and result.rating.count < 50:
        flags.append("low_review_count")
    if not result.cancellation_terms.strip():
        flags.append("no_cancellation_info")
    if result.sleeping_places is None:
        flags.append("no_sleeping_info")
    elif result.sleeping_places < request.guests.own_beds_required():
        flags.append("not_enough_sleeping_places")
    if request.transport_preferences.avoid_taxi_dependency and _contains_any(
        _result_text(result),
        ["taxi", "car required", "need a car", "far from public transport"],
    ):
        flags.append("taxi_dependency")
    return flags


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


def _contains_any(text: str, needles: list[str]) -> bool:
    return any(needle in text for needle in needles)


def _matches_any_phrase(text: str, needles: list[str]) -> bool:
    return any(re.search(rf"\b{re.escape(needle)}\b", text) for needle in needles)


def _bedding_text(result: HotelResult) -> str:
    room_option = result.room_option.lower()
    if any(marker in room_option for marker in ["bed", "single", "double", "sofa"]):
        return room_option
    return result.description.lower() or room_option
