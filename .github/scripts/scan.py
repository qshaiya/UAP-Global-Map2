#!/usr/bin/env python3
"""
SENTINEL-7 Daily UAP Scan
Calls the OpenRouter API (free model + web search plugin) to find new UAP/UFO
sightings, witness reports, and government disclosures reported recently.
Appends any genuinely new entries (deduplicated by name) to data/sightings.json.

If a sighting only has a general area (no precise coordinates), the model is
instructed to provide an approximate lat/lng for that area and set "approx": true.
"""
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "sightings.json")
API_KEY = os.environ.get("OPENROUTER_API_KEY")
API_URL = "https://openrouter.ai/api/v1/chat/completions"
# Free-tier OpenRouter model. The "web" plugin (Exa search) used below incurs a
# tiny per-search fee (a few tenths of a cent) even though the base model is
# free — your OpenRouter account needs a small amount of credit for this.
#
# Pass a different model as argv[1] to run a second/third scan pass with a
# different model — each model formulates its own search queries, so a
# second pass often surfaces different sightings even using the same web
# search backend. See daily-scan.yml for how multiple passes are wired up.
DEFAULT_MODEL = "deepseek/deepseek-chat-v3.1:free"
MODEL = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("OPENROUTER_MODEL", DEFAULT_MODEL)

SYSTEM_PROMPT = """You are SENTINEL-7, a UAP/UFO intelligence extraction agent.

Search the internet (Reddit r/UFOs, X/Twitter, NUFORC, MUFON, news wires, the Pentagon PURSUE/war.gov/ufo portal, AARO releases, and similar sources) for UAP/UFO sightings, witness reports, or government disclosure documents that were reported or published in roughly the last 24-72 hours.

Return ONLY a valid JSON array, no markdown, no commentary:
[
  {
    "name": "Location or Region, Country",
    "lat": 0.0,
    "lng": 0.0,
    "cat": "recent",
    "date": "Month Year or specific date",
    "desc": "Factual description under 150 characters",
    "source": "Source name and date",
    "approx": false
  }
]

Rules:
- Categories allowed: recent, military, civilian, gov, historic
- If the report gives an exact location, use precise coordinates and set "approx": false.
- If the report only gives a general area (a city, region, country, "near X base", "over the Pacific", etc.) with no exact coordinates, pick a reasonable representative lat/lng for that area (e.g. the city center, or a point within the named region/ocean) and set "approx": true.
- Only include incidents that are NEWLY reported (do not return well-known historic cases like Roswell, Area 51, etc. unless there is a genuinely new development about them).
- Return between 0 and 6 items. If you find nothing new, return an empty array [].
- Every item must have real, plausible coordinates (no 0,0 placeholders unless the location truly is at the equator/prime meridian).
"""

USER_PROMPT = "Search for the latest UAP/UFO sightings, witness reports, and government disclosures from the last 24-72 hours. Return as a JSON array per the schema."


def call_model():
    body = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT},
        ],
        "plugins": [{"id": "web", "max_results": 5}],
        "max_tokens": 1500,
    }
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
            "HTTP-Referer": "https://github.com/qshaiya/UAP-Global-Map2",
            "X-Title": "SENTINEL-7 UAP Daily Scan",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def extract_json_array(text):
    text = re.sub(r"```json|```", "", text).strip()
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        return []
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return []


def main():
    if not API_KEY:
        print("No OPENROUTER_API_KEY set — skipping scan.")
        sys.exit(0)

    print(f"Running scan with model: {MODEL}")

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        db = json.load(f)

    existing_names = {s["name"].strip().lower() for s in db["sightings"]}

    try:
        data = call_model()
    except Exception as e:
        print(f"API call failed: {e}")
        sys.exit(0)

    try:
        full_text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        print(f"Unexpected response shape: {json.dumps(data)[:500]}")
        sys.exit(0)

    new_items = extract_json_array(full_text)

    added = 0
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    model_tag = re.sub(r"[^a-z0-9]+", "-", MODEL.lower()).strip("-")[:20]
    for item in new_items:
        name = str(item.get("name", "")).strip()
        lat = item.get("lat")
        lng = item.get("lng")
        if not name or lat is None or lng is None:
            continue
        if name.strip().lower() in existing_names:
            continue
        new_id = "scan_" + datetime.now(timezone.utc).strftime("%Y%m%d") + f"_{model_tag}_{added+1:02d}"
        db["sightings"].append({
            "id": new_id,
            "name": name,
            "lat": float(lat),
            "lng": float(lng),
            "cat": item.get("cat", "recent"),
            "date": item.get("date", today),
            "desc": item.get("desc", ""),
            "source": item.get("source", "SENTINEL-7 Daily Scan"),
            "approx": bool(item.get("approx", False)),
            "addedOn": today,
            "isNew": True,
        })
        existing_names.add(name.strip().lower())
        added += 1
        print(f"NEW PIN: {name} ({item.get('cat')}) {'[APPROX]' if item.get('approx') else ''}")

    # Clear "isNew" flag from entries older than 7 days
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
    for s in db["sightings"]:
        if s.get("isNew") and s.get("addedOn", today) < cutoff:
            s["isNew"] = False

    db["updated"] = today
    db["count"] = len(db["sightings"])

    if added > 0:
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=2)
        print(f"Added {added} new sighting(s). Total: {db['count']}")
    else:
        print("No new sightings found.")


if __name__ == "__main__":
    main()
