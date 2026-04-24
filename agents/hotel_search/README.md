# Hotel Search Agent

External hotel search agent for FamilyTripHelper manual workflow.

Current purpose:
- accept hotel search criteria;
- split work into parallel jobs by `area x aggregator`;
- normalize hotel results into one JSON format;
- classify stay type as `hotel`, `aparthotel`, or `private`;
- score soft area fit, sleeping-place fit, transport fit, budget, amenities, and risks;
- export `stay` markdown blocks compatible with FamilyTripHelper import format.
- enforce a hard nightly budget ceiling for the whole guest composition when `price.max` is set.

Current state:
- architecture scaffold is implemented;
- request parsing, job planning, normalization, ranking, and markdown export are implemented;
- `booking` adapter has browser-based Selenium implementation path;
- `ozon_travel` adapter is still blocked by anti-bot and returns explicit adapter error;
- live adapters require a local browser WebDriver.

## Input

Input is JSON file with fields:

```json
{
  "trip_city": "Batumi",
  "areas": ["Old Batumi", "Chakvi"],
  "check_in": "2026-08-13",
  "check_out": "2026-08-21",
  "guests": {
    "adults": 3,
    "children": [
      {
        "age": 6,
        "needs_own_bed": true
      }
    ],
    "rooms": 1,
    "preferred_beds": 4
  },
  "price": {
    "min": null,
    "max": 100,
    "currency": "USD"
  },
  "required_amenities": ["wifi", "kitchen", "pool"],
  "aggregators": ["booking"],
  "max_results_per_area": 5,
  "transport_preferences": {
    "prefer_public_transport": true,
    "avoid_taxi_dependency": true,
    "metro_nearby_bonus": true,
    "max_walk_to_metro_minutes": 12
  },
  "accommodation_mix": ["hotel", "aparthotel", "private"],
  "area_profiles": [
    {
      "name": "Old Batumi",
      "anchors": ["Old Boulevard", "Europe Square", "Piazza"],
      "nearby_landmarks": ["Batumi Boulevard", "Alphabet Tower"],
      "transport_anchors": ["bus", "station", "walking distance"],
      "positive_terms": ["central", "walkable", "quiet", "family"],
      "negative_terms": ["nightclub", "very noisy", "taxi"],
      "accommodation_mix": ["hotel", "aparthotel", "private"]
    }
  ]
}
```

See [config.example.json](/Users/user/repos/my/FamilyTripHelper/agents/hotel_search/config.example.json).

## Output

Agent writes:
- normalized JSON result file;
- markdown file with `stay` plan items.

JSON contains:
- request echo;
- job-level adapter errors;
- ranked hotel results;
- per-area grouped results.
- best candidates by soft area profile and stay type.

Markdown contains:
- front matter;
- one `stay` item block per ranked result.

## Run

```bash
python3 -m agents.hotel_search.run \
  --input agents/hotel_search/config.example.json \
  --json-out /tmp/hotel-search-results.json \
  --md-out /tmp/hotel-search-results.md
```

## Notes

- Agent is external to current web app and DB.
- Generated markdown is intended for later import into FamilyTripHelper.
- `price.max` is treated as a hard nightly budget cap for the full requested guest composition, not as a per-room hint.
- `booking` adapter works best through installed Google Chrome; Safari can be used when Safari Remote Automation is enabled.
- If browser driver is unavailable, agent records adapter error in JSON output.
