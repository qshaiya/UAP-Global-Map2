# SENTINEL-7 — UAP Live World Map

A continuously-updating interactive map of UAP/UFO sightings, government disclosures, and witness reports from around the world.

**Live map:** https://qshaiya.github.io/UAP-Global-Map2/
**Repo:** https://github.com/qshaiya/UAP-Global-Map2

---

## How it works

This repo is the **display layer** of a two-repo pipeline:

```
UAP-Global-Map (curated data, rich schema)
      ↓  weekly merge
UAP-Global-Map2 (live map, daily scan, GitHub Pages)
```

- **`index.html`** — interactive map built on Leaflet.js + CARTO dark tiles. Loads pins from `data/sightings.json` on every page load.
- **`data/sightings.json`** — the live pin database. Grows automatically every day.
- **`api/`** — static JSON API rebuilt after every scan or write (see [API](#api)).
- **`.github/scripts/`** — Python scripts for scanning, merging, geocoding, and building the API.
- **`.github/workflows/`** — GitHub Actions automating everything daily/weekly.

---

## Map legend

**Pin color = category**

| Color | Category |
|---|---|
| 🟢 Cyan | Recent 2024–26 |
| 🔵 Blue | Civilian report |
| 🟠 Orange | Military |
| 🟡 Yellow | Government document |
| 🟣 Purple | Historic |

**Pin shape = confidence**

| Shape | Confidence |
|---|---|
| ● Circle | High |
| ◆ Diamond | Medium-high |
| ■ Square | Medium |
| ▲ Triangle | Low |
| ○ Open circle | Unknown |

Approximate-location pins show a **dashed ring** — coordinates are a best estimate, not exact.

---

## Data sources

### 1. Legacy merge — `merge_legacy.py` (weekly, Sundays)

Fetches `uap_reports.json` from the old [UAP-Global-Map](https://github.com/qshaiya/UAP-Global-Map) repo and merges entries into `sightings.json`, carrying over the full rich schema:

| Old repo field | Used for |
|---|---|
| `latitude` / `longitude` | Pin coordinates |
| `confidence` | Pin shape on map (circle/diamond/square/triangle) |
| `source_url` | Clickable source link in popup |
| `pin_status` | Entries marked `needs_better_coordinates` → `approx:true` pin; `not_pinned_non_earth` → skipped |
| `location_precision` | Shown as note in popup when not `exact` |
| `source_type` | Mapped to category (gov/military/civilian etc.) |
| `summary` | Description shown in popup and sidebar |

**Deduplication** uses `source_url` first (strongest signal), then location name — so the same sighting is never added twice regardless of which pipeline found it first.

**Enrichment** — existing pins already in `sightings.json` get `source_url` and `confidence` filled in from the old repo if they were missing, without creating duplicates.

### 2. Daily AI scan — `scan.py` (daily, 09:00 UTC)

Calls the OpenRouter API with live web search to find new sightings reported in the last 24–72 hours. Runs two passes with different models for broader coverage:

- **Pass 1** — `deepseek/deepseek-chat-v3.1:online`
- **Pass 2** — `meta-llama/llama-3.3-70b-instruct:online`

Plus once a week (Monday 10:00 UTC):
- **Pass 3** — `google/gemini-2.0-flash-exp:online`

Sources searched: Reddit r/UFOs, X/Twitter, NUFORC, MUFON, news wires, Pentagon PURSUE/AARO portal.

New pins get `"isNew": true` and show a **[NEW]** badge on the map for 7 days.

### 3. Geocoding — `geocode_missing.py` (daily, 10:00 UTC)

Finds legacy entries that were skipped due to missing coordinates and looks them up using the [Nominatim](https://nominatim.openstreetmap.org/) geocoding API (OpenStreetMap — completely free, no key needed). Processes 150 entries per run. Country/continent-level results are marked `approx:true`.

### 4. Manual via Write API

See [Write API](#write-api-post) below.

---

## Setup (one-time)

1. **Get a free OpenRouter API key** at https://openrouter.ai/keys
   - The models are free. The web search plugin costs a fraction of a cent per search — add **$1–2 credit**, which lasts ~1 year at the current scan rate.
2. Go to **Settings → Secrets and variables → Actions** in this repo.
3. Add secret **`OPENROUTER_API_KEY`** with your key (paste directly in the browser — never share in chat).
4. *(Optional)* **Settings → Pages** → Deploy from branch `main`, folder `/` → live at `https://qshaiya.github.io/UAP-Global-Map2/`

---

## Workflows

| Workflow | Schedule | What it does |
|---|---|---|
| `daily-scan.yml` | Daily 09:00 UTC + Mon 10:00 UTC | AI web search for new sightings (2 daily passes + 1 weekly Gemini pass) |
| `merge-legacy.yml` | Sunday 11:00 UTC | Fetch old repo data, merge with rich schema into `sightings.json` |
| `geocode-missing.yml` | Daily 10:00 UTC | Look up coordinates for legacy entries using Nominatim |
| `build-api.yml` | On every push to `data/sightings.json` | Rebuild all static API files |
| `add-sighting.yml` | Manual (Write API) | Add a single sighting via GitHub Actions API |

Trigger any workflow manually: **Actions tab → workflow name → Run workflow**.

---

## Switching models

Edit `MODEL` in `.github/scripts/scan.py`. Check https://openrouter.ai/models?max_price=0 for currently available free models. Verify the `:online` suffix works for the model you choose — not all models support web search.

---

## API

The map exposes a static read API (served via GitHub Pages) and a write API (via GitHub Actions `workflow_dispatch`). No extra server or hosting needed.

### Read API (GET)

**Base URL:**
```
https://qshaiya.github.io/UAP-Global-Map2/api/
```
Or via raw GitHub (no Pages caching delay):
```
https://raw.githubusercontent.com/qshaiya/UAP-Global-Map2/main/api/
```

| Endpoint | Description |
|---|---|
| `GET /api/sightings.json` | All sightings + metadata + endpoint index |
| `GET /api/recent.json` | Sightings added in the last 7 days |
| `GET /api/by-cat/recent.json` | Category: Recent 2024–26 |
| `GET /api/by-cat/military.json` | Category: Military |
| `GET /api/by-cat/civilian.json` | Category: Civilian |
| `GET /api/by-cat/gov.json` | Category: Government documents |
| `GET /api/by-cat/historic.json` | Category: Historic |

**Example entry** (enriched with legacy schema fields):
```json
{
  "id": "legacy_uap-2024-001",
  "name": "Rendlesham Forest, UK",
  "lat": 52.09,
  "lng": 1.449,
  "cat": "military",
  "date": "1980-12-26",
  "desc": "USAF personnel encountered landed craft. Lt Col Halt recorded audio on-site.",
  "source": "Official Disclosure | confidence: high",
  "source_url": "https://example.com/rendlesham",
  "confidence": "high",
  "pin_status": "pinned",
  "location_precision": "exact",
  "approx": false,
  "legacy": true
}
```

**Quick test:**
```bash
curl https://raw.githubusercontent.com/qshaiya/UAP-Global-Map2/main/api/recent.json | python3 -m json.tool
```

---

### Write API (POST)

Add a new sighting by triggering the `add-sighting.yml` workflow. Requires a GitHub PAT with **Contents: read+write** and **Actions: write** permissions.

**Endpoint:**
```
POST https://api.github.com/repos/qshaiya/UAP-Global-Map2/actions/workflows/add-sighting.yml/dispatches
```

**Body:**
```json
{
  "ref": "main",
  "inputs": {
    "name":   "Tokyo, Japan",
    "lat":    "35.689",
    "lng":    "139.692",
    "cat":    "civilian",
    "date":   "June 2026",
    "desc":   "Bright spherical object over Tokyo Bay for 4 minutes",
    "source": "Japanese UFO Research Institute 2026",
    "approx": "false"
  }
}
```

| Field | Required | Description |
|---|---|---|
| `name` | ✅ | Location name |
| `lat` | ✅ | Latitude (-90 to 90) |
| `lng` | ✅ | Longitude (-180 to 180) |
| `cat` | ✅ | `recent` `military` `civilian` `gov` `historic` |
| `date` | — | e.g. `"June 2026"` |
| `desc` | ✅ | Description, max 200 chars |
| `source` | — | Source attribution |
| `approx` | — | `"true"` if coordinates are approximate |

Returns HTTP **204** on success. Pin appears on the live map on next page load. Deduplication prevents adding the same location name twice.

**curl example:**
```bash
curl -X POST \
  -H "Authorization: Bearer github_pat_YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"ref":"main","inputs":{"name":"Tokyo, Japan","lat":"35.689","lng":"139.692","cat":"civilian","date":"June 2026","desc":"Bright spherical object over Tokyo Bay","source":"Witness 2026","approx":"false"}}' \
  https://api.github.com/repos/qshaiya/UAP-Global-Map2/actions/workflows/add-sighting.yml/dispatches
```

**Python example:**
```python
import urllib.request, json

req = urllib.request.Request(
    "https://api.github.com/repos/qshaiya/UAP-Global-Map2/actions/workflows/add-sighting.yml/dispatches",
    data=json.dumps({"ref":"main","inputs":{"name":"Tokyo, Japan","lat":"35.689","lng":"139.692","cat":"civilian","date":"June 2026","desc":"Bright spherical object","source":"Witness 2026","approx":"false"}}).encode(),
    headers={"Authorization":"Bearer github_pat_YOUR_TOKEN","Content-Type":"application/json"},
    method="POST"
)
with urllib.request.urlopen(req) as r:
    print(r.status)  # 204 = success
```

---

## Local development

```bash
cd ~/UAP-Global-Map2/uap-live-map
python3 -m http.server 8080
# open http://localhost:8080
```

Opening `index.html` directly via `file://` blocks Leaflet tiles due to CORS — always use a local server.
