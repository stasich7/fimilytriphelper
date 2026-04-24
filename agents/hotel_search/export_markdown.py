from __future__ import annotations

from collections import defaultdict

from agents.hotel_search.models import HotelResult, SearchRequest


def render_markdown(request: SearchRequest, results: list[HotelResult]) -> str:
    lines: list[str] = [
        "---",
        f"trip_id: {slugify(request.trip_city)}-hotel-search",
        f"trip_title: {request.trip_city} hotel search",
        "version_id: v1",
        f"title: Hotel search results for {request.trip_city}",
        "---",
        "",
    ]

    for result in results:
        stable_key = build_stable_key(result)
        lines.append(f"## [{stable_key}] {result.name}")
        lines.append("Type: stay")
        lines.append(f"Area: {result.area}")
        lines.append(f"Category: {result.category}")
        lines.append(f"Aggregator: {result.aggregator}")
        lines.append(f"Dates: {result.check_in.isoformat()} to {result.check_out.isoformat()}")
        lines.append(f"Guests: {_format_guests(result)}")
        if result.sleeping_places is not None:
            lines.append(f"Sleeping places: {result.sleeping_places}")
        price_line = _format_price(result)
        if price_line:
            lines.append(f"Price: {price_line}")
        lines.append(f"Availability: {'confirmed' if result.availability_confirmed else 'not confirmed'}")
        lines.append(f"Fit score: {result.score:.2f}")
        lines.append(f"Area fit: {result.area_fit_score:.2f}")
        lines.append(f"Sleeping fit: {result.sleeping_fit_score:.2f}")
        lines.append(f"Transport fit: {result.transport_score:.2f}")
        if result.amenities:
            lines.append(f"Amenities: {', '.join(result.amenities)}")
        if result.risk_flags:
            lines.append(f"Risk flags: {', '.join(result.risk_flags)}")
        lines.append("")

        body_lines = [
            f"Link: [{result.aggregator}]({result.source_url})" if result.source_url else "Link: source pending",
        ]
        image_url = result.primary_image_url()
        if image_url:
            body_lines.append(f"![{result.name}]({image_url})")
        if result.description:
            body_lines.extend(["", result.description])
        if result.features:
            body_lines.extend(["", "Features:", *[f"- {feature}" for feature in result.features]])
        if result.cancellation_terms:
            body_lines.extend(["", f"Cancellation: {result.cancellation_terms}"])

        lines.extend(body_lines)
        lines.extend(["", ""])

    return "\n".join(lines).rstrip() + "\n"


def group_by_area(results: list[HotelResult]) -> dict[str, list[HotelResult]]:
    grouped: dict[str, list[HotelResult]] = defaultdict(list)
    for result in results:
        grouped[result.area].append(result)
    return dict(grouped)


def build_stable_key(result: HotelResult) -> str:
    area_slug = slugify(result.area or result.city)
    hotel_slug = slugify(result.name)
    return f"stay.{area_slug}.{hotel_slug}"


def slugify(value: str) -> str:
    lowered = value.strip().lower()
    output: list[str] = []
    prev_dot = False
    for char in lowered:
        if char.isalnum():
            output.append(char)
            prev_dot = False
            continue
        if not prev_dot:
            output.append(".")
            prev_dot = True
    slug = "".join(output).strip(".")
    return slug or "item"


def _format_guests(result: HotelResult) -> str:
    return (
        f"{result.guests.adults} adults, {result.guests.children} children, "
        f"{result.guests.rooms} rooms, {result.guests.own_beds_required()} own beds required"
    )


def _format_price(result: HotelResult) -> str:
    parts: list[str] = []
    if result.price.nightly is not None:
        parts.append(f"{result.price.nightly:.2f} {result.price.currency} per night")
    if result.price.total is not None:
        parts.append(f"{result.price.total:.2f} {result.price.currency} total")
    if result.price.original_currency:
        original_parts: list[str] = []
        if result.price.original_nightly is not None:
            original_parts.append(f"{result.price.original_nightly:.2f} {result.price.original_currency} per night")
        if result.price.original_total is not None:
            original_parts.append(f"{result.price.original_total:.2f} {result.price.original_currency} total")
        if original_parts:
            parts.append(f"original: {', '.join(original_parts)}")
    return ", ".join(parts)
