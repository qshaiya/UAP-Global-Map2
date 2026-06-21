#!/usr/bin/env python3
"""
SENTINEL-7 — Merge Legacy UAP Reports
Fetches uap_reports.json from the old UAP-Global-Map repo and merges any
entries that have valid coordinates into data/sightings.json, deduplicating
by name. Runs as part of the GitHub Actions workflow.

Old schema (uap_reports.json):
  {
    "id": "...",
    "title": "...",
    "event_date": "2024-01-01",
    "location_name": "Phoenix, Arizona",
    "latitude": 33.448,       # or "lat"
    "longitude": -112.074,    # or "lng"
    "confidence": "high",
    "source_type": "government",   # or "source_category" / "type"
    "summary": "...",              # or "notes"
    "source_url": "https://..."
  }
"""
import json
import os
import re
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone

ROOT      = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
DATA_PATH = os.path.join(ROOT, "data", "sightings.json")

OLD_REPO_RAW = (
    "https://raw.githubusercontent.com/qshaiya/UAP-Global-Map/main/data/uap_reports.json"
)


# ── Schema helpers ────────────────────────────────────────────────────────────

def get_lat(r):
    for k in ("latitude", "lat", "Latitude"):
        if r.get(k) is not None:
            return r[k]
    coords = r.get("coordinates", {})
    return coords.get("lat") if isinstance(coords, dict) else None


def get_lng(r):
    for k in ("longitude", "lng", "lon", "Longitude"):
        if r.get(k) is not None:
            return r[k]
    coords = r.get("coordinates", {})
    return coords.get("lng") or coords.get("lon") if isinstance(coords, dict) else None


def parse_coord(v):
    if v is None or v == "":
        return None
    try:
        n = float(v)
        return n if -180 <= n <= 360 else None   # loose check, tighten per axis later
    except (ValueError, TypeError):
        return None


def map_confidence_to_cat(r):
    """Convert old confidence / source_type fields to our category system."""
    src = str(r.get("source_type") or r.get("source_category") or r.get("type") or "").lower()
    conf = str(r.get("confidence") or "").lower()

    if "government" in src or "official" in src:
        return "gov"
    if "military" in src or "military" in str(r.get("title", "")).lower():
        return "military"
    if "reddit" in src:
        return "civilian"
    if "historic" in conf or "historical" in src:
        return "historic"
    # date-based: if event is before 2020, treat as historic
    date_str = str(r.get("event_date") or r.get("date") or "")
    if date_str and date_str[:4].isdigit() and int(date_str[:4]) < 2000:
        return "historic"
    if date_str and date_str[:4].isdigit() and int(date_str[:4]) >= 2024:
        return "recent"
    return "civilian"


def make_desc(r):
    raw = r.get("summary") or r.get("notes") or r.get("description") or ""
    raw = str(raw).strip()
    # Truncate to 200 chars
    return raw[:200] if raw else "No description."


def make_source(r):
    parts = []
    src_type = r.get("source_type") or r.get("source_category") or r.get("type")
    if src_type:
        parts.append(str(src_type).title())
    conf = r.get("confidence")
    if conf:
        parts.append(f"confidence: {conf}")
    url = r.get("source_url") or r.get("url") or ""
    if url and len(url) < 80:
        parts.append(url)
    return " | ".join(parts) if parts else "UAP-Global-Map legacy data"


def safe_name(r):
    return (
        r.get("location_name")
        or r.get("location")
        or r.get("title")
        or r.get("id")
        or "Unknown Location"
    )


def safe_date(r):
    d = r.get("event_date") or r.get("date") or ""
    return str(d)[:10] if d else ""


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=== SENTINEL-7 Legacy Merge ===")
    print(f"Source : {OLD_REPO_RAW}")
    print(f"Target : {os.path.abspath(DATA_PATH)}")
    print()

    # ── Fetch old repo data ───────────────────────────────────────────────────
    print("Fetching uap_reports.json from old repo...")
    try:
        req = urllib.request.Request(
            OLD_REPO_RAW,
            headers={"User-Agent": "SENTINEL-7-bot/1.0"},
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw_text = resp.read().decode("utf-8")
        old_reports = json.loads(raw_text)
        print(f"Fetched {len(old_reports)} records from old repo.")
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code} fetching old repo — skipping merge.")
        sys.exit(0)
    except Exception as e:
        print(f"Error fetching old repo: {e} — skipping merge.")
        sys.exit(0)

    # ── Load current DB ───────────────────────────────────────────────────────
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        db = json.load(f)

    existing_names = {s["name"].strip().lower() for s in db["sightings"]}
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # ── Merge ─────────────────────────────────────────────────────────────────
    added = skipped_no_coords = skipped_dup = skipped_invalid = 0

    for r in old_reports:
        name = str(safe_name(r)).strip()
        if not name:
            skipped_invalid += 1
            continue

        lat = parse_coord(get_lat(r))
        lng = parse_coord(get_lng(r))

        if lat is None or lng is None:
            skipped_no_coords += 1
            continue
        if not (-90 <= lat <= 90 and -180 <= lng <= 180):
            skipped_invalid += 1
            continue
        if name.lower() in existing_names:
            skipped_dup += 1
            continue

        cat = map_confidence_to_cat(r)
        old_id = str(r.get("id") or "")
        new_id = f"legacy_{re.sub(r'[^a-z0-9]+', '-', name.lower())[:30]}"
        if old_id:
            new_id = f"legacy_{old_id[:40]}"

        entry = {
            "id":      new_id,
            "name":    name,
            "lat":     round(lat, 6),
            "lng":     round(lng, 6),
            "cat":     cat,
            "date":    safe_date(r),
            "desc":    make_desc(r),
            "source":  make_source(r),
            "approx":  False,
            "addedOn": today,
            "isNew":   False,          # legacy data doesn't get the NEW badge
            "legacy":  True,
        }
        db["sightings"].append(entry)
        existing_names.add(name.lower())
        added += 1

    # ── Write back ────────────────────────────────────────────────────────────
    db["count"]   = len(db["sightings"])
    db["updated"] = today

    if added > 0:
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=2)
        print(f"\nMerge complete:")
        print(f"  Added       : {added}")
        print(f"  Skipped (dup)     : {skipped_dup}")
        print(f"  Skipped (no coords): {skipped_no_coords}")
        print(f"  Skipped (invalid) : {skipped_invalid}")
        print(f"  Total in DB : {db['count']}")
    else:
        print(f"\nNo new entries to merge.")
        print(f"  Already in DB : {skipped_dup}")
        print(f"  No coords     : {skipped_no_coords}")
        print(f"  Invalid       : {skipped_invalid}")


if __name__ == "__main__":
    main()
