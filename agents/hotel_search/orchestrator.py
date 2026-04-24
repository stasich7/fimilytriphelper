from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from agents.hotel_search.classify import classify_results
from agents.hotel_search.currency import CurrencyConverter
from agents.hotel_search.dedupe import dedupe_results
from agents.hotel_search.export_markdown import group_by_area, render_markdown
from agents.hotel_search.models import AreaProfile, HotelResult, SearchJob, SearchRequest
from agents.hotel_search.normalize import normalize_results
from agents.hotel_search.rank import rank_results
from agents.hotel_search.registry import build_adapter_registry


def run_search(request: SearchRequest) -> tuple[dict[str, Any], str]:
    registry = build_adapter_registry()
    jobs = build_jobs(request)
    raw_results: list[HotelResult] = []
    job_errors: list[dict[str, str]] = []

    with ThreadPoolExecutor(max_workers=calculate_max_workers(jobs)) as executor:
        futures = {
            executor.submit(_run_job, registry, request, job): job
            for job in jobs
        }
        for future in as_completed(futures):
            job = futures[future]
            try:
                raw_results.extend(future.result())
            except Exception as err:  # noqa: BLE001
                job_errors.append(
                    {
                        "area": job.area,
                        "aggregator": job.aggregator,
                        "error": str(err),
                    }
                )

    normalized = normalize_results(request, raw_results)
    converted = CurrencyConverter().convert_results(request, normalized)
    classified = classify_results(request, converted)
    budget_filtered = filter_results_by_budget(request, classified)
    ranked = rank_results(request, budget_filtered)
    deduped = dedupe_results(ranked)
    classified_deduped = classify_results(request, deduped)
    ranked_deduped = rank_results(request, classified_deduped)
    limited = limit_results_per_area(request, ranked_deduped)

    payload = {
        "request": request.to_dict(),
        "job_errors": job_errors,
        "results": [result.to_dict() for result in limited],
        "results_by_area": {
            area: [result.to_dict() for result in area_results]
            for area, area_results in group_by_area(limited).items()
        },
        "best_by_area_and_type": build_best_by_area_and_type(request, ranked_deduped),
    }
    markdown = render_markdown(request, limited)
    return payload, markdown


def build_jobs(request: SearchRequest) -> list[SearchJob]:
    jobs: list[SearchJob] = []
    for aggregator in request.aggregators:
        if aggregator == "booking":
            jobs.append(SearchJob(area=request.trip_city, aggregator=aggregator))
            continue
        for area in request.areas:
            jobs.append(SearchJob(area=area, aggregator=aggregator))
    return jobs


def filter_results_by_budget(request: SearchRequest, results: list[HotelResult]) -> list[HotelResult]:
    min_amount = request.price.min_amount
    max_amount = request.price.max_amount
    if min_amount is None and max_amount is None:
        return results

    filtered: list[HotelResult] = []
    for result in results:
        nightly = result.price.nightly
        if nightly is None:
            continue
        if min_amount is not None and nightly < min_amount:
            continue
        if max_amount is not None and nightly > max_amount:
            continue
        filtered.append(result)
    return filtered


def calculate_max_workers(jobs: list[SearchJob]) -> int:
    if any(job.aggregator == "booking" for job in jobs):
        return 1
    return max(1, len(jobs))


def limit_results_per_area(request: SearchRequest, results: list[HotelResult]) -> list[HotelResult]:
    counts: dict[str, int] = {}
    limited: list[HotelResult] = []
    for result in results:
        current = counts.get(result.area, 0)
        if current >= request.max_results_per_area:
            continue
        counts[result.area] = current + 1
        limited.append(result)
    return limited


def build_best_by_area_and_type(request: SearchRequest, results: list[HotelResult]) -> dict[str, dict[str, list[dict[str, Any]]]]:
    output: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for profile in request.area_profiles:
        categories = profile.accommodation_mix or request.accommodation_mix or ["hotel", "aparthotel", "private"]
        area_bucket: dict[str, list[dict[str, Any]]] = {category: [] for category in categories}
        area_results = [result for result in results if _matches_profile(profile, result)]
        for category in categories:
            category_results = [
                result
                for result in area_results
                if result.category == category
            ]
            area_bucket[category] = [
                result.to_dict()
                for result in category_results[: request.max_results_per_area]
            ]
        output[profile.name] = area_bucket
    return output


def _matches_profile(profile: AreaProfile, result: HotelResult) -> bool:
    text = " ".join(
        [
            result.name,
            result.area,
            result.location_summary,
            result.description,
            " ".join(result.features),
        ]
    ).lower()
    needles = [
        profile.name,
        *profile.anchors,
        *profile.nearby_landmarks,
        *profile.transport_anchors,
    ]
    return any(needle.lower() in text for needle in needles if needle.strip())


def _run_job(registry: dict[str, Any], request: SearchRequest, job: SearchJob) -> list[HotelResult]:
    adapter = registry.get(job.aggregator)
    if adapter is None:
        raise ValueError(f"unsupported aggregator: {job.aggregator}")
    return adapter.search(request, job.area)
