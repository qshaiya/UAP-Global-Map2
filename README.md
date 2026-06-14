# SENTINEL-7 — UAP Live World Map

A continuously-updating interactive map of UAP/UFO sightings, government disclosures, and witness reports from around the world.

Live repo: https://github.com/qshaiya/UAP-Global-Map2

## How it works

- **`index.html`** — the interactive canvas-based map (SENTINEL-7 UI). Loads pin data from `data/sightings.json`.
- **`data/sightings.json`** — the live sightings database. Every pin on the map comes from here.
- **`.github/workflows/daily-scan.yml`** — a GitHub Actions workflow that runs once a day, calls the **OpenRouter API** (free model + web search plugin) to find new UAP sightings/disclosures reported since the last scan, and commits any new pins to `data/sightings.json`.

## Setup (one-time)

1. Get a free OpenRouter API key at **https://openrouter.ai/keys**
   - Sign up (free), create a key.
   - The model used (`deepseek/deepseek-chat-v3.1:free`) is free, but the **web search plugin** (Exa) costs a tiny fee per search (a fraction of a cent). Add **$1-2 of credit** to your OpenRouter account — at one scan/day this lasts a very long time (~$0.30-1/year).
2. In this repo, go to **Settings → Secrets and variables → Actions**.
3. Add a new repository secret named **`OPENROUTER_API_KEY`** with your key.
   - ⚠️ Paste it directly into the GitHub Settings page in your browser — never share API keys in chat.
4. (Optional) Go to **Settings → Pages** and enable GitHub Pages, source = `main` branch, root folder. Your map will then be live at your GitHub Pages URL.

## How daily updates work

Every day at 09:00 UTC, the GitHub Action:
1. Asks the model (with web search) to find new UAP/UFO sightings, witness reports, or government disclosure documents reported in the last 24-72 hours (Reddit, X/Twitter, news, NUFORC, Pentagon/PURSUE portal, etc.)
2. The model returns each new sighting as JSON, with latitude/longitude. If only a general area is known (no exact coordinates), it provides an **approximate** lat/lng for that area/city/region and marks `"approx": true`.
3. The workflow appends any genuinely new sightings (deduplicated by name) to `data/sightings.json`.
4. The workflow commits and pushes the updated file automatically.
5. The live map (open `index.html` or your GitHub Pages link) automatically picks up the new pins on load — new entries are marked with a **[NEW]** badge for 7 days.

## Manual scan

You can also trigger a scan manually any time:
- Go to the **Actions** tab → **Daily UAP Scan** → **Run workflow**

## Adding pins manually

Open `index.html` in a browser and use the **+** button to add a sighting by hand (latitude, longitude, category, description, source). This is stored in your browser only — for it to appear for everyone, add the same entry to `data/sightings.json` and push.

## Approximate locations

If a sighting only has a general region (e.g. "near Colorado Springs" or "Western US"), the entry includes `"approx": true` in `sightings.json`. On the map, approximate pins are shown with a dashed ring around them to indicate the location is a best estimate, not exact coordinates.

## Switching models

If `deepseek/deepseek-chat-v3.1:free` becomes unavailable or rate-limited, edit `MODEL` in `.github/scripts/scan.py`. Other free OpenRouter options include `meta-llama/llama-3.3-70b-instruct:free` or `google/gemini-2.0-flash-exp:free` — check https://openrouter.ai/models?max_price=0 for current free models.
