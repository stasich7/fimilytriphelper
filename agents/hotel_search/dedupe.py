from __future__ import annotations

from agents.hotel_search.models import AlternateSource, HotelResult


def dedupe_results(results: list[HotelResult]) -> list[HotelResult]:
    grouped: dict[str, HotelResult] = {}
    for result in results:
        existing = grouped.get(result.dedupe_key)
        if existing is None:
            grouped[result.dedupe_key] = result
            continue

        primary, secondary = _pick_primary(existing, result)
        if primary is not existing:
            grouped[result.dedupe_key] = primary

        primary.alternate_sources.append(
            AlternateSource(
                aggregator=secondary.aggregator,
                source_url=secondary.source_url,
                nightly_price=secondary.price.nightly,
                total_price=secondary.price.total,
            )
        )
    return list(grouped.values())


def _pick_primary(left: HotelResult, right: HotelResult) -> tuple[HotelResult, HotelResult]:
    if right.score > left.score:
        return right, left
    if right.availability_confirmed and not left.availability_confirmed:
        return right, left
    return left, right
