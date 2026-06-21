#!/usr/bin/env python3
"""
SENTINEL-7 — Add a single sighting via the Write API
Called by the add-sighting.yml workflow_dispatch action.
Reads inputs from environment variables (set by the workflow),
appends the new sighting to data/sightings.json if it's not a duplicate.
"""
import json
import os
import re
import sys
from datetime import datetime, timezone

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
DATA_PATH = os.path.join(ROOT, "data", "sightings.json")
VALID_CATS = {"recent", "military", "civilian", "gov", "historic"}


def env(key, default=""):
    return os.environ.get(key, default).strip()


name   = env("INPUT_NAME")
lat_s  = env("INPUT_LAT")
lng_s  = env("INPUT_LNG")
cat    = env("INPUT_CAT", "recent").lower()
date   = env("INPUT_DATE")
desc   = env("INPUT_DESC")
source = env("INPUT_SOURCE", "Manual via API")
approx = env("INPUT_APPROX", "false").lower() == "true"

# ── Validate ──────────────────────────────────────────────────────────────────
errors = []
if not name:
    errors.append("name is required")
if not desc:
    errors.append("desc is required")
try:
    lat = float(lat_s)
    if not (-90 <= lat <= 90):
        raise ValueError
except (ValueError, TypeError):
    errors.append(f"lat must be a number between -90 and 90 (got: {lat_s!r})")
    lat = None
try:
    lng = float(lng_s)
    if not (-180 <= lng <= 180):
        raise ValueError
except (ValueError, TypeError):
    errors.append(f"lng must be a number between -180 and 180 (got: {lng_s!r})")
    lng = None
if cat not in VALID_CATS:
    errors.append(f"cat must be one of {sorted(VALID_CATS)} (got: {cat!r})")

if errors:
    print("Validation failed:")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)

# ── Load DB ───────────────────────────────────────────────────────────────────
with open(DATA_PATH, "r", encoding="utf-8") as f:
    db = json.load(f)

existing_names = {s["name"].strip().lower() for s in db["sightings"]}

if name.strip().lower() in existing_names:
    print(f"Sighting already exists: {name!r} — no change made.")
    sys.exit(0)

# ── Build new entry ───────────────────────────────────────────────────────────
today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
safe_name = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:30]
new_id = f"api_{today}_{safe_name}"

entry = {
    "id":      new_id,
    "name":    name,
    "lat":     lat,
    "lng":     lng,
    "cat":     cat,
    "date":    date or today,
    "desc":    desc[:200],
    "source":  source,
    "approx":  approx,
    "addedOn": today,
    "isNew":   True,
}

db["sightings"].append(entry)
db["count"]   = len(db["sightings"])
db["updated"] = today

with open(DATA_PATH, "w", encoding="utf-8") as f:
    json.dump(db, f, ensure_ascii=False, indent=2)

print(f"Added: {name} ({cat}) lat={lat} lng={lng} approx={approx}")
print(f"Total sightings: {db['count']}")
