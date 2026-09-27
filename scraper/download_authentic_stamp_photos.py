#!/usr/bin/env python3
"""
Downloads authentic photographed ink stamps from Funakiya (旅のスタンプ帳)
for all categories:
1. Castles (日本100名城 & 続日本100名城)
2. Railway Stations (JR, Shinkansen, Tokyo Metro, Toei, Osaka Metro)
3. Michi-no-Eki (全国道の駅)
4. Highway Expressways (SA/PA)

Replaces generic SVG seals with genuine physical ink impression photographs.
"""

import os
import re
import json
import time
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, Optional, List

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STAMPS_FILE = os.path.join(BASE_DIR, "public", "data", "stamps.json")
OUTPUT_DIR = os.path.join(BASE_DIR, "public", "images", "stamps")
BASE_URL = "https://stamp.funakiya.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://stamp.funakiya.com/",
}

# Load castle index mapping
castle_photo_map = {}


def load_castle_photo_maps():
    global castle_photo_map
    for page, series in [("japan-100castles.html", 1), ("japan-100castles-2nd.html", 2)]:
        url = f"{BASE_URL}/{page}"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.status_code == 200:
                resp.encoding = "utf-8"
                soup = BeautifulSoup(resp.text, "html.parser")
                for li in soup.find_all("li"):
                    text = li.get_text(strip=True)
                    m = re.search(r'No\.(\d+)', text)
                    if m:
                        num = int(m.group(1))
                        if "平戸" in text:
                            num = 90
                        stamp_id = f"castle-100-{num:03d}" if series == 1 else f"castle-zoku-{num:03d}"
                        a_tag = li.find("a")
                        detail_url = a_tag.get("href") if a_tag else ""
                        if detail_url and not detail_url.startswith("http"):
                            detail_url = f"{BASE_URL}/{detail_url.lstrip('/')}"
                        
                        img_tag = li.find("img")
                        img_src = img_tag.get("src") if img_tag else ""
                        if img_src and "nocheck" not in img_src:
                            castle_photo_map[stamp_id] = {
                                "detail_url": detail_url,
                                "thumb_url": img_src
                            }
        except Exception as e:
            print(f"Error loading castle map: {e}")


def get_detail_urls_for_stamp(stamp: Dict[str, Any]) -> List[str]:
    s_id = stamp["id"]
    cat = stamp.get("category", "")
    urls = []

    if cat == "castle":
        entry = castle_photo_map.get(s_id)
        if entry:
            if entry.get("detail_url"):
                urls.append(entry["detail_url"])
            if entry.get("thumb_url"):
                urls.append(entry["thumb_url"])
    elif cat == "eki":
        slug = s_id.replace("eki-", "")
        if slug.startswith("yamanote-"):
            clean = slug.replace("yamanote-", "")
            urls.append(f"{BASE_URL}/jr-{clean}.html")
        elif slug.startswith("shinkansen-"):
            clean = slug.replace("shinkansen-", "")
            urls.append(f"{BASE_URL}/jr-{clean}.html")
            urls.append(f"{BASE_URL}/jrt-{clean}.html")
            urls.append(f"{BASE_URL}/jrw-{clean}.html")
        elif slug.startswith("metro-"):
            clean = slug.replace("metro-", "")
            urls.append(f"{BASE_URL}/metro-{clean}.html")
        elif slug.startswith("toei-"):
            clean = slug.replace("toei-", "")
            urls.append(f"{BASE_URL}/toei-{clean}.html")
        elif slug.startswith("om-"):
            clean = slug.replace("om-", "")
            urls.append(f"{BASE_URL}/om-{clean}.html")
        else:
            urls.append(f"{BASE_URL}/jr-{slug}.html")
    elif cat == "michinoeki":
        slug = s_id.replace("michi-", "")
        urls.append(f"{BASE_URL}/miti-{slug}.html")
    elif cat == "highway":
        slug = s_id.replace("hw-", "")
        urls.append(f"{BASE_URL}/hw-{slug}.html")

    return urls


def extract_photo_url_from_html(html: str) -> Optional[str]:
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")
    # 1. Prefer full-size stamp photo
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if "/i/stamp/" in src and not any(x in src for x in ["nocheck", "mitinoeki", "pref_", "list_", "hw.jpg", "icon_"]):
            return src if src.startswith("http") else f"{BASE_URL}/{src.lstrip('/')}"
    # 2. Fallback to thumbnail stamp photo
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if "/i/stampsum/" in src and not any(x in src for x in ["nocheck", "mitinoeki", "pref_", "list_", "hw.jpg", "icon_"]):
            return src if src.startswith("http") else f"{BASE_URL}/{src.lstrip('/')}"
    return None


def download_image(img_url: str, dest_path: str) -> bool:
    try:
        resp = requests.get(img_url, headers=HEADERS, timeout=10)
        if resp.status_code == 200 and len(resp.content) > 3000:
            header = resp.content[:4]
            # JPEG (\xff\xd8\xff) or PNG (\x89PNG)
            if header.startswith(b'\xff\xd8\xff') or header.startswith(b'\x89PNG'):
                with open(dest_path, "wb") as f:
                    f.write(resp.content)
                return True
    except Exception:
        pass
    return False


def process_stamp(stamp: Dict[str, Any]) -> Optional[str]:
    s_id = stamp["id"]
    dest_path = os.path.join(OUTPUT_DIR, f"{s_id}.jpg")

    # If photo already exists and is valid, return
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 3000:
        return f"/images/stamps/{s_id}.jpg"

    urls = get_detail_urls_for_stamp(stamp)
    for u in urls:
        if u.endswith(".jpg") or u.endswith(".png"):
            # Direct image url
            if download_image(u, dest_path):
                return f"/images/stamps/{s_id}.jpg"
        else:
            # HTML page
            try:
                r = requests.get(u, headers=HEADERS, timeout=8)
                if r.status_code == 200:
                    r.encoding = "utf-8"
                    photo_url = extract_photo_url_from_html(r.text)
                    if photo_url:
                        if download_image(photo_url, dest_path):
                            return f"/images/stamps/{s_id}.jpg"
            except Exception:
                continue

    return None


def main():
    print("=" * 70)
    print(" AUTHENTIC STAMP PHOTO SCRAPER & DOWNLOADER")
    print("=" * 70)

    with open(STAMPS_FILE, "r", encoding="utf-8") as f:
        stamps = json.load(f)

    print(f"Loaded {len(stamps)} stamps from {STAMPS_FILE}")
    print("Indexing Castle photographs...")
    load_castle_photo_maps()
    print(f"Indexed {len(castle_photo_map)} castle photos from registry.")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"Searching and downloading authentic photographs (12 worker threads)...")
    success_count = 0
    svg_fallback_count = 0

    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = {executor.submit(process_stamp, s): s for s in stamps}
        for future in as_completed(futures):
            stamp = futures[future]
            res = future.result()
            if res:
                stamp["imageUrl"] = res
                success_count += 1
            else:
                svg_name = f"{stamp['id']}.svg"
                stamp["imageUrl"] = f"/images/stamps/{svg_name}"
                svg_fallback_count += 1

    print("\n" + "=" * 70)
    print(" RESULTS:")
    print(f" - Authentic Photographed Stamps Downloaded: {success_count}")
    print(f" - Fallback Hanko SVGs: {svg_fallback_count}")
    print(f" - Total Stamps: {len(stamps)}")
    print("=" * 70)

    with open(STAMPS_FILE, "w", encoding="utf-8") as f:
        json.dump(stamps, f, ensure_ascii=False, indent=2)

    print(f"Updated {STAMPS_FILE} with authentic stamp photos.")


if __name__ == "__main__":
    main()
