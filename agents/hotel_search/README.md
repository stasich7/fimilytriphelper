# Hotel Search Agent

External hotel search agent for FamilyTripHelper manual workflow.

Current purpose:
- accept hotel search criteria;
- split work into parallel jobs by `area x aggregator`;
- normalize hotel results into one JSON format;
- export `stay` markdown blocks compatible with FamilyTripHelper import format.

Current state:
- architecture scaffold is implemented;
- request parsing, job planning, normalization, ranking, and markdown export are implemented;
- `booking` adapter has browser-based Selenium/Safari implementation path;
- `ozon_travel` adapter is still blocked by anti-bot and returns explicit adapter error;
- live adapters require Safari WebDriver to be enabled locally.

## Input

Input is JSON file with fields:

```json
{
  "trip_city": "Batumi",
  "areas": ["Old Batumi", "Chakvi"],
  "check_in": "2026-08-13",
  "check_out": "2026-08-21",
  "guests": {
    "adults": 4,
    "children": 2,
    "rooms": 2
  },
  "price": {
    "min": 100,
    "max": 250,
    "currency": "USD"
  },
  "required_amenities": ["wifi", "kitchen", "pool"],
  "aggregators": ["booking", "ozon_travel"],
  "max_results_per_area": 5
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
- `booking` adapter requires `safaridriver --enable` and Safari Remote Automation.
- If browser driver is unavailable, agent records adapter error in JSON output.
