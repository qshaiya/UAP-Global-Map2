# SENTINEL-7 — UAP Live World Map

A continuously-updating interactive map of UAP/UFO sightings, government disclosures, and witness reports from around the world.

## How it works

- **`index.html`** — the interactive canvas-based map (SENTINEL-7 UI). Loads pin data from `data/sightings.json`.
- **`data/sightings.json`** — the live sightings database. Every pin on the map comes from here.
- **`.github/workflows/daily-scan.yml`** — a GitHub Actions workflow that runs once a day, calls the Claude API with web search enabled, finds new UAP sightings/disclosures reported since the last scan, and commits any new pins to `data/sightings.json`.

## Setup (one-time)

1. Push this repo to GitHub (already done if you're reading this on GitHub).
2. Go to **Settings → Secrets and variables → Actions** in this repo.
3. Add a new repository secret named **`ANTHROPIC_API_KEY`** with your Anthropic API key.
   - Get a key at https://console.anthropic.com/settings/keys
4. (Optional) Go to **Settings → Pages** and enable GitHub Pages, source = `main` branch, root folder. Your map will then be live at:
   `https://qshaiya.github.io/uap-live-map/`

## How daily updates work

Every day at 09:00 UTC, the GitHub Action:
1. Asks Claude (with live web search) to find new UAP/UFO sightings, witness reports, or government disclosure documents reported in the last 24-48 hours (Reddit, X/Twitter, news, NUFORC, Pentagon/PURSUE portal, etc.)
2. Claude returns each new sighting as JSON, with latitude/longitude. If only a general area is known (no exact coordinates), Claude provides an **approximate** lat/lng for that area/city/region and marks `"approx": true`.
3. The workflow appends any genuinely new sightings (deduplicated by name) to `data/sightings.json`.
4. The workflow commits and pushes the updated file automatically.
5. The live map (open `index.html` or your GitHub Pages link) automatically picks up the new pins — refresh the page to see them, marked with a **[NEW]** badge for 7 days.

## Manual scan

You can also trigger a scan manually any time:
- Go to the **Actions** tab → **Daily UAP Scan** → **Run workflow**

## Adding pins manually

Open `index.html` in a browser and use the **+** button to add a sighting by hand (latitude, longitude, category, description, source). This is stored in your browser only — for it to appear for everyone, add the same entry to `data/sightings.json` and push.

## Approximate locations

If a sighting only has a general region (e.g. "near Colorado Springs" or "Western US"), the entry includes `"approx": true` in `sightings.json`. On the map, approximate pins are shown with a dashed outline ring to indicate the location is a best estimate, not exact coordinates.
