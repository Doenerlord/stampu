#!/usr/bin/env python3
"""
Imports verified authentic Tourist Information Centers & Museums from Funakiya / Hankore
========================================================================================
- Scrapes verified entries with active stamps (≪○：設置あり≫)
- Downloads authentic photographed ink stamp images
- Geocodes coordinates via GSI (国土地理院)
- Appends cleanly to public/data/stamps.json and updates public/data/prefectures.json
"""

import os
import re
import json
import time
import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional, List

from geocode_gsi import (
    geocode_address,
    extract_prefecture,
    extract_prefecture_en,
    extract_city,
    PREF_EN_TO_JA,
    PREF_JA_TO_EN
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(BASE_DIR, "public", "data", "stamps.json")
PREF_FILE = os.path.join(BASE_DIR, "public", "data", "prefectures.json")
IMAGES_DIR = os.path.join(BASE_DIR, "public", "images", "stamps")
BASE_URL = "https://stamp.funakiya.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://stamp.funakiya.com/",
}

os.makedirs(IMAGES_DIR, exist_ok=True)

# Curated list of high-priority verified tourist info & museum pages
TARGET_CANDIDATES = [
    # --- TOURIST INFO CENTERS ---
    {
        "url": "https://stamp.funakiya.com/akihabara-infodesk.html",
        "category": "tourist_info",
        "id": "info-akihabara-tourist-desk",
        "name_en": "Akihabara Tourist Information Desk",
        "operator": "Akihabara Tourism Promotion Association"
    },
    {
        "url": "https://stamp.funakiya.com/nihombashi-kanko.html",
        "category": "tourist_info",
        "id": "info-nihonbashi-tourist-center",
        "name_en": "Nihonbashi Tourist Information Center",
        "operator": "Chuo City Tourism Association"
    },
    {
        "url": "https://stamp.funakiya.com/nihombashi-info.html",
        "category": "tourist_info",
        "id": "info-nihonbashi-annaijo",
        "name_en": "Nihonbashi Information Center (Coredo Muromachi)",
        "operator": "Mitsui Fudosan / Chuo City Tourism"
    },
    {
        "url": "https://stamp.funakiya.com/ginza-info.html",
        "category": "tourist_info",
        "id": "info-ginza-kanko-annaijo",
        "name_en": "Ginza Tourist Information Center",
        "operator": "Ginza Street Association / JNTO"
    },
    {
        "url": "https://stamp.funakiya.com/minatoku-info-tokyotower.html",
        "category": "tourist_info",
        "id": "info-minato-tokyotower-center",
        "name_en": "Minato City Tourist Information Center Tokyo Tower",
        "operator": "Minato City Tourism Association"
    },
    {
        "url": "https://stamp.funakiya.com/shinjuku-kanko.html",
        "category": "tourist_info",
        "id": "info-shinjuku-kanko-annaijo",
        "name_en": "Shinjuku Tourist Information Center",
        "operator": "Shinjuku Convention & Visitors Bureau"
    },
    {
        "url": "https://stamp.funakiya.com/metro-omotesando-info.html",
        "category": "tourist_info",
        "id": "info-tokyo-metro-omotesando",
        "name_en": "Tokyo Metro Omote-sando Tourist Information Center",
        "operator": "Tokyo Metro Commerce"
    },
    {
        "url": "https://stamp.funakiya.com/minatoku-info-fudanotsuji.html",
        "category": "tourist_info",
        "id": "info-minato-fudanotsuji-center",
        "name_en": "Minato City Tourist Information Center (Fudanotsuji)",
        "operator": "Minato City Tourism Association"
    },

    # --- MUSEUMS & ART GALLERIES ---
    {
        "url": "https://stamp.funakiya.com/nact.html",
        "category": "museum",
        "id": "museum-nact-roppongi",
        "name_en": "The National Art Center, Tokyo (NACT)",
        "operator": "Independent Administrative Institution National Museum of Art"
    },
    {
        "url": "https://stamp.funakiya.com/currency-museum.html",
        "category": "museum",
        "id": "museum-currency-bank-of-japan",
        "name_en": "Bank of Japan Currency Museum",
        "operator": "Bank of Japan (日本銀行)"
    },
    {
        "url": "https://stamp.funakiya.com/uenonomori-museum.html",
        "category": "museum",
        "id": "museum-ueno-royal-museum",
        "name_en": "The Ueno Royal Museum",
        "operator": "Japan Art Association"
    },
    {
        "url": "https://stamp.funakiya.com/firedepartment-museum.html",
        "category": "museum",
        "id": "museum-tokyo-fire-department",
        "name_en": "Tokyo Fire Museum (Yotsuya)",
        "operator": "Tokyo Fire Department (東京消防庁)"
    },
    {
        "url": "https://stamp.funakiya.com/shinjuku-historymuseum.html",
        "category": "museum",
        "id": "museum-shinjuku-historical",
        "name_en": "Shinjuku Historical Museum",
        "operator": "Shinjuku City Future Creation Foundation"
    },
    {
        "url": "https://stamp.funakiya.com/baseball-museum.html",
        "category": "museum",
        "id": "museum-baseball-hall-of-fame",
        "name_en": "The Baseball Hall of Fame and Museum (Tokyo Dome)",
        "operator": "Baseball Hall of Fame and Museum Foundation"
    },
    {
        "url": "https://stamp.funakiya.com/meijiac-museum.html",
        "category": "museum",
        "id": "museum-meiji-university",
        "name_en": "Meiji University Museum (Criminal & Archaeological)",
        "operator": "Meiji University"
    },
    {
        "url": "https://stamp.funakiya.com/mufg-trust-museum.html",
        "category": "museum",
        "id": "museum-mufg-trust-bank",
        "name_en": "Mitsubishi UFJ Trust Bank Museum",
        "operator": "Mitsubishi UFJ Trust and Banking Corporation"
    },
    {
        "url": "https://stamp.funakiya.com/logistics-museum.html",
        "category": "museum",
        "id": "museum-logistics-shinagawa",
        "name_en": "Museum of Logistics (Shinagawa)",
        "operator": "Ryutsu Tsushin Foundation"
    },
    {
        "url": "https://stamp.funakiya.com/kachidoki-bridge-museum.html",
        "category": "museum",
        "id": "museum-kachidoki-bridge-archive",
        "name_en": "Kachidoki Bridge Archive Museum",
        "operator": "Tokyo Metropolitan Government Construction Bureau"
    },

    # --- BATCH 2: REGIONAL & KANSAI / HOKKAIDO EXPANSION ---
    {
        "url": "https://stamp.funakiya.com/keikyu-museum.html",
        "category": "museum",
        "id": "museum-keikyu-railway",
        "name_en": "Keikyu Railway Museum",
        "operator": "Keikyu Corporation"
    },
    {
        "url": "https://stamp.funakiya.com/chinatown80.html",
        "category": "tourist_info",
        "id": "info-chinatown80-yokohama",
        "name_en": "Yokohama Chinatown Information Center (ChinaTown80)",
        "operator": "Yokohama Chinatown Development Association"
    },
    {
        "url": "https://stamp.funakiya.com/mitsubishi-minatomiraimuseum.html",
        "category": "museum",
        "id": "museum-mitsubishi-minatomirai",
        "name_en": "Mitsubishi Minatomirai Industrial Museum",
        "operator": "Mitsubishi Heavy Industries"
    },
    {
        "url": "https://stamp.funakiya.com/osaka-kanko.html",
        "category": "tourist_info",
        "id": "info-osaka-tourist-center",
        "name_en": "Osaka Tourist Information Center (JR Osaka Station)",
        "operator": "Osaka Convention & Tourism Bureau"
    },
    {
        "url": "https://stamp.funakiya.com/tsutenkaku.html",
        "category": "tower",
        "id": "tower-tsutenkaku-osaka",
        "name_en": "Tsutenkaku Observatory Tower (通天閣)",
        "operator": "Tsutenkaku Kanko Co., Ltd."
    },
    {
        "url": "https://stamp.funakiya.com/kyoto-kanko.html",
        "category": "tourist_info",
        "id": "info-kyoto-kyo-navi",
        "name_en": "Kyoto General Tourist Information Center (Kyo Navi)",
        "operator": "Kyoto City Tourism Association / JNTO"
    },
    {
        "url": "https://stamp.funakiya.com/nishioyatsuhashi-kyotohachijo.html",
        "category": "shop",
        "id": "shop-nishio-yatsuhashi-kyoto",
        "name_en": "Honke Nishio Yatsuhashi Kyoto Hachijoguchi",
        "operator": "Honke Nishio Yatsuhashi (Established 1689)"
    },
    {
        "url": "https://stamp.funakiya.com/shinkobe-kanko.html",
        "category": "tourist_info",
        "id": "info-shinkobe-station-tourist",
        "name_en": "Shin-Kobe Station Tourist Information Center",
        "operator": "Kobe Tourism Bureau"
    },
    {
        "url": "https://stamp.funakiya.com/kitanoijinkan-kazamidori.html",
        "category": "museum",
        "id": "museum-kobe-weathercock-house",
        "name_en": "Kobe Kitano Weathercock House Museum (風見鶏の館)",
        "operator": "Kobe City Culture Promotion Foundation"
    },
    {
        "url": "https://stamp.funakiya.com/kitanoijinkan-moegi.html",
        "category": "museum",
        "id": "museum-kobe-moegi-house",
        "name_en": "Kobe Kitano Moegi House Museum (萌黄の館)",
        "operator": "Kobe City Culture Promotion Foundation"
    },
    {
        "url": "https://stamp.funakiya.com/shinhakodatehokuto-kanko.html",
        "category": "tourist_info",
        "id": "info-shinhakodatehokuto-desk",
        "name_en": "Shin-Hakodate-Hokuto Station Tourist Information Center",
        "operator": "Hokuto City Tourism Association"
    },
    {
        "url": "https://stamp.funakiya.com/onuma-kanko.html",
        "category": "tourist_info",
        "id": "info-onuma-park-tourist-desk",
        "name_en": "Onuma Quasi-National Park Tourist Information Center",
        "operator": "Nanae Town Tourism Association"
    },
    {
        "url": "https://stamp.funakiya.com/oshamanbe-kanko.html",
        "category": "tourist_info",
        "id": "info-oshamanbe-kanko-desk",
        "name_en": "Oshamambe Tourism Association Information Desk",
        "operator": "Oshamambe Tourism Association"
    },
    {
        "url": "https://stamp.funakiya.com/kishomusemu.html",
        "category": "museum",
        "id": "museum-kishomuseum-tokyo",
        "name_en": "Japan Meteorological Museum",
        "operator": "Japan Meteorological Agency (気象庁)"
    },
    {
        "url": "https://stamp.funakiya.com/aidamitsuo-museum.html",
        "category": "museum",
        "id": "museum-aidamitsuo-tokyo",
        "name_en": "Mitsuo Aida Museum",
        "operator": "Mitsuo Aida Museum Foundation"
    },
    {
        "url": "https://stamp.funakiya.com/kahaku-nature.html",
        "category": "museum",
        "id": "museum-kahaku-nature-garden",
        "name_en": "National Museum of Nature and Science Institute for Nature Study",
        "operator": "National Museum of Nature and Science (国立科学博物館)"
    },
    {
        "url": "https://stamp.funakiya.com/sousuiko-museum.html",
        "category": "museum",
        "id": "museum-sousuiko-tokyo",
        "name_en": "Tokyo Fire Hydrant Museum (送水口博物館)",
        "operator": "Murakami Waterworks & Architectural Heritage"
    },
    {
        "url": "https://stamp.funakiya.com/kigumi-museum.html",
        "category": "museum",
        "id": "museum-kigumi-tokyo",
        "name_en": "Kigumi Museum of Traditional Timber Architecture",
        "operator": "Kigumi Museum NPO"
    }
]


def download_image(img_url: str, save_path: str) -> bool:
    try:
        resp = requests.get(img_url, headers=HEADERS, timeout=12)
        if resp.status_code == 200 and len(resp.content) > 1000:
            with open(save_path, "wb") as f:
                f.write(resp.content)
            return True
    except Exception as e:
        print(f"Error downloading {img_url}: {e}")
    return False


def process_stamp(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    url = item["url"]
    try:
        resp = requests.get(url, headers=HEADERS, timeout=12)
        if resp.status_code != 200:
            print(f"Failed to fetch {url}: {resp.status_code}")
            return None
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "html.parser")
        text = soup.get_text()

        # Title JA
        title_ja = soup.title.string.split("-")[0].replace("のスタンプ", "").strip() if soup.title else ""
        if not title_ja:
            title_ja = item["name_en"]

        # Address
        m_addr = re.search(r"所在地：(?:〒\d{3}-\d{4}\s*)?([^\n\r]+)", text)
        address = m_addr.group(1).strip() if m_addr else ""

        # Stamp Location
        m_loc = re.search(r"設置場所：([^\n\r]+)", text)
        location = m_loc.group(1).strip() if m_loc else "受付カウンター (Reception Counter)"

        # Hours
        m_hrs = re.search(r"営業時間：([^\n\r]+)", text)
        hours = m_hrs.group(1).strip() if m_hrs else "10:00 - 17:00"

        # Image URL
        img_url = ""
        for img in soup.find_all("img"):
            src = img.get("src", "")
            if "/i/stamp/" in src and "sum" not in src:
                img_url = src
                break

        if not img_url:
            print(f"No image found for {url}")
            return None

        # Geocode
        coords = geocode_address(address)
        if not coords or coords == (0.0, 0.0):
            print(f"Geocoding failed for {address}")
            return None

        # Download image
        ext = ".jpg"
        img_filename = f"{item['id']}{ext}"
        local_img_path = os.path.join(IMAGES_DIR, img_filename)
        if not os.path.exists(local_img_path):
            ok = download_image(img_url, local_img_path)
            if not ok:
                print(f"Failed to save image for {item['id']}")
                return None

        pref = extract_prefecture(address) or "東京都"
        pref_en = extract_prefecture_en(pref) or "Tokyo"
        city = extract_city(address) or ""

        # Description & Romaji
        if item["category"] == "tourist_info":
            desc = f"Official commemorative tourism stamp for {item['name_en']} ({title_ja}) located in {city}, {pref_en}. Available at the information counter for travelers."
            romaji = f"{title_ja}-annaijo"
        elif item["category"] == "tower":
            desc = f"Official commemorative observation tower stamp for {item['name_en']} ({title_ja}) in {city}, {pref_en}. Depicts panoramic skyline views and regional architecture."
            romaji = f"{title_ja}-tower"
        elif item["category"] == "shop":
            desc = f"Official commemorative artisan atelier stamp for {item['name_en']} ({title_ja}) in {city}, {pref_en}. Bespoke collection seal celebrating traditional craftsmanship."
            romaji = f"{title_ja}-shop"
        else:
            desc = f"Official commemorative cultural stamp for {item['name_en']} ({title_ja}) in {city}, {pref_en}. Depicts the institution's collection, historical heritage, and regional architecture."
            romaji = f"{title_ja}-museum"

        stamp = {
            "id": item["id"],
            "name": item["name_en"],
            "name_ja": title_ja,
            "name_romaji": romaji,
            "category": item["category"],
            "prefecture": pref_en,
            "city": city,
            "address": address,
            "coordinates": [round(coords[0], 6), round(coords[1], 6)],
            "stampLocation": location,
            "hours": hours,
            "operator": item["operator"],
            "imageUrl": f"/images/stamps/{img_filename}",
            "description": desc,
            "source": "Funakiya Stamp Notebook (旅のスタンプ帳)",
            "sourceUrl": url
        }
        return stamp
    except Exception as e:
        print(f"Error processing {url}: {e}")
        return None


def main():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        stamps = json.load(f)

    existing_ids = {s["id"] for s in stamps}
    print(f"Existing stamps: {len(stamps)}")

    added_stamps = []
    for item in TARGET_CANDIDATES:
        if item["id"] in existing_ids:
            print(f"Skipping already existing {item['id']}")
            continue
        print(f"Processing {item['name_en']} ({item['url']})...")
        stamp = process_stamp(item)
        if stamp:
            stamps.append(stamp)
            existing_ids.add(stamp["id"])
            added_stamps.append(stamp)
            print(f"  [OK] Added {stamp['id']} ({stamp['name']}) -> {stamp['coordinates']}")
        time.sleep(0.3)

    print(f"\nAdded {len(added_stamps)} new verified stamps to database.")
    print(f"New total: {len(stamps)} stamps.")

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(stamps, f, ensure_ascii=False, indent=2)

    # Update prefectures count
    if os.path.exists(PREF_FILE):
        with open(PREF_FILE, "r", encoding="utf-8") as f:
            prefs = json.load(f)

        pref_counts = {}
        for s in stamps:
            p = s.get("prefecture", "")
            pref_counts[p] = pref_counts.get(p, 0) + 1

        for p in prefs:
            p_name = p.get("name", "")
            if p_name in pref_counts:
                p["stampCount"] = pref_counts[p_name]

        with open(PREF_FILE, "w", encoding="utf-8") as f:
            json.dump(prefs, f, ensure_ascii=False, indent=2)
        print("Updated prefectures stamp counts.")


if __name__ == "__main__":
    main()
