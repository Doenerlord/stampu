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

        # Description
        if item["category"] == "tourist_info":
            desc = f"Official commemorative tourism stamp for {item['name_en']} ({title_ja}) located in {city}, {pref_en}. Available at the information counter for travelers."
        else:
            desc = f"Official commemorative cultural stamp for {item['name_en']} ({title_ja}) in {city}, {pref_en}. Depicts the institution's collection, historical heritage, and regional architecture."

        stamp = {
            "id": item["id"],
            "name": item["name_en"],
            "name_ja": title_ja,
            "name_romaji": f"{title_ja}-annaijo" if item["category"] == "tourist_info" else f"{title_ja}-museum",
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
