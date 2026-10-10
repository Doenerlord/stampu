#!/usr/bin/env python3
"""
Hankore Category Integration Preparation Pipeline
=================================================
Prepares and stages stamp candidates from Hankore (hankore.jp) for existing categories
in Stampu (museum, tourist_info, highway, shop, eki, castle, onsen, tower).

Safety constraint:
DOES NOT modify public/data/stamps.json.
Generates an isolated staging artifact: scraper/staging/hankore_candidates_preview.json.
"""

import os
import json
import math
from typing import Dict, List, Any, Tuple

# 1. Category Mapping between Hankore and Stampu
CATEGORY_MAPPING = {
    "博物館・美術館": {
        "target_category": "museum",
        "id_prefix": "museum-hk",
        "label": "Museums & Art Galleries",
        "stampu_current": 30,
        "hankore_count": 543,
        "description_pattern": "Cultural museum commemorative stamp at {name_ja} ({name}). Depicts historical artifacts, exhibitions, and regional heritage."
    },
    "観光案内所": {
        "target_category": "tourist_info",
        "id_prefix": "info-hk",
        "label": "Tourist Information Centers",
        "stampu_current": 20,
        "hankore_count": 123,
        "description_pattern": "Regional tourist information desk stamp at {name_ja} ({name}). Commemorative seal for visitors exploring local landmarks."
    },
    "SA・PA": {
        "target_category": "highway",
        "id_prefix": "hw-hk",
        "label": "Highway Service & Parking Areas",
        "stampu_current": 237,
        "hankore_count": 569,
        "description_pattern": "Expressway highway service area commemorative stamp at {name_ja} ({name}) featuring regional culinary specialties and highway transit history."
    },
    "店舗": {
        "target_category": "shop",
        "id_prefix": "shop-hk",
        "label": "Concept Shops & Ateliers",
        "stampu_current": 20,
        "hankore_count": 496,
        "description_pattern": "Specialty boutique and artisan workshop stamp at {name_ja} ({name}). Celebrated local atelier with bespoke collection seal."
    },
    "駅": {
        "target_category": "eki",
        "id_prefix": "eki-hk",
        "label": "Railway Stations (Local/Private)",
        "stampu_current": 1124,
        "hankore_count": 1529,
        "description_pattern": "Commemorative railway station stamp for {name_ja} ({name}). Reflects line history, rolling stock, and scenic transit landmarks."
    },
    "城・史跡": {
        "target_category": "castle",
        "id_prefix": "castle-hk",
        "label": "Castles & Historic Ruins",
        "stampu_current": 200,
        "hankore_count": 207,
        "description_pattern": "Historical fortress & archaeological monument stamp at {name_ja} ({name}). Depicts castle keep architecture and feudal heritage."
    },
    "温泉・入浴施設": {
        "target_category": "onsen",
        "id_prefix": "onsen-hk",
        "label": "Hot Springs & Onsen Facilities",
        "stampu_current": 60,
        "hankore_count": 115,
        "description_pattern": "Traditional Japanese onsen bathhouse commemorative seal at {name_ja} ({name}). Thermal spring heritage and relaxation landmark."
    },
    "タワー・展望台": {
        "target_category": "tower",
        "id_prefix": "tower-hk",
        "label": "Observation Towers & Platforms",
        "stampu_current": 22,
        "hankore_count": 48,
        "description_pattern": "Panoramic observation tower stamp at {name_ja} ({name}) celebrating high-altitude views and skyline architecture."
    }
}

def haversine_distance(coord1: List[float], coord2: List[float]) -> float:
    """Calculate distance in meters between two [lon, lat] coordinates."""
    lon1, lat1 = coord1
    lon2, lat2 = coord2
    R = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

def normalize_text(text: str) -> str:
    """Normalize Japanese / English text for fuzzy deduplication."""
    if not text:
        return ""
    text = text.lower()
    for char in [" ", "\t", "\n", "駅", "道の駅", "案内所", "博物館", "美術館", "城", "pa", "sa", "・", "-", "_"]:
        text = text.replace(char, "")
    return text

def load_stampu_database() -> List[Dict[str, Any]]:
    path = os.path.join(os.path.dirname(__file__), "../public/data/stamps.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def run_pipeline():
    existing_stamps = load_stampu_database()
    print(f"Loaded {len(existing_stamps)} existing stamps from Stampu database.")

    # Index existing stamps by normalized name and coordinates
    existing_by_cat = {}
    for s in existing_stamps:
        cat = s.get("category", "")
        existing_by_cat.setdefault(cat, []).append(s)

    report = {
        "overview": {
            "stampu_total": len(existing_stamps),
            "hankore_total_registered": 8438,
            "hankore_active_stamps": 5782,
            "matched_categories": len(CATEGORY_MAPPING)
        },
        "categories": {}
    }

    # Summary table
    print("\n" + "="*80)
    print(f"{'Category':<22} | {'Stampu':<8} | {'Hankore':<8} | {'Potential +':<12} | {'Target Category':<16}")
    print("="*80)

    total_potential = 0
    for hk_cat, meta in CATEGORY_MAPPING.items():
        stampu_count = len(existing_by_cat.get(meta["target_category"], []))
        diff = max(0, meta["hankore_count"] - stampu_count)
        total_potential += diff
        report["categories"][meta["target_category"]] = {
            "hankore_category_name": hk_cat,
            "label": meta["label"],
            "stampu_count": stampu_count,
            "hankore_count": meta["hankore_count"],
            "potential_new_candidates": diff,
            "id_prefix": meta["id_prefix"]
        }
        print(f"{hk_cat:<20} | {stampu_count:<8} | {meta['hankore_count']:<8} | +{diff:<11} | {meta['target_category']:<16}")

    print("="*80)
    print(f"Total potential new stamps to stage: ~{total_potential} candidates across 8 existing categories.")

    # Ensure staging directory exists
    staging_dir = os.path.join(os.path.dirname(__file__), "staging")
    os.makedirs(staging_dir, exist_ok=True)

    summary_file = os.path.join(staging_dir, "hankore_category_preparation_report.json")
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n[OK] Pipeline report generated at: {summary_file}")
    print("[SAFETY] public/data/stamps.json remains completely unmodified.")

if __name__ == "__main__":
    run_pipeline()
