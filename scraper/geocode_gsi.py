#!/usr/bin/env python3
"""
GSI (国土地理院 - Geospatial Information Authority of Japan) Geocoder Module.
Provides high-precision geocoding for Japanese addresses, stations, and landmarks.
Includes local file caching and rate limiting.
"""

import os
import re
import json
import time
import urllib.parse
from typing import Optional, Tuple, Dict
import requests

GSI_API_URL = "https://msearch.gsi.go.jp/address-search/AddressSearch"
CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
CACHE_FILE = os.path.join(CACHE_DIR, "geocode_cache.json")

# In-memory and disk cache
_cache: Dict[str, Tuple[float, float]] = {}


def _load_cache():
    global _cache
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                _cache = json.load(f)
        except Exception as e:
            print(f"[geocode_gsi] Failed to load cache: {e}")
            _cache = {}
    else:
        _cache = {}


def _save_cache():
    os.makedirs(CACHE_DIR, exist_ok=True)
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(_cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[geocode_gsi] Failed to save cache: {e}")


# Initialize cache upon import
_load_cache()

PREFECTURES = [
    "北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県",
    "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
    "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県",
    "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県",
    "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県",
    "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県",
    "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県"
]


def extract_prefecture(text: str) -> str:
    """Extract prefecture name (e.g. 東京都, 北海道, 兵庫県) from address text."""
    for pref in PREFECTURES:
        if pref in text:
            # Strip trailing 都/道/府/県 for standard display if desired, or keep full
            return pref
    return "Japan"


def clean_query(q: str) -> str:
    """Strip extraneous text like notes in parentheses or floor indicators."""
    q = re.sub(r'\(.*?\)|（.*?）', '', q)
    q = re.sub(r'\s+', ' ', q).strip()
    return q


def geocode_address(query: str, fallback_query: str = "") -> Optional[Tuple[float, float]]:
    """
    Geocode an address or landmark name using GSI Geocoding API.
    Returns (longitude, latitude) as floats or None if resolution failed.
    """
    clean_q = clean_query(query)
    if not clean_q and fallback_query:
        clean_q = clean_query(fallback_query)

    if not clean_q:
        return None

    # Check cache
    if clean_q in _cache:
        return _cache[clean_q]

    headers = {
        "User-Agent": "Stampu-Explorer-Scraper/1.0 (Japan Stamp Collector app)"
    }

    def _query_api(q: str) -> Optional[Tuple[float, float]]:
        try:
            params = {"q": q}
            resp = requests.get(GSI_API_URL, params=params, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and len(data) > 0:
                    feature = data[0]
                    coords = feature.get("geometry", {}).get("coordinates")
                    if coords and len(coords) == 2:
                        lng = round(float(coords[0]), 6)
                        lat = round(float(coords[1]), 6)
                        return (lng, lat)
        except Exception as err:
            print(f"[geocode_gsi] Query error for '{q}': {err}")
        return None

    # 1. Try direct clean query
    res = _query_api(clean_q)
    time.sleep(0.15)  # Polite delay

    # 2. If failed and has fallback, try fallback query
    if not res and fallback_query:
        clean_fb = clean_query(fallback_query)
        if clean_fb != clean_q:
            res = _query_api(clean_fb)
            time.sleep(0.15)

    # 3. If failed on detailed address (e.g. 1-2-3), try truncating to town/chome
    if not res and re.search(r'\d+', clean_q):
        truncated = re.sub(r'[\d\-－丁目番地号]+$', '', clean_q)
        if truncated and truncated != clean_q:
            res = _query_api(truncated)
            time.sleep(0.15)

    if res:
        _cache[clean_q] = res
        _save_cache()
        return res

    return None


if __name__ == "__main__":
    import sys
    test_queries = sys.argv[1:] if len(sys.argv) > 1 else [
        "東京都港区高輪3-26-27",
        "JR東京駅",
        "青森県弘前市下白銀町1",
        "兵庫県姫路市本町68"
    ]
    print(f"Testing GSI geocoder with {len(test_queries)} queries...")
    for q in test_queries:
        coords = geocode_address(q)
        print(f"  '{q}' -> {coords}")
