#!/usr/bin/env python3
"""
Funakiya's Travel Stamp Book Scraper (旅のスタンプ帳)
Scrapes Eki Stamps (JR Yamanote Line) and Japan 100 Famous Castles (日本100名城).
Integrates with GSI Geocoding API (国土地理院) and saves to public/data/stamps.json.
"""

import os
import re
import sys
import json
import time
from typing import List, Dict, Any, Optional
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

from geocode_gsi import geocode_address, extract_prefecture

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
}

BASE_URL = "https://stamp.funakiya.com"
OUTPUT_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "public", "data", "stamps.json")
)

# Standard metadata for all 30 JR Yamanote Line stations
YAMANOTE_STATION_META = {
    "shinagawa": {"en": "Shinagawa Station", "ja": "JR品川駅", "romaji": "Shinagawa-eki", "ward": "Minato City"},
    "osaki": {"en": "Osaki Station", "ja": "JR大崎駅", "romaji": "Ōsaki-eki", "ward": "Shinagawa City"},
    "gotanda": {"en": "Gotanda Station", "ja": "JR五反田駅", "romaji": "Gotanda-eki", "ward": "Shinagawa City"},
    "meguro": {"en": "Meguro Station", "ja": "JR目黒駅", "romaji": "Meguro-eki", "ward": "Shinagawa City"},
    "ebisu": {"en": "Ebisu Station", "ja": "JR恵比寿駅", "romaji": "Ebisu-eki", "ward": "Shibuya City"},
    "shibuya": {"en": "Shibuya Station", "ja": "JR渋谷駅", "romaji": "Shibuya-eki", "ward": "Shibuya City"},
    "harajuku": {"en": "Harajuku Station", "ja": "JR原宿駅", "romaji": "Harajuku-eki", "ward": "Shibuya City"},
    "yoyogi": {"en": "Yoyogi Station", "ja": "JR代々木駅", "romaji": "Yoyogi-eki", "ward": "Shibuya City"},
    "shinjuku": {"en": "Shinjuku Station", "ja": "JR新宿駅", "romaji": "Shinjuku-eki", "ward": "Shinjuku City"},
    "shinokubo": {"en": "Shin-Okubo Station", "ja": "JR新大久保駅", "romaji": "Shin-Ōkubo-eki", "ward": "Shinjuku City"},
    "takadanobaba": {"en": "Takadanobaba Station", "ja": "JR高田馬場駅", "romaji": "Takadanobaba-eki", "ward": "Shinjuku City"},
    "mejiro": {"en": "Mejiro Station", "ja": "JR目白駅", "romaji": "Mejiro-eki", "ward": "Toshima City"},
    "ikebukuro": {"en": "Ikebukuro Station", "ja": "JR池袋駅", "romaji": "Ikebukuro-eki", "ward": "Toshima City"},
    "otsuka": {"en": "Otsuka Station", "ja": "JR大塚駅", "romaji": "Ōtsuka-eki", "ward": "Toshima City"},
    "sugamo": {"en": "Sugamo Station", "ja": "JR巣鴨駅", "romaji": "Sugamo-eki", "ward": "Toshima City"},
    "komagome": {"en": "Komagome Station", "ja": "JR駒込駅", "romaji": "Komagome-eki", "ward": "Toshima City"},
    "tabata": {"en": "Tabata Station", "ja": "JR田端駅", "romaji": "Tabata-eki", "ward": "Kita City"},
    "nishinippori": {"en": "Nishi-Nippori Station", "ja": "JR西日暮里駅", "romaji": "Nishi-Nippori-eki", "ward": "Arakawa City"},
    "nippori": {"en": "Nippori Station", "ja": "JR日暮里駅", "romaji": "Nippori-eki", "ward": "Arakawa City"},
    "uguisudani": {"en": "Uguisudani Station", "ja": "JR鶯谷駅", "romaji": "Uguisudani-eki", "ward": "Taito City"},
    "ueno": {"en": "Ueno Station", "ja": "JR上野駅", "romaji": "Ueno-eki", "ward": "Taito City"},
    "okachimachi": {"en": "Okachimachi Station", "ja": "JR御徒町駅", "romaji": "Okachimachi-eki", "ward": "Taito City"},
    "akihabara": {"en": "Akihabara Station", "ja": "JR秋葉原駅", "romaji": "Akihabara-eki", "ward": "Chiyoda City"},
    "kanda": {"en": "Kanda Station", "ja": "JR神田駅", "romaji": "Kanda-eki", "ward": "Chiyoda City"},
    "tokyo": {"en": "Tokyo Station", "ja": "JR東京駅", "romaji": "Tōkyō-eki", "ward": "Chiyoda City"},
    "yurakucho": {"en": "Yurakucho Station", "ja": "JR有楽町駅", "romaji": "Yūrakuchō-eki", "ward": "Chiyoda City"},
    "shinbashi": {"en": "Shimbashi Station", "ja": "JR新橋駅", "romaji": "Shinbashi-eki", "ward": "Minato City"},
    "hamamatucho": {"en": "Hamamatsucho Station", "ja": "JR浜松町駅", "romaji": "Hamamatsuchō-eki", "ward": "Minato City"},
    "tamachi": {"en": "Tamachi Station", "ja": "JR田町駅", "romaji": "Tamachi-eki", "ward": "Minato City"},
    "takanawagateway": {"en": "Takanawa Gateway Station", "ja": "JR高輪ゲートウェイ駅", "romaji": "Takanawa Gētowei-eki", "ward": "Minato City"},
}


def clean_html_text(text: str) -> str:
    """Clean HTML fragments and normalize spaces."""
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace('&nbsp;', ' ').replace('&#160;', ' ')
    return re.sub(r'\s+', ' ', text).strip()


def fetch_url(url: str, max_retries: int = 3) -> Optional[str]:
    """Fetch URL with retries and timeout."""
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=12)
            if resp.status_code == 200:
                resp.encoding = 'utf-8'
                return resp.text
        except Exception as e:
            time.sleep(1.0 * (attempt + 1))
    return None


def scrape_yamanote_stations() -> List[Dict[str, Any]]:
    """Scrapes all 30 stations along JR Yamanote Line from Funakiya."""
    print("\n[1/2] Scraping JR Yamanote Line (山手線) Stations...")
    index_url = f"{BASE_URL}/jr-yamanote-line.html"
    html = fetch_url(index_url)
    if not html:
        print(f"Error: Unable to fetch {index_url}")
        return []

    soup = BeautifulSoup(html, "html.parser")
    station_links = []
    for a in soup.find_all("a"):
        href = a.get("href", "")
        text = a.get_text(strip=True)
        if "駅のスタンプ" in text and "jr-" in href:
            if not href.startswith("http"):
                href = f"{BASE_URL}/{href.lstrip('/')}"
            slug_match = re.search(r'jr-([a-zA-Z0-9\-]+)\.html', href)
            slug = slug_match.group(1).lower() if slug_match else ""
            station_links.append((slug, text, href))

    # Remove duplicates preserving order
    seen_slugs = set()
    unique_links = []
    for slug, text, href in station_links:
        if slug and slug not in seen_slugs:
            seen_slugs.add(slug)
            unique_links.append((slug, text, href))

    print(f"Found {len(unique_links)} Yamanote line station entries.")
    results = []

    for slug, text, url in tqdm(unique_links, desc="Yamanote Stations"):
        st_html = fetch_url(url)
        time.sleep(0.2)  # Polite delay

        meta = YAMANOTE_STATION_META.get(slug, {
            "en": f"{slug.capitalize()} Station",
            "ja": text.split("≪")[0].replace("のスタンプ", ""),
            "romaji": f"{slug.capitalize()}-eki",
            "ward": "Tokyo"
        })

        address = ""
        stamp_location = ""
        image_url = ""

        if st_html:
            st_soup = BeautifulSoup(st_html, "html.parser")

            # Extract address: 所在地：〒100-0005 東京都千代田区...
            addr_match = re.search(r'所在地：(?:〒\d{3}-\d{4}\s*)?([^\r\n<]+)', st_html)
            if addr_match:
                address = clean_html_text(addr_match.group(1)).split("設置")[0].strip()

            # Extract stamp location: 設置場所：...
            # Prefer active permanent locations (filter out '現在なし' or temporary ones if possible)
            loc_matches = re.findall(r'設置場所：([^\r\n<]+)', st_html)
            for cand in loc_matches:
                cand_clean = clean_html_text(cand)
                if cand_clean and "現在なし" not in cand_clean:
                    stamp_location = cand_clean
                    break
            if not stamp_location and loc_matches:
                stamp_location = clean_html_text(loc_matches[0])

            # Extract stamp image preview
            for img in st_soup.find_all("img"):
                src = img.get("src", "")
                alt = img.get("alt", "")
                if "/i/stamp/" in src and "スタンプ" in alt:
                    image_url = src if src.startswith("http") else f"{BASE_URL}/{src.lstrip('/')}"
                    break

        if not address:
            address = f"東京都{meta['ward']} ({meta['ja']})"
        if not stamp_location:
            stamp_location = f"{meta['ja']} 改札口・みどりの窓口付近 (Ticket Gate / Information Counter)"

        # Geocode address using GSI API
        coords = geocode_address(address, fallback_query=f"東京都{meta['ward']}{meta['ja']}")
        if not coords:
            # Fallback to known approximate center of Tokyo if geocoding fails
            coords = (139.7671, 35.6812)

        stamp_item = {
            "id": f"eki-yamanote-{slug}",
            "name": meta["en"],
            "name_ja": meta["ja"],
            "name_romaji": meta["romaji"],
            "category": "eki",
            "prefecture": "Tokyo",
            "city": meta["ward"],
            "address": address,
            "coordinates": [coords[0], coords[1]],
            "stampLocation": stamp_location,
            "hours": "07:00 - 21:00 (Station / Ticket office hours)",
            "operator": "JR East (JR東日本 - 山手線)",
            "imageUrl": image_url or "https://images.unsplash.com/photo-1503899036084-c55cdd92da26?auto=format&fit=crop&w=600&q=80",
            "description": f"JR Yamanote Line station stamp for {meta['en']}. Commemorates local neighborhood heritage, architectural landmarks, and historic railway connections."
        }
        results.append(stamp_item)

    print(f"Successfully scraped {len(results)} Yamanote Line stamps.")
    return results


def scrape_100_castles() -> List[Dict[str, Any]]:
    """Scrapes Japan's 100 Famous Castles (日本100名城) from Funakiya and geocodes them."""
    print("\n[2/2] Scraping Japan's 100 Famous Castles (日本100名城)...")
    ja_url = f"{BASE_URL}/japan-100castles.html"
    en_url = f"{BASE_URL}/en/japan-100castles.html"

    ja_html = fetch_url(ja_url)
    en_html = fetch_url(en_url)

    if not ja_html:
        print(f"Error: Unable to fetch {ja_url}")
        return []

    # Map English names by castle number if available
    en_meta = {}
    if en_html:
        for m in re.finditer(r'(.+?)\s*stamp\s*No\.(\d+)\s*(.+)', en_html, re.IGNORECASE):
            try:
                name_en = clean_html_text(m.group(1))
                num = int(m.group(2))
                loc_en = clean_html_text(m.group(3))
                en_meta[num] = {"name_en": name_en, "loc_en": loc_en}
            except Exception:
                continue

    soup_ja = BeautifulSoup(ja_html, "html.parser")
    castles_raw = []

    for li in soup_ja.find_all("li"):
        text = li.get_text(strip=True)
        m = re.search(r'(.+?)のスタンプ\s*No\.(\d+)\s*(.+)', text)
        if m:
            name_ja = m.group(1).strip()
            num = int(m.group(2))
            location_ja = m.group(3).strip()
            a_tag = li.find("a")
            detail_url = a_tag.get("href") if a_tag else None
            if detail_url and not detail_url.startswith("http"):
                detail_url = f"{BASE_URL}/{detail_url.lstrip('/')}"
            castles_raw.append({
                "num": num,
                "name_ja": name_ja,
                "location_ja": location_ja,
                "url": detail_url
            })

    # Deduplicate by castle number
    seen_nums = set()
    unique_castles = []
    for c in castles_raw:
        if c["num"] not in seen_nums:
            seen_nums.add(c["num"])
            unique_castles.append(c)

    # Sort in numerical order No.1 to No.100
    unique_castles.sort(key=lambda x: x["num"])
    print(f"Found {len(unique_castles)} castles in Japan 100 Castles index.")

    results = []

    for c in tqdm(unique_castles, desc="100 Castles"):
        num = c["num"]
        name_ja = c["name_ja"]
        location_ja = c["location_ja"]
        detail_url = c["url"]

        en_info = en_meta.get(num, {})
        name_en = en_info.get("name_en") or (name_ja if "城" not in name_ja else name_ja.replace("城", " Castle"))
        if not name_en.endswith("Castle") and not any(term in name_en for term in ["Site", "Fort", "Goryōkaku", "Goryokaku", "館"]):
            name_en += " Castle"

        prefecture = extract_prefecture(location_ja)
        # Clean municipality from location_ja
        city = location_ja.replace(prefecture, "").strip() if prefecture in location_ja else location_ja

        stamp_location = "城内管理事務所・案内所 / 天守閣受付 (Castle Office / Main Gate)"
        address = location_ja
        image_url = ""
        hours = "09:00 - 17:00 (Castle grounds / Exhibition hours)"

        # Fetch detail page if available
        if detail_url:
            time.sleep(0.15)
            dt_html = fetch_url(detail_url)
            if dt_html:
                dt_soup = BeautifulSoup(dt_html, "html.parser")
                addr_m = re.search(r'所在地：(?:〒\d{3}-\d{4}\s*)?([^\r\n<]+)', dt_html)
                if addr_m:
                    address = clean_html_text(addr_m.group(1)).split("設置")[0].strip()

                loc_m = re.search(r'設置場所：([^\r\n<]+)', dt_html)
                if loc_m:
                    stamp_location = clean_html_text(loc_m.group(1))

                for img in dt_soup.find_all("img"):
                    src = img.get("src", "")
                    alt = img.get("alt", "")
                    if "/i/stamp/" in src and ("名城" in alt or "スタンプ" in alt):
                        image_url = src if src.startswith("http") else f"{BASE_URL}/{src.lstrip('/')}"
                        break

        # Geocode using GSI
        coords = geocode_address(address, fallback_query=f"{location_ja} {name_ja}")
        if not coords:
            coords = geocode_address(f"{name_ja}", fallback_query=location_ja)
        if not coords:
            # Safe national center fallback if remote island
            coords = (138.2529, 36.2048)

        castle_item = {
            "id": f"castle-100-{num:03d}",
            "name": f"{name_en} (No.{num})",
            "name_ja": f"{name_ja} (日本100名城 No.{num})",
            "name_romaji": f"{name_ja}-jō",
            "category": "castle",
            "prefecture": prefecture,
            "city": city or prefecture,
            "address": address,
            "coordinates": [coords[0], coords[1]],
            "stampLocation": stamp_location,
            "hours": hours,
            "operator": f"Japan Castle Association (日本城郭協会 100名城 No.{num})",
            "imageUrl": image_url or "https://images.unsplash.com/photo-1590559899731-a382839e5549?auto=format&fit=crop&w=600&q=80",
            "description": f"Registered historic castle site #{num} in Japan's Top 100 Castles (日本100名城), located in {location_ja}. Official collectible stamp authenticated by the Japan Castle Association."
        }
        results.append(castle_item)

    print(f"Successfully scraped {len(results)} of the 100 Famous Castles.")
    return results


def load_existing_stamps() -> List[Dict[str, Any]]:
    """Loads existing stamps to preserve non-overlapping categories (Michi-no-Eki, Highway, Shrines)."""
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: could not read existing {OUTPUT_FILE}: {e}")
    return []


def main():
    print("=" * 65)
    print(" STAMPU SCRAPER: Funakiya (Yamanote Line + 100 Famous Castles)")
    print("=" * 65)

    # 1. Scrape Yamanote line stations
    yamanote_stamps = scrape_yamanote_stations()

    # 2. Scrape 100 castles
    castle_stamps = scrape_100_castles()

    # 3. Preserve non-overlapping items from existing dataset (e.g. michinoeki, highway, shrines)
    existing = load_existing_stamps()
    preserved = [
        item for item in existing
        if item.get("category") in ["michinoeki", "highway", "temple_shrine"]
    ]

    all_stamps = yamanote_stamps + castle_stamps + preserved

    # Ensure output directory exists
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_stamps, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 65)
    print(f" SCRAPING COMPLETE!")
    print(f" - Yamanote Stations: {len(yamanote_stamps)}")
    print(f" - 100 Famous Castles: {len(castle_stamps)}")
    print(f" - Preserved other stamps: {len(preserved)}")
    print(f" - TOTAL STAMPS: {len(all_stamps)}")
    print(f" Saved directly to: {OUTPUT_FILE}")
    print("=" * 65)


if __name__ == "__main__":
    main()
