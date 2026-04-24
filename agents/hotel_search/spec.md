# Hotel Search Agent Spec

## Scope

Agent runs outside FamilyTripHelper backend/frontend.

Responsibilities:
- accept structured hotel search request;
- plan parallel jobs by `area x aggregator`;
- collect adapter results;
- normalize fields;
- classify stay type;
- deduplicate hotels across aggregators;
- rank candidates with soft area, transport, sleeping-place, budget, and risk signals;
- export JSON for model consumption;
- export markdown `stay` blocks for FamilyTripHelper import.
- drop over-budget results before ranking when the request sets `price.max`.

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
  - `children: int | {age: int, needs_own_bed: bool}[]`
  - `rooms: int`
  - `preferred_beds: int`
- `price`
  - `min: number`
  - `max: number`
  - `currency: string`
- `required_amenities: string[]`
- `aggregators: string[]`
- `max_results_per_area: int`
- `transport_preferences`
  - `prefer_public_transport: bool`
  - `avoid_taxi_dependency: bool`
  - `metro_nearby_bonus: bool`
  - `max_walk_to_metro_minutes: int`
- `accommodation_mix: string[]`
- `area_profiles`
  - `name: string`
  - `anchors: string[]`
  - `nearby_landmarks: string[]`
  - `transport_anchors: string[]`
  - `positive_terms: string[]`
  - `negative_terms: string[]`
  - `accommodation_mix: string[]`

## Parallelism model

Job formula:
- one job per `area x aggregator`

Each job receives:
- same date range;
- same guest composition;
- one area;
- one aggregator;
- same amenity filters;
- same hard nightly budget ceiling for the full guest composition when `price.max` is set.

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
- inferred category and sleeping-place details when available.

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

Budget handling:
- `price.max` is a hard nightly cap for the whole requested guest composition after currency normalization;
- results above `price.max` are excluded before ranking;
- results without a nightly price are excluded when any budget bound is set.

Current default weights:
- soft area fit: `0.20`
- exact availability: `0.15`
- sleeping-place fit: `0.20`
- price fit: `0.15`
- public transport fit: `0.10`
- amenities fit: `0.08`
- rating fit: `0.07`
- cancellation info: `0.03`
- accommodation category fit: `0.02`

Area fit is intentionally soft:
- exact polygon boundaries are not required;
- profile anchors such as `right bank`, `near metro`, `old square`, or `botanical garden` are treated as positive signals;
- negative terms such as `very noisy`, `taxi`, or `car required` reduce fit.

Sleeping-place fit uses `preferred_beds` first. If it is not set, each adult and each child with `needs_own_bed=true` counts as one required sleeping place.

## Grouped shortlist

JSON output includes `best_by_area_and_type`:
- one bucket per area profile;
- one list per category from `accommodation_mix`, usually `hotel`, `aparthotel`, `private`;
- each list is sorted by final score.

## Markdown export rules

Each hotel exports as `stay` item:
- stable key format: `stay.<city-or-area>.<slug>`
- title = hotel name
- metadata lines include area, aggregator, dates, guests, price, availability, amenities
- metadata lines include category, sleeping places, fit scores, and risk flags when available
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
