# Project Specification: Japan Stamp Explorer (Android)

## 1. Overview & Objectives
An offline-capable Android application built with web technologies (Capacitor) providing an interactive map and registry of collectible stamps across Japan:
- **Eki Stamps (駅スタンプ):** Railway & subway stations (JR, Private lines, Metro).
- **Michi-no-Eki (道の駅):** Roadside rest stations.
- **Highway Stamps (ハイウェイスタンプ):** SA / PA expressway rest stops.
- **Castle Stamps (日本100名城 / 続日本100名城):** Registered historic castle sites.
- **Temples & Shrines (御朱印 / 記念スタンプ):** Prominent spiritual locations.

---

## 2. Technical Stack
- **Runtime / Wrapper:** Capacitor 6.x (Android Native Bridge).
- **Frontend Framework:** Vite + Vue 3 (Composition API, `<script setup>`) or React + TypeScript.
- **Styling:** Tailwind CSS + Lucide Icons.
- **Mapping Engine:** MapLibre GL JS (Vector / Raster Tile support) or Leaflet with `leaflet.markercluster`.
- **Base Map Tiles:** CartoDB Voyager / OpenStreetMap (with offline tile-caching layer or local mbtiles option).
- **Client Storage:** Dexie.js (IndexedDB wrapper) for zero-latency offline access and visited-stamp tracking.
- **Data Scraping & ETL:** Python 3.11+ (`requests`, `beautifulsoup4`, `playwright`, `tqdm`) or Node.js (`cheerio`, `axios`).

---

## 3. Data Sources, Selectors & Extraction Plan

### Source A: Funakiya's Travel Stamp Book (Eki, Castles, Highway)
* **Root URL:** `https://stamp.funakiya.com/` (or English index `https://stamp.funakiya.com/en/`)
* **Station Stamps Index:** `https://stamp.funakiya.com/en/railway.html`
* **Roadside Stations:** `https://stamp.funakiya.com/en/michinoeki.html`
* **100 Fine Castles:** `https://stamp.funakiya.com/en/japan-100castles.html`
* **Highway Rest Areas:** `https://stamp.funakiya.com/en/sapa/`

#### Scraping Logic & DOM Selectors:
1. **Line / Region Links:**
   - Container: `div#mainContent`, `div.entry-content`
   - Links pattern: `a[href*="-line.html"]` or `a[href*="/station/"]`
2. **Station & Stamp Detail Pages:**
   - Station Title: `h1.entry-title` or `h2.station-name` (Extract Kanji, Katakana, and Romaji).
   - Stamp Location / Availability text:
     - Target: `table.stamp-info` or definition lists `dl.stamp-detail`
     - Location clue keywords: `設置場所` (Location), `窓口` (Ticket counter), `改札外` (Outside ticket gate), `改札内` (Inside ticket gate), `利用可能時間` (Operating hours).
   - Stamp Image (preview): `img.stamp-image`, extract `src` or `data-src`.

### Source B: Zenkoku Michi-no-Eki (National Roadside Station Registry)
* **Directory URL:** `https://www.michi-no-eki.jp/stations/search`
* **Alternative open listing:** MLIT Road Bureau official records (`https://www.mlit.go.jp/road/Michi-no-Eki/list.html`)
* **Key Fields to extract:**
  - Name: `.station-item__name` (e.g., 道の駅 許田)
  - Address: `.station-item__address` (Japanese prefecture + municipal address)
  - Facilities / Hours: Look for `スタンプ台` (Stamp stand) details under business hours.

### Source C: OpenStreetMap Overpass API (Ground Truth Coordinates for Stations & Shrines)
To avoid manual geocoding for thousands of railway stations, use Overpass QL directly:

```overpassql
[out:json][timeout:90];
area["ISO3166-1"="JP"][admin_level=2]->.japan;
(
  node["railway"="station"](area.japan);
  node["railway"="halt"](area.japan);
  node["amenity"="place_of_worship"]["religion"~"shinto|buddhist"](area.japan);
);
out body;
>;
out skey qt;