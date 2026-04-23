from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from agents.hotel_search.dedupe import dedupe_results
from agents.hotel_search.export_markdown import group_by_area, render_markdown
from agents.hotel_search.models import HotelResult, SearchJob, SearchRequest
from agents.hotel_search.normalize import normalize_results
from agents.hotel_search.rank import rank_results
from agents.hotel_search.registry import build_adapter_registry


def run_search(request: SearchRequest) -> tuple[dict[str, Any], str]:
    registry = build_adapter_registry()
    jobs = build_jobs(request)
    raw_results: list[HotelResult] = []
    job_errors: list[dict[str, str]] = []

    with ThreadPoolExecutor(max_workers=max(1, len(jobs))) as executor:
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
    ranked = rank_results(request, normalized)
    deduped = dedupe_results(ranked)
    ranked_deduped = rank_results(request, deduped)
    limited = limit_results_per_area(request, ranked_deduped)

    payload = {
        "request": request.to_dict(),
        "job_errors": job_errors,
        "results": [result.to_dict() for result in limited],
        "results_by_area": {
            area: [result.to_dict() for result in area_results]
            for area, area_results in group_by_area(limited).items()
        },
    }
    markdown = render_markdown(request, limited)
    return payload, markdown


def build_jobs(request: SearchRequest) -> list[SearchJob]:
    jobs: list[SearchJob] = []
    for area in request.areas:
        for aggregator in request.aggregators:
            jobs.append(SearchJob(area=area, aggregator=aggregator))
    return jobs


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


def _run_job(registry: dict[str, Any], request: SearchRequest, job: SearchJob) -> list[HotelResult]:
    adapter = registry.get(job.aggregator)
    if adapter is None:
        raise ValueError(f"unsupported aggregator: {job.aggregator}")
    return adapter.search(request, job.area)
