#!/usr/bin/env python3
"""
Imports missing regional, scenic, and private railway stations (Eki Stamps)
=============================================================================
Transfers authentic stations from Funakiya's Private Railway & Regional directory (私鉄・公営交通):
- Tsukuba Express (TX)
- Sotetsu Line (Sagami Railway)
- Enoden (Enoshima Electric Railway)
- Chichibu Railway
- Hakone Tozan Railway
- Fujikyu Railway
- Oigawa Railway
- Izu Kyuko & Izuhakone Railway
- Eizan Electric Railway & Randen
- Shinano Railway
- Tokyo Monorail & Yokohama Minatomirai Line
- Tama Monorail & Chiba Urban Monorail
- Osaka Monorail & Semboku Rapid Railway
- Kobe Port Liner & Kobe Electric Railway
- Sanriku Railway, Aoimori Railway & IGR Iwate Galaxy Railway
- IR Ishikawa Railway & Echizen Railway
- Tosa Kuroshio Railway & Chizu Express
- Tenryu Hamanako Railroad & Shin-Keisei Electric Railway

Features:
- Scrapes authentic station details (address, stamp location, hours, image)
- Downloads real photographed stamp images (.jpg) or generates bespoke Hanko SVG (.svg)
- Geocodes coordinates via GSI (国土地理院) with persistent cache
- Appends to public/data/stamps.json and updates public/data/prefectures.json
"""

import os
import re
import json
import time
import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from geocode_gsi import (
    geocode_address,
    extract_prefecture,
    extract_prefecture_en,
    extract_city,
    PREF_EN_TO_JA,
    PREF_JA_TO_EN
)
from generate_bespoke_stamps import generate_seal_svg

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

# Operator naming dictionary for clean bilingual titles
OPERATOR_MAP = {
    "相模鉄道": ("Sotetsu Line", "相模鉄道 (Sagami Railway / Sotetsu)", "sotetsu"),
    "江ノ島電鉄": ("Enoshima Electric Railway (Enoden)", "江ノ島電鉄 (Enoshima Electric Railway)", "enoden"),
    "つくばエクスプレス": ("Tsukuba Express", "首都圏新都市鉄道 (Tsukuba Express)", "tx"),
    "つくばエ": ("Tsukuba Express", "首都圏新都市鉄道 (Tsukuba Express)", "tx"),
    "秩父鉄道": ("Chichibu Railway", "秩父鉄道 (Chichibu Railway)", "chichibu"),
    "箱根登山電車": ("Hakone Tozan Railway", "小田急箱根 (Hakone Tozan Railway)", "hakone"),
    "箱根登山鉄道": ("Hakone Tozan Railway", "小田急箱根 (Hakone Tozan Railway)", "hakone"),
    "富士急行": ("Fujikyu Railway", "富士山麓電気鉄道 (Fujikyu Railway)", "fujikyu"),
    "大井川鐵道": ("Oigawa Railway", "大井川鐵道 (Oigawa Railway)", "oigawa"),
    "大井川鉄道": ("Oigawa Railway", "大井川鐵道 (Oigawa Railway)", "oigawa"),
    "伊豆急行": ("Izu Kyuko", "伊豆急行 (Izu Kyuko)", "izukyu"),
    "伊豆箱根鉄道": ("Izuhakone Railway", "伊豆箱根鉄道 (Izuhakone Railway)", "izuhakone"),
    "叡山電鉄": ("Eizan Electric Railway", "叡山電鉄 (Eizan Electric Railway)", "eizan"),
    "嵐電": ("Keifuku Electric Railroad (Randen)", "京福電気鉄道 (Randen)", "randen"),
    "三陸鉄道": ("Sanriku Railway", "三陸鉄道 (Sanriku Railway)", "sanriku"),
    "しなの鉄道": ("Shinano Railway", "しなの鉄道 (Shinano Railway)", "shinano"),
    "東京モノレール": ("Tokyo Monorail", "東京モノレール (Tokyo Monorail)", "tokyomonorail"),
    "多摩都市モノレール": ("Tama Monorail", "多摩都市モノレール (Tama Monorail)", "tamamonorail"),
    "多摩モノレール": ("Tama Monorail", "多摩都市モノレール (Tama Monorail)", "tamamonorail"),
    "大阪モノレール": ("Osaka Monorail", "大阪モノレール (Osaka Monorail)", "osakamonorail"),
    "ポートライナー": ("Kobe New Transit Port Liner", "神戸新交通 (Kobe New Transit)", "portliner"),
    "六甲ライナー": ("Kobe New Transit Rokko Liner", "神戸新交通 (Kobe New Transit)", "rokkoliner"),
    "横浜高速鉄道": ("Yokohama Minatomirai Line", "横浜高速鉄道 (Yokohama Minatomirai Railway)", "minatomirai"),
    "新京成電鉄": ("Shin-Keisei Electric Railway", "新京成電鉄 (Shin-Keisei Electric Railway)", "shinkeisei"),
    "青い森鉄道": ("Aoimori Railway", "青い森鉄道 (Aoimori Railway)", "aoimori"),
    "IRいしかわ鉄道": ("IR Ishikawa Railway", "IRいしかわ鉄道 (IR Ishikawa Railway)", "irishikawa"),
    "土佐くろしお鉄道": ("Tosa Kuroshio Railway", "土佐くろしお鉄道 (Tosa Kuroshio Railway)", "tosakuroshio"),
    "智頭急行": ("Chizu Express", "智頭急行 (Chizu Express)", "chizuexpress"),
    "能勢電鉄": ("Nose Electric Railway", "能勢電鉄 (Nose Electric Railway)", "nosedentetsu"),
    "天竜浜名湖鉄道": ("Tenryu Hamanako Railroad", "天竜浜名湖鉄道 (Tenryu Hamanako Railroad)", "tenhama"),
    "上信電鉄": ("Joshin Electric Railway", "上信電鉄 (Joshin Electric Railway)", "joshin"),
    "えちぜん鉄道": ("Echizen Railway", "えちぜん鉄道 (Echizen Railway)", "echizen"),
    "神戸電鉄": ("Kobe Electric Railway (Shintetsu)", "神戸電鉄 (Kobe Electric Railway)", "shintetsu"),
    "泉北高速鉄道": ("Semboku Rapid Railway", "泉北高速鉄道 (Semboku Rapid Railway)", "semboku"),
    "京都丹後鉄道": ("Kyoto Tango Railway", "WILLER TRAINS (Kyoto Tango Railway)", "tantetsu"),
    "近江鉄道": ("Ohmi Railway", "近江鉄道 (Ohmi Railway)", "ohmi"),
    "千葉都市モノレール": ("Chiba Urban Monorail", "千葉都市モノレール (Chiba Urban Monorail)", "chibamonorail"),
    "IGRいわて銀河鉄道": ("IGR Iwate Galaxy Railway", "アイジーアールいわて銀河鉄道 (IGR Iwate Galaxy Railway)", "igriwate"),
    "流鉄": ("Ryutetsu", "流鉄 (Ryutetsu)", "ryutetsu"),
    "ひたちなか海浜鉄道": ("Hitachinaka Seaside Railway", "ひたちなか海浜鉄道 (Hitachinaka Seaside Railway)", "hitachinaka"),
    "いすみ鉄道": ("Isumi Railway", "いすみ鉄道 (Isumi Railway)", "isumi"),
    "岳南電車": ("Gakunan Electric Train", "岳南電車 (Gakunan Electric Train)", "gakunan"),
    "くま川鉄道": ("Kumagawa Railway", "くま川鉄道 (Kumagawa Railway)", "kumagawa"),
    "わたらせ渓谷鐵道": ("Watarase Keikoku Railway", "わたらせ渓谷鐵道 (Watarase Keikoku Railway)", "watarase"),
    "アストラムライン": ("Astram Line", "広島高速交通 (Astram Line)", "astram"),
    "水島臨海鉄道": ("Mizushima Rinkai Railway", "水島臨海鉄道 (Mizushima Rinkai Railway)", "mizushima"),
    "北神急行電鉄": ("Hokushin Kyuko Railway", "北神急行電鉄 (Hokushin Kyuko Railway)", "hokushin"),
    "三岐鉄道": ("Sangi Railway", "三岐鉄道 (Sangi Railway)", "sangi"),
    "関東鉄道": ("Kanto Railway", "関東鉄道 (Kanto Railway)", "kantotetsudo"),
    "北海道ちほく高原鉄道": ("Hokkaido Chihoku Kogen Railway", "北海道ちほく高原鉄道 (CR)", "chihoku"),
    "野岩鉄道": ("Yagan Railway", "野岩鉄道 (Yagan Railway)", "yagan"),
    "阪神電鉄": ("Hanshin Electric Railway", "阪神電気鉄道 (Hanshin Electric Railway)", "hanshin"),
    "京福電鉄": ("Keifuku Electric Railroad", "京福電気鉄道 (Keifuku)", "keifuku"),
}


def download_image(img_url: str, save_path: str) -> bool:
    try:
        resp = requests.get(img_url, headers=HEADERS, timeout=12)
        if resp.status_code == 200 and len(resp.content) > 1000:
            with open(save_path, "wb") as f:
                f.write(resp.content)
            return True
    except Exception:
        pass
    return False


def collect_mintetsu_catalog() -> List[Dict[str, str]]:
    """Crawl pages 1-11 of mintetsu to collect all station entries."""
    candidates = []
    seen_urls = set()

    for p in range(1, 12):
        url = f"{BASE_URL}/mintetsu/" if p == 1 else f"{BASE_URL}/mintetsu/index_{p}.html"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.status_code != 200:
                continue
            resp.encoding = "utf-8"
            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.find_all("a"):
                t = a.get_text().strip()
                h = a.get("href", "")
                if "駅のスタンプ" in t and h.endswith(".html"):
                    m = re.match(r"^(.*?)駅のスタンプ", t)
                    st_name = m.group(1).strip() if m else t
                    clean_name = st_name.replace("【私鉄】", "").strip()
                    if h not in seen_urls:
                        seen_urls.add(h)
                        candidates.append({
                            "raw_name": clean_name,
                            "url": h
                        })
        except Exception as e:
            print(f"Error fetching catalog page {p}: {e}")

    return candidates


def match_operator(raw_name: str) -> Tuple[str, str, str, str, str]:
    """
    Returns (station_clean_name, operator_clean_prefix, line_en, op_ja, id_prefix)
    """
    # Sort keys by descending length
    sorted_keys = sorted(OPERATOR_MAP.keys(), key=len, reverse=True)
    for key in sorted_keys:
        if key in raw_name:
            line_en, op_ja, prefix = OPERATOR_MAP[key]
            st_name = raw_name.replace(key, "").strip()
            # Clean any trailing leftovers
            st_clean = re.sub(r"^(?:鉄道|電鉄|電車|急行|ライン|高速鉄道)?", "", st_name).strip()
            st_clean = st_clean.replace("駅", "").strip() or st_name.replace("駅", "").strip()
            return st_clean, key, line_en, op_ja, prefix

    # Fallback heuristic
    m = re.match(r"^(.+?)(?:鉄道|電鉄|電車|急行|ライン|高速鉄道|モノレール|交通|バス|新交通|軌道)(.*)$", raw_name)
    if m:
        op_prefix = m.group(1)
        st_name = m.group(2).strip().replace("駅", "")
        return st_name or raw_name.replace("駅", ""), op_prefix, f"{op_prefix} Railway", f"{op_prefix} (Regional Railway)", "eki-reg"

    return raw_name.replace("駅", ""), "地方鉄道", "Regional Railway", "地方鉄道 (Regional Railway)", "eki-reg"


def parse_station_page(item: Dict[str, str]) -> Optional[Dict[str, Any]]:
    url = item["url"]
    try:
        resp = requests.get(url, headers=HEADERS, timeout=12)
        if resp.status_code != 200:
            return None
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "html.parser")
        text = soup.get_text()

        # Station names
        st_clean, op_key, line_en, op_ja, id_prefix = match_operator(item["raw_name"])
        if not st_clean:
            st_clean = item["raw_name"].replace("駅", "")

        # Proper Japanese display name: e.g. "相模鉄道 横浜駅" or "江ノ島電鉄 鎌倉高校前駅"
        name_ja_clean = f"{op_key} {st_clean}駅" if op_key and op_key not in st_clean else f"{st_clean}駅"

        # Romaji from URL slug
        slug_m = re.search(r"/([a-zA-Z0-9\-]+)\.html", url)
        slug_raw = slug_m.group(1).lower() if slug_m else st_clean
        parts = slug_raw.split("-", 1)
        st_slug = parts[1] if len(parts) > 1 and parts[0] in ["sotetsu", "enoden", "tx", "chichibu", "hakone", "fujikyu", "oigawa", "izu", "randen", "eizan", "tkt", "astram", "ryu", "hitachinaka", "isumi", "shintetsu", "gakunan", "kumagawa", "wa", "mizurin", "hokushin", "shinkeisei", "aoimori", "irishikawa", "tenhama", "joshin", "echizen", "tantetsu", "ohmi", "chiba", "igriwate", "sangi", "kanto", "yagan"] else slug_raw

        stamp_id = f"eki-{id_prefix}-{st_slug}"
        romaji_display = st_slug.replace("-", " ").capitalize()
        name_en = f"{romaji_display} Station ({line_en})"
        name_romaji = f"{st_slug}-eki"

        # Address
        m_addr = re.search(r"所在地：(?:〒\d{3}-\d{4}\s*)?([^\n\r]+)", text)
        address = m_addr.group(1).strip() if m_addr else ""

        # Stamp Location
        m_loc = re.search(r"設置場所：([^\n\r]+)", text)
        stamp_location = m_loc.group(1).strip() if m_loc else "駅改札窓口 (Station ticket gate window)"

        # Hours
        m_hrs = re.search(r"営業時間：([^\n\r]+)", text)
        hours = m_hrs.group(1).strip() if m_hrs else "始発～終電 (05:30 - 23:30)"

        # Image URL
        img_url = ""
        for img in soup.find_all("img"):
            src = img.get("src", "")
            if "/i/stamp/" in src and "sum" not in src:
                img_url = src
                break

        # Geocode
        coords = None
        if address:
            coords = geocode_address(address)
        if not coords or coords == (0.0, 0.0):
            coords = geocode_address(f"{st_clean}駅")

        if not coords or coords == (0.0, 0.0):
            return None

        pref = extract_prefecture(address) if address else ""
        pref_en = extract_prefecture_en(pref) if pref else "Japan"
        city = extract_city(address) if address else f"{st_clean} Area"

        # Save Image
        img_filename = f"{stamp_id}.jpg"
        img_dest = os.path.join(IMAGES_DIR, img_filename)
        has_real_photo = False
        if img_url:
            has_real_photo = download_image(img_url, img_dest)

        if not has_real_photo or not os.path.exists(img_dest):
            # Generate bespoke Hanko SVG
            svg_content = generate_seal_svg({
                "id": stamp_id,
                "name_ja": f"{st_clean}駅",
                "category": "eki",
                "prefecture": pref_en,
                "city": city
            })
            img_filename = f"{stamp_id}.svg"
            img_dest = os.path.join(IMAGES_DIR, img_filename)
            with open(img_dest, "w", encoding="utf-8") as f:
                f.write(svg_content)

        stamp_record = {
            "id": stamp_id,
            "name": name_en,
            "name_ja": name_ja_clean,
            "name_romaji": name_romaji,
            "category": "eki",
            "prefecture": pref_en,
            "city": city,
            "address": address or f"{pref}{city}",
            "coordinates": [round(coords[0], 6), round(coords[1], 6)],
            "stampLocation": stamp_location,
            "hours": hours,
            "operator": op_ja,
            "imageUrl": f"/images/stamps/{img_filename}",
            "description": f"Commemorative railway stamp for {romaji_display} Station on the {line_en} ({op_ja}) located in {city}, {pref_en}. Depicts regional landmarks, railway rolling stock, and scenic transit heritage.",
            "source": "Funakiya Stamp Notebook (旅のスタンプ帳)",
            "sourceUrl": url
        }
        return stamp_record

    except Exception as e:
        print(f"Error parsing station {url}: {e}")
        return None


def main():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        stamps = json.load(f)

    existing_ids = {s["id"] for s in stamps}
    existing_coords = {(round(s["coordinates"][0], 3), round(s["coordinates"][1], 3)) for s in stamps}
    existing_names = {s.get("name_ja", "") for s in stamps}

    print(f"Existing stamps: {len(stamps)} (Eki: {len([s for s in stamps if s.get('category') == 'eki'])})", flush=True)

    print("\nCollecting candidate stations from Funakiya Private Railway directory...", flush=True)
    catalog = collect_mintetsu_catalog()
    print(f"Discovered {len(catalog)} station candidates in catalog.", flush=True)

    items_to_process = []
    for item in catalog:
        raw = item["raw_name"]
        raw_full = f"{raw}{'駅' if not raw.endswith('駅') else ''}"
        if raw_full in existing_names:
            continue
        items_to_process.append(item)

    print(f"Candidate stations to process: {len(items_to_process)}", flush=True)

    added = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        future_to_item = {executor.submit(parse_station_page, item): item for item in items_to_process}
        for future in as_completed(future_to_item):
            item = future_to_item[future]
            try:
                stamp = future.result()
                if stamp:
                    c_key = (round(stamp["coordinates"][0], 3), round(stamp["coordinates"][1], 3))
                    if stamp["id"] not in existing_ids and stamp["name_ja"] not in existing_names:
                        stamps.append(stamp)
                        existing_ids.add(stamp["id"])
                        existing_coords.add(c_key)
                        existing_names.add(stamp["name_ja"])
                        added.append(stamp)
                        print(f"  [{len(added)}] Added {stamp['id']}: {stamp['name']} ({stamp['name_ja']}) -> {stamp['prefecture']}", flush=True)
            except Exception as e:
                print(f"Failed processing {item['url']}: {e}", flush=True)

    print(f"\n=======================================================", flush=True)
    print(f"Successfully added {len(added)} new authentic railway stations!", flush=True)
    eki_total = len([s for s in stamps if s.get('category') == 'eki'])
    print(f"Total railway stations in Stampu: {eki_total}", flush=True)
    print(f"Total stamps in database: {len(stamps)}", flush=True)
    print(f"=======================================================", flush=True)

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(stamps, f, ensure_ascii=False, indent=2)

    # Update prefectures
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
        print("Updated prefectures.json counts successfully.", flush=True)


if __name__ == "__main__":
    main()
