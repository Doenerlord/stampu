#!/usr/bin/env python3
"""
Downloads all remote stamp images locally to public/images/stamps/
Updates public/data/stamps.json to point exclusively to local assets.
Generates local SVG placeholder badges for stamps without external photos.
Guarantees 100% offline image availability inside the APK.
Uses concurrent.futures for fast multi-threaded downloads.
"""

import os
import json
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any

STAMPS_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "public", "data", "stamps.json")
)
IMAGES_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "public", "images", "stamps")
)
PLACEHOLDERS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "public", "images", "placeholders")
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)",
    "Referer": "https://stamp.funakiya.com/",
}

# SVG Placeholders for each category
CATEGORY_SVGS = {
    "eki": '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300" width="100%" height="100%">
  <rect width="100%" height="100%" fill="#064e3b"/>
  <circle cx="200" cy="150" r="100" fill="none" stroke="#10b981" stroke-width="8" stroke-dasharray="12 8"/>
  <circle cx="200" cy="150" r="85" fill="#047857" opacity="0.3"/>
  <path d="M160 120 h80 v50 h-80 z M175 145 a8 8 0 1 0 0 -16 8 8 0 0 0 0 16 M225 145 a8 8 0 1 0 0 -16 8 8 0 0 0 0 16 M160 170 l-15 20 M240 170 l15 20" fill="none" stroke="#a7f3d0" stroke-width="6" stroke-linecap="round"/>
  <text x="200" y="80" font-family="sans-serif" font-weight="bold" font-size="22" fill="#6ee7b7" text-anchor="middle" letter-spacing="4">駅スタンプ</text>
  <text x="200" y="240" font-family="sans-serif" font-size="14" fill="#a7f3d0" text-anchor="middle">RAILWAY STATION STAMP</text>
</svg>''',
    "castle": '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300" width="100%" height="100%">
  <rect width="100%" height="100%" fill="#4c0519"/>
  <circle cx="200" cy="150" r="100" fill="none" stroke="#f43f5e" stroke-width="8" stroke-dasharray="10 6"/>
  <circle cx="200" cy="150" r="85" fill="#be123c" opacity="0.3"/>
  <path d="M150 175 h100 v-25 h-15 v-20 h-20 v-15 h-30 v15 h-20 v20 h-15 z" fill="none" stroke="#fecdd3" stroke-width="6" stroke-linejoin="round"/>
  <text x="200" y="80" font-family="sans-serif" font-weight="bold" font-size="22" fill="#fda4af" text-anchor="middle" letter-spacing="4">日本100名城</text>
  <text x="200" y="240" font-family="sans-serif" font-size="14" fill="#fecdd3" text-anchor="middle">JAPAN TOP 100 CASTLES</text>
</svg>''',
    "michinoeki": '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300" width="100%" height="100%">
  <rect width="100%" height="100%" fill="#451a03"/>
  <circle cx="200" cy="150" r="100" fill="none" stroke="#f59e0b" stroke-width="8" stroke-dasharray="8 6"/>
  <circle cx="200" cy="150" r="85" fill="#b45309" opacity="0.3"/>
  <path d="M155 130 l45 -25 l45 25 v50 h-90 z M180 180 v-25 h40 v25" fill="none" stroke="#fde68a" stroke-width="6"/>
  <text x="200" y="80" font-family="sans-serif" font-weight="bold" font-size="22" fill="#fcd34d" text-anchor="middle" letter-spacing="4">道の駅</text>
  <text x="200" y="240" font-family="sans-serif" font-size="14" fill="#fde68a" text-anchor="middle">ROADSIDE STATION</text>
</svg>''',
    "highway": '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300" width="100%" height="100%">
  <rect width="100%" height="100%" fill="#172554"/>
  <circle cx="200" cy="150" r="100" fill="none" stroke="#3b82f6" stroke-width="8" stroke-dasharray="14 6"/>
  <circle cx="200" cy="150" r="85" fill="#1d4ed8" opacity="0.3"/>
  <path d="M160 170 h80 M165 140 h70 l15 25 h-100 z M175 175 a6 6 0 1 0 0 -12 a6 6 0 0 0 0 12 M225 175 a6 6 0 1 0 0 -12 a6 6 0 0 0 0 12" fill="none" stroke="#bfdbfe" stroke-width="5" stroke-linecap="round"/>
  <text x="200" y="80" font-family="sans-serif" font-weight="bold" font-size="20" fill="#93c5fd" text-anchor="middle" letter-spacing="3">ハイウェイSA・PA</text>
  <text x="200" y="240" font-family="sans-serif" font-size="14" fill="#bfdbfe" text-anchor="middle">EXPRESSWAY REST AREA</text>
</svg>''',
    "temple_shrine": '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300" width="100%" height="100%">
  <rect width="100%" height="100%" fill="#3b0764"/>
  <circle cx="200" cy="150" r="100" fill="none" stroke="#a855f7" stroke-width="8" stroke-dasharray="10 8"/>
  <circle cx="200" cy="150" r="85" fill="#7e22ce" opacity="0.3"/>
  <path d="M140 120 h120 M150 135 h100 M170 135 v45 M230 135 v45" fill="none" stroke="#e9d5ff" stroke-width="7" stroke-linecap="round"/>
  <text x="200" y="80" font-family="sans-serif" font-weight="bold" font-size="22" fill="#d8b4fe" text-anchor="middle" letter-spacing="4">神社・寺院</text>
  <text x="200" y="240" font-family="sans-serif" font-size="14" fill="#e9d5ff" text-anchor="middle">TEMPLE &amp; SHRINE</text>
</svg>'''
}


def create_placeholder_files():
    os.makedirs(PLACEHOLDERS_DIR, exist_ok=True)
    for cat, svg_code in CATEGORY_SVGS.items():
        path = os.path.join(PLACEHOLDERS_DIR, f"{cat}.svg")
        with open(path, "w", encoding="utf-8") as f:
            f.write(svg_code)


def download_single_image(args):
    stamp_id, url, dest_path = args
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 1000:
        return (stamp_id, True)

    for attempt in range(2):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=8)
            if resp.status_code == 200 and len(resp.content) > 1000:
                with open(dest_path, "wb") as f:
                    f.write(resp.content)
                return (stamp_id, True)
        except Exception:
            time.sleep(0.5)
    return (stamp_id, False)


def main():
    print("=" * 65)
    print(" STAMPU OFFLINE ASSETS: Fast Parallel Download")
    print("=" * 65)

    os.makedirs(IMAGES_DIR, exist_ok=True)
    create_placeholder_files()

    with open(STAMPS_FILE, "r", encoding="utf-8") as f:
        stamps = json.load(f)

    to_download = []
    for stamp in stamps:
        stamp_id = stamp["id"]
        image_url = stamp.get("imageUrl", "")
        local_filename = f"{stamp_id}.jpg"
        local_filepath = os.path.join(IMAGES_DIR, local_filename)

        if "funakiya" in image_url and not (os.path.exists(local_filepath) and os.path.getsize(local_filepath) > 1000):
            to_download.append((stamp_id, image_url, local_filepath))

    print(f"Tasks: {len(to_download)} images queued for download (concurrent threads: 6)")

    results_map = {}
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(download_single_image, item): item[0] for item in to_download}
        for future in as_completed(futures):
            s_id, ok = future.result()
            results_map[s_id] = ok

    # Now update stamps.json
    for stamp in stamps:
        stamp_id = stamp["id"]
        category = stamp.get("category", "eki")
        local_filename = f"{stamp_id}.jpg"
        local_filepath = os.path.join(IMAGES_DIR, local_filename)

        if os.path.exists(local_filepath) and os.path.getsize(local_filepath) > 1000:
            stamp["imageUrl"] = f"/images/stamps/{local_filename}"
        else:
            stamp["imageUrl"] = f"/images/placeholders/{category}.svg"

    # Save updated stamps.json
    with open(STAMPS_FILE, "w", encoding="utf-8") as f:
        json.dump(stamps, f, ensure_ascii=False, indent=2)

    total_downloaded = sum(1 for f in os.listdir(IMAGES_DIR) if f.endswith('.jpg'))
    print("=" * 65)
    print(f" COMPLETED:")
    print(f" - Local downloaded stamp photos: {total_downloaded}")
    print(f" - Total stamps configured with 100% offline assets: {len(stamps)}")
    print(f" Updated {STAMPS_FILE}")
    print("=" * 65)


if __name__ == "__main__":
    main()
