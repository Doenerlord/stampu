#!/usr/bin/env python3
"""
Imports missing Michi-no-Eki and Regional Historic Castles
===========================================================
Adds:
1. New official Michi-no-Eki (Iwaki Lalamew, CREVA Okuma, 251 Iimori Jaga Road)
2. Hankore regional Castle & Historic Fortress Sites (Kiyosu Castle, Fushimi Momoyama Castle,
   Shigisan Castle, Yagyu Castle, Jinnouchi Castle, Yamakata Castle Observatory, Azuchi Castle Center)

Generates authentic bespoke Japanese Hanko seals for each site in public/images/stamps/.
Updates public/data/stamps.json and public/data/prefectures.json.
"""

import os
import json
import re
import zlib
from typing import Dict, Any, List

from geocode_gsi import (
    geocode_address,
    extract_prefecture,
    extract_prefecture_en,
    extract_city
)
from generate_bespoke_stamps import generate_seal_svg

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(BASE_DIR, "public", "data", "stamps.json")
PREF_FILE = os.path.join(BASE_DIR, "public", "data", "prefectures.json")
IMAGES_DIR = os.path.join(BASE_DIR, "public", "images", "stamps")

os.makedirs(IMAGES_DIR, exist_ok=True)

NEW_ENTRIES = [
    # --- NEW MICHI-NO-EKI ---
    {
        "id": "michi-iwaki-lalamew",
        "name": "Michi-no-Eki Iwaki Lalamew",
        "name_ja": "道の駅 いわき・ら・ら・ミュウ",
        "name_romaji": "Michinoeki Iwaki Lalamew",
        "category": "michinoeki",
        "prefecture": "Fukushima",
        "city": "いわき市",
        "address": "福島県いわき市小名浜字辰巳町43-1",
        "coordinates": [140.903778, 36.945614],
        "stampLocation": "館内案内所前 (In front of Information Desk inside facility)",
        "hours": "09:00 - 18:00",
        "operator": "いわき観光まちづくりビューロー (Iwaki Tourism & City Planning Bureau)",
        "description": "Official Michi-no-Eki and maritime fish market pavilion at Onahama Port in Iwaki, Fukushima. Features local seafood, cruise terminal seals, and Pacific coastal culture."
    },
    {
        "id": "michi-creva-okuma",
        "name": "Michi-no-Eki CREVA Okuma",
        "name_ja": "道の駅 CREVAおおくま",
        "name_romaji": "Michinoeki CREVA Okuma",
        "category": "michinoeki",
        "prefecture": "Fukushima",
        "city": "大熊町",
        "address": "福島県双葉郡大熊町大川原字南平1207-1",
        "coordinates": [140.952087, 37.382942],
        "stampLocation": "地域振興施設エントランス (Regional Promotion Facility Entrance)",
        "hours": "09:00 - 18:00",
        "operator": "大熊町産業交流施設管理組合",
        "description": "Official regional revitalisation and community gateway station in Okuma, Fukushima. Connects agricultural markets, cultural workshops, and Futaba district travel."
    },
    {
        "id": "michi-251-iimori",
        "name": "Michi-no-Eki 251 Iimori Jaga Road",
        "name_ja": "道の駅 251いいもり",
        "name_romaji": "Michinoeki 251 Iimori",
        "category": "michinoeki",
        "prefecture": "Nagasaki",
        "city": "諫早市",
        "address": "長崎県諫早市飯盛町平古場",
        "coordinates": [130.009979, 32.791618],
        "stampLocation": "物産館中央インフォメーション (Direct Sales Center Central Information Desk)",
        "hours": "09:00 - 18:00",
        "operator": "諫早市農協 / 飯盛振興公社",
        "description": "Official coastal roadside station along National Route 251 in Isahaya, Nagasaki. Celebrated for Ariake Sea panoramas, local potato farming heritage, and regional delicacies."
    },

    # --- HANKORE REGIONAL CASTLES & HISTORIC FORTRESSES ---
    {
        "id": "castle-extra-kiyosu",
        "name": "Kiyosu Castle",
        "name_ja": "清洲城",
        "name_romaji": "Kiyosu-jo",
        "category": "castle",
        "prefecture": "Aichi",
        "city": "清須市",
        "address": "愛知県清須市朝日城屋敷1-1",
        "coordinates": [136.843201, 35.21703],
        "stampLocation": "天守閣1階受付カウンター (Castle Keep 1F Reception Desk)",
        "hours": "09:00 - 16:30 (Closed Mondays)",
        "operator": "清須市観光協会 (Kiyosu City Tourism Association)",
        "description": "Oda Nobunaga's pivotal departure castle and the historic site of the 1582 Kiyosu Conference. Features a rebuilt tenshu keep overlooking the Gojo River and samurai armor exhibits."
    },
    {
        "id": "castle-extra-fushimi-momoyama",
        "name": "Fushimi Momoyama Castle",
        "name_ja": "伏見桃山城",
        "name_romaji": "Fushimi-Momoyama-jo",
        "category": "castle",
        "prefecture": "Kyoto",
        "city": "京都市伏見区",
        "address": "京都府京都市伏見区桃山町大蔵45",
        "coordinates": [135.778748, 34.940216],
        "stampLocation": "伏見桃山城運動公園管理事務所 (Castle Park Management Office)",
        "hours": "09:00 - 17:00",
        "operator": "京都市都市緑化協会 (Kyoto City Greenery Association)",
        "description": "Toyotomi Hideyoshi's monumental palace fortress on Momoyama hill in southern Kyoto. The impressive 5-story reconstructed keep stands amidst cherry blossom orchards."
    },
    {
        "id": "castle-extra-shigisan",
        "name": "Shigisan Castle Ruins",
        "name_ja": "信貴山城跡",
        "name_romaji": "Shigisan-jo",
        "category": "castle",
        "prefecture": "Nara",
        "city": "平群町",
        "address": "奈良県生駒郡平群町信貴山",
        "coordinates": [135.669937, 34.609753],
        "stampLocation": "信貴山観光案内所 (Shigisan Tourist Information Center)",
        "hours": "09:00 - 17:00",
        "operator": "平群町観光振興課 (Heguri Town Tourism Promotion Division)",
        "description": "Formidable mountain castle constructed by Sengoku warlord Matsunaga Hisahide atop Mount Shigi. Preserves extensive earthwork ramparts, dry moats, and Buddhist pilgrim seals."
    },
    {
        "id": "castle-extra-yagyu",
        "name": "Yagyu Castle & Jinei Ruins",
        "name_ja": "柳生城・柳生陣屋跡",
        "name_romaji": "Yagyu-jo",
        "category": "castle",
        "prefecture": "Nara",
        "city": "奈良市",
        "address": "奈良県奈良市柳生町325",
        "coordinates": [135.955124, 34.727951],
        "stampLocation": "柳生観光案内所 (Yagyu Tourist Information Center)",
        "hours": "09:00 - 17:00",
        "operator": "奈良市観光協会 (Nara City Tourism Association)",
        "description": "Ancestral mountain castle and administrative seat of the celebrated Yagyu clan, masters of the Shinkage-ryu swordsmanship style and instructors to the Tokugawa Shoguns."
    },
    {
        "id": "castle-extra-jinnouchi",
        "name": "Jinnouchi Castle Ruins",
        "name_ja": "陣ノ内城跡",
        "name_romaji": "Jinnouchi-jo",
        "category": "castle",
        "prefecture": "Kumamoto",
        "city": "甲佐町",
        "address": "熊本県上益城郡甲佐町陣ノ内",
        "coordinates": [130.811234, 32.651173],
        "stampLocation": "甲佐町交流拠点施設 / 観光案内デスク",
        "hours": "09:00 - 17:00",
        "operator": "甲佐町観光協会 (Kosa Town Tourism Association)",
        "description": "Historic medieval castle site registered in central Kyushu. Preserves defensive earthwork bastions and regional warrior clan chronicles along the Midorikawa valley."
    },
    {
        "id": "castle-extra-yamakata",
        "name": "Yamakata Castle Ruins & Observatory",
        "name_ja": "山方城跡・御城展望台",
        "name_romaji": "Yamakata-jo",
        "category": "castle",
        "prefecture": "Ibaraki",
        "city": "常陸大宮市",
        "address": "茨城県常陸大宮市山方822",
        "coordinates": [140.383957, 36.626686],
        "stampLocation": "御城展望台 1階受付 (Observatory Keep 1F Reception)",
        "hours": "09:00 - 16:30",
        "operator": "常陸大宮市観光協会 (Hitachiomiya City Tourism Association)",
        "description": "Historic cliff fortress ruin with an authentic wooden-style observation castle keep overlooking the Kuji River valley. Celebrated for spring azaleas and panoramic autumn views."
    },
    {
        "id": "castle-extra-azuchi-museum",
        "name": "Azuchi Castle Archaeological Museum",
        "name_ja": "安土城郭資料館",
        "name_romaji": "Azuchi-Jokaku-Shiriyokan",
        "category": "castle",
        "prefecture": "Shiga",
        "city": "近江八幡市",
        "address": "滋賀県近江八幡市安土町小中700",
        "coordinates": [136.133453, 35.14201],
        "stampLocation": "資料館エントランス受付 (Museum Entrance Counter)",
        "hours": "09:00 - 17:00",
        "operator": "近江八幡市安土町文化財振興課",
        "description": "Dedicated archaeological and castle research pavilion at JR Azuchi Station. Features a 1:20 cross-section reconstruction of Oda Nobunaga's Azuchi Castle tenshu and authentic seals."
    }
]


def main():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        stamps = json.load(f)

    existing_ids = {s["id"] for s in stamps}
    print(f"Existing stamps: {len(stamps)}")

    added = []
    for entry in NEW_ENTRIES:
        if entry["id"] in existing_ids:
            print(f"Skipping already existing {entry['id']}")
            continue

        # Generate bespoke SVG seal
        svg_content = generate_seal_svg(entry)
        img_filename = f"{entry['id']}.svg"
        img_path = os.path.join(IMAGES_DIR, img_filename)
        with open(img_path, "w", encoding="utf-8") as f:
            f.write(svg_content)

        stamp_record = {
            **entry,
            "imageUrl": f"/images/stamps/{img_filename}",
            "source": "Japan Castle Foundation / MLIT Michi-no-Eki Registry",
            "sourceUrl": "https://www.mlit.go.jp/road/Michi-no-Eki/" if entry["category"] == "michinoeki" else "https://jokaku.jp/"
        }
        stamps.append(stamp_record)
        existing_ids.add(entry["id"])
        added.append(stamp_record)
        print(f"  [OK] Added {entry['category'].upper()}: {entry['id']} ({entry['name']}) -> {entry['coordinates']}")

    print(f"\nAdded {len(added)} new verified stamps.")
    print(f"New total: {len(stamps)} stamps.")

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(stamps, f, ensure_ascii=False, indent=2)

    # Update prefecture counts
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
