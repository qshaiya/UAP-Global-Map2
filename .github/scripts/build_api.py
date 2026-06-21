#!/usr/bin/env python3
"""
SENTINEL-7 — Build static API files
Regenerates api/sightings.json, api/recent.json, api/by-cat/<cat>.json
from data/sightings.json every time the database changes.
"""
import json
import os
from datetime import datetime, timezone, timedelta

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
DATA_PATH = os.path.join(ROOT, "data", "sightings.json")
API_DIR = os.path.join(ROOT, "api")
BY_CAT_DIR = os.path.join(API_DIR, "by-cat")

os.makedirs(API_DIR, exist_ok=True)
os.makedirs(BY_CAT_DIR, exist_ok=True)

CATS = ["recent", "military", "civilian", "gov", "historic"]
REPO = "https://github.com/qshaiya/UAP-Global-Map2"
DOCS = f"{REPO}#api"

with open(DATA_PATH, "r", encoding="utf-8") as f:
    db = json.load(f)

sightings = db["sightings"]
updated = db.get("updated", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
now = datetime.now(timezone.utc)
cutoff7 = now - timedelta(days=7)


def is_recent(s):
    if s.get("isNew"):
        return True
    added = s.get("addedOn")
    if added:
        try:
            dt = datetime.fromisoformat(added.replace("Z", "+00:00"))
            if not dt.tzinfo:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt > cutoff7
        except ValueError:
            pass
    return False


# ── 1. api/sightings.json — full endpoint ────────────────────────────────────
api_full = {
    "api_version": "1.0",
    "description": "SENTINEL-7 UAP Live Map — complete sightings database",
    "repo": REPO,
    "docs": DOCS,
    "updated": updated,
    "total": len(sightings),
    "categories": {c: sum(1 for s in sightings if s.get("cat") == c) for c in CATS},
    "approximate_locations": sum(1 for s in sightings if s.get("approx")),
    "endpoints": {
        "all":    f"{REPO.replace('github.com','raw.githubusercontent.com')}/main/api/sightings.json",
        "recent": f"{REPO.replace('github.com','raw.githubusercontent.com')}/main/api/recent.json",
        "by_category": {
            c: f"{REPO.replace('github.com','raw.githubusercontent.com')}/main/api/by-cat/{c}.json"
            for c in CATS
        },
        "write": {
            "method": "POST",
            "url": f"https://api.github.com/repos/qshaiya/UAP-Global-Map2/actions/workflows/add-sighting.yml/dispatches",
            "auth": "Bearer <GITHUB_PAT> with Contents+Workflows write scope",
            "docs": DOCS
        }
    },
    "sightings": sightings,
}
path = os.path.join(API_DIR, "sightings.json")
with open(path, "w", encoding="utf-8") as f:
    json.dump(api_full, f, ensure_ascii=False, indent=2)
print(f"Built api/sightings.json ({len(sightings)} entries)")

# ── 2. api/recent.json — last 7 days ─────────────────────────────────────────
recent = [s for s in sightings if is_recent(s)]
api_recent = {
    "api_version": "1.0",
    "description": "SENTINEL-7 — sightings added or confirmed in the last 7 days",
    "updated": updated,
    "total": len(recent),
    "sightings": recent,
}
path = os.path.join(API_DIR, "recent.json")
with open(path, "w", encoding="utf-8") as f:
    json.dump(api_recent, f, ensure_ascii=False, indent=2)
print(f"Built api/recent.json ({len(recent)} entries)")

# ── 3. api/by-cat/<cat>.json — one per category ───────────────────────────────
for cat in CATS:
    subset = [s for s in sightings if s.get("cat") == cat]
    obj = {
        "api_version": "1.0",
        "description": f"SENTINEL-7 — category: {cat}",
        "category": cat,
        "updated": updated,
        "total": len(subset),
        "sightings": subset,
    }
    path = os.path.join(BY_CAT_DIR, f"{cat}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    print(f"Built api/by-cat/{cat}.json ({len(subset)} entries)")

print("API build complete.")
