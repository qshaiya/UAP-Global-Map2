#!/usr/bin/env python3
"""
SENTINEL-7 Daily UAP Scan
Uses OpenRouter's openrouter:web_search server tool to find new UAP/UFO
sightings, government disclosures, and witness reports daily.

Usage:
  python3 scan.py                                    # uses DEFAULT_MODEL
  python3 scan.py "meta-llama/llama-3.3-70b-instruct:free"
"""
import json
import os
import re
import sys
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
DATA_PATH = os.path.join(ROOT, "data", "sightings.json")

API_KEY  = os.environ.get("OPENROUTER_API_KEY")
API_URL  = "https://openrouter.ai/api/v1/chat/completions"

# Base free models — :online suffix enables web search for any model via Exa
DEFAULT_MODEL = "deepseek/deepseek-chat-v3.1:free"
MODEL = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("OPENROUTER_MODEL", DEFAULT_MODEL)

# Append :online if web search suffix not already present
# This is the correct, non-deprecated way per OpenRouter docs (2026)
if ":online" not in MODEL and ":free" in MODEL:
    SEARCH_MODEL = MODEL.replace(":free", "") + ":online"
elif ":online" not in MODEL:
    SEARCH_MODEL = MODEL + ":online"
else:
    SEARCH_MODEL = MODEL

SYSTEM_PROMPT = """You are SENTINEL-7, a UAP/UFO intelligence extraction agent.

Search the internet for UAP/UFO sightings, witness reports, or government
disclosure documents reported or published in the last 24-72 hours. Search
Reddit r/UFOs, X/Twitter UAP accounts, NUFORC, MUFON, news wires, and the
Pentagon PURSUE/AARO portal.

Return ONLY a valid JSON array (no markdown, no commentary, no preamble):
[
  {
    "name": "City, Country or Region",
    "lat": 0.0,
    "lng": 0.0,
    "cat": "recent",
    "date": "Month Year",
    "desc": "Factual description under 150 characters",
    "source": "Source name and date",
    "approx": false
  }
]

Rules:
- cat must be one of: recent, military, civilian, gov, historic
- approx: true if coordinates are estimated (only a region/country known),
  false if the sighting has a specific city/location
- Return 3-8 genuinely NEW incidents — do NOT return well-known historic
  cases (Roswell, Nimitz, Area 51, etc.) unless there is brand-new news
- If you find nothing new, return exactly: []
- Every lat/lng must be a real coordinate — never use 0.0 unless the
  location is actually near the equator/prime meridian
"""

USER_PROMPT = (
    "Search for the latest UAP/UFO sightings, witness reports, and government "
    "disclosures from the last 24-72 hours. Include specific locations where known. "
    "Return as a JSON array only."
)


def call_model():
    """Call OpenRouter using the openrouter:web_search server tool."""
    body = {
        "model": SEARCH_MODEL,
        "max_tokens": 1500,
        "tools": [
            {
                "type": "openrouter:web_search",
                "engine": "auto",       # auto = native search if available, else Exa
                "max_results": 8,
            }
        ],
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": USER_PROMPT},
        ],
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        API_URL,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
            "HTTP-Referer": "https://github.com/qshaiya/UAP-Global-Map2",
            "X-Title": "SENTINEL-7 UAP Daily Scan",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")
        print(f"HTTP {e.code}: {body_text[:800]}")
        raise


def extract_json_array(text):
    """Extract a JSON array from model output, handling markdown fences."""
    text = re.sub(r"```json|```", "", text).strip()
    start = text.find("[")
    end   = text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        print(f"No JSON array found in response. Raw text:\n{text[:600]}")
        return []
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}\nRaw snippet: {text[start:start+400]}")
        return []


def main():
    print(f"=== SENTINEL-7 UAP Scan ===")
    print(f"Model     : {MODEL}")
    print(f"Search via: {SEARCH_MODEL}")
    print(f"Data file : {os.path.abspath(DATA_PATH)}")
    print(f"Timestamp : {datetime.now(timezone.utc).isoformat()}")
    print()

    if not API_KEY:
        print("ERROR: No OPENROUTER_API_KEY set — skipping scan.")
        sys.exit(1)

    if not os.path.exists(DATA_PATH):
        print(f"ERROR: Data file not found: {DATA_PATH}")
        sys.exit(1)

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        db = json.load(f)

    existing_names = {s["name"].strip().lower() for s in db["sightings"]}
    print(f"Existing sightings in DB: {len(db['sightings'])}")

    # ── Call the model ────────────────────────────────────────────────────────
    try:
        response = call_model()
    except Exception as e:
        print(f"ERROR: API call failed: {e}")
        sys.exit(1)

    # ── Print usage/cost info if available ────────────────────────────────────
    usage = response.get("usage", {})
    if usage:
        print(f"Tokens used: prompt={usage.get('prompt_tokens','-')} "
              f"completion={usage.get('completion_tokens','-')}")

    # ── Extract text from response ────────────────────────────────────────────
    choices = response.get("choices", [])
    if not choices:
        print(f"ERROR: No choices in response. Full response:\n{json.dumps(response)[:800]}")
        sys.exit(1)

    msg = choices[0].get("message", {})
    full_text = msg.get("content") or ""

    # Tool call results may also contain text
    tool_calls = msg.get("tool_calls", [])
    if tool_calls:
        print(f"Model made {len(tool_calls)} tool call(s) (web search)")

    print(f"Model response ({len(full_text)} chars):\n{full_text[:600]}")
    print()

    if not full_text.strip():
        print("WARNING: Empty response from model.")
        sys.exit(0)

    # ── Parse JSON array from the response ───────────────────────────────────
    new_items = extract_json_array(full_text)

    # Some models return an array of JSON strings instead of an array of objects.
    # e.g. ["{ \"name\": \"...\" }", "{ \"name\": \"...\" }"]
    # Parse each string element into a dict if needed.
    parsed_items = []
    for item in new_items:
        if isinstance(item, dict):
            parsed_items.append(item)
        elif isinstance(item, str):
            try:
                obj = json.loads(item)
                if isinstance(obj, dict):
                    parsed_items.append(obj)
            except json.JSONDecodeError:
                print(f"  SKIP (could not parse string item): {item[:80]}")
    new_items = parsed_items
    print(f"Items returned by model: {len(new_items)}")

    # ── Add genuinely new sightings ───────────────────────────────────────────
    added = 0
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    model_tag = re.sub(r"[^a-z0-9]+", "-", MODEL.lower()).strip("-")[:20]

    VALID_CATS = {"recent", "military", "civilian", "gov", "historic"}

    for item in new_items:
        name = str(item.get("name", "")).strip()
        lat  = item.get("lat")
        lng  = item.get("lng")

        if not name:
            print(f"  SKIP (no name): {item}")
            continue
        if lat is None or lng is None:
            print(f"  SKIP (no coords): {name}")
            continue
        try:
            lat = float(lat); lng = float(lng)
        except (ValueError, TypeError):
            print(f"  SKIP (bad coords): {name} lat={lat} lng={lng}")
            continue
        if not (-90 <= lat <= 90 and -180 <= lng <= 180):
            print(f"  SKIP (out-of-range coords): {name} lat={lat} lng={lng}")
            continue
        if name.strip().lower() in existing_names:
            print(f"  SKIP (duplicate): {name}")
            continue

        cat = item.get("cat", "recent")
        if cat not in VALID_CATS:
            cat = "recent"

        new_id = f"scan_{today}_{model_tag}_{added+1:02d}"
        entry = {
            "id":      new_id,
            "name":    name,
            "lat":     lat,
            "lng":     lng,
            "cat":     cat,
            "date":    item.get("date", today),
            "desc":    str(item.get("desc", ""))[:200],
            "source":  str(item.get("source", "SENTINEL-7 Daily Scan")),
            "approx":  bool(item.get("approx", False)),
            "addedOn": today,
            "isNew":   True,
        }
        db["sightings"].append(entry)
        existing_names.add(name.strip().lower())
        added += 1
        approx_tag = " [APPROX]" if entry["approx"] else ""
        print(f"  + NEW PIN: {name} ({cat}){approx_tag}")

    # ── Age out old "isNew" flags ─────────────────────────────────────────────
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
    for s in db["sightings"]:
        if s.get("isNew") and s.get("addedOn", today) < cutoff:
            s["isNew"] = False

    db["updated"] = today
    db["count"]   = len(db["sightings"])

    # ── Write back only if something changed ──────────────────────────────────
    if added > 0:
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=2)
        print(f"\nAdded {added} new sighting(s). Total: {db['count']}")
    else:
        print(f"\nNo new sightings found. DB unchanged ({db['count']} entries).")


if __name__ == "__main__":
    main()
