# Hotel Search Agent Spec

## Scope

Agent runs outside FamilyTripHelper backend/frontend.

Responsibilities:
- accept structured hotel search request;
- plan parallel jobs by `area x aggregator`;
- collect adapter results;
- normalize fields;
- deduplicate hotels across aggregators;
- rank candidates;
- export JSON for model consumption;
- export markdown `stay` blocks for FamilyTripHelper import.

Non-goals for current iteration:
- direct FamilyTripHelper API calls;
- DB writes;
- official aggregator API integration.

## Input schema

Top-level fields:
- `trip_city: string`
- `areas: string[]`
- `check_in: YYYY-MM-DD`
- `check_out: YYYY-MM-DD`
- `guests`
  - `adults: int`
  - `children: int`
  - `rooms: int`
- `price`
  - `min: number`
  - `max: number`
  - `currency: string`
- `required_amenities: string[]`
- `aggregators: string[]`
- `max_results_per_area: int`

## Parallelism model

Job formula:
- one job per `area x aggregator`

Each job receives:
- same date range;
- same guest composition;
- one area;
- one aggregator;
- same amenity and budget filters.

## Adapter contract

Each adapter must implement:
- `search(request, area) -> list[HotelResult]`

Adapter returns normalized-enough hotel candidates with:
- source aggregator;
- source URL;
- exact requested dates;
- guest composition;
- availability flag;
- pricing;
- amenities;
- features;
- first image URL when available.

If adapter cannot run:
- raise explicit adapter error;
- orchestrator records error in `job_errors`.

## Normalization rules

- amenity values are lowercased and deduplicated;
- feature values are trimmed and deduplicated;
- empty image URLs are dropped;
- currency defaults to request currency when adapter omits it;
- `availability_confirmed` must reflect exact requested dates, not generic availability wording.

## Deduplication rules

Primary key heuristic:
- normalized hotel name
- normalized area
- normalized city

If two results share same dedupe key:
- keep better-ranked item as primary;
- append alternate source metadata into `alternate_sources`.

## Ranking

Current default weights:
- area match: `0.30`
- price fit: `0.20`
- amenities fit: `0.20`
- family fit: `0.15`
- rating fit: `0.10`
- cancellation fit: `0.05`

## Markdown export rules

Each hotel exports as `stay` item:
- stable key format: `stay.<city-or-area>.<slug>`
- title = hotel name
- metadata lines include area, aggregator, dates, guests, price, availability, amenities
- body contains:
  - source link
  - primary image
  - short summary
  - features
  - cancellation terms if available

Output must stay compatible with FamilyTripHelper markdown parser:
- item heading: `## [stable_key] Title`
- metadata as `Key: Value`
- non-empty body markdown required
