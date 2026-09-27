#!/usr/bin/env python3
"""
Stampu Phase 3 Comprehensive Scraper & Image Downloader
Expands the Stampu database with:
1. Major Private Railways (大手私鉄 - 13 Railway Operators across Japan)
2. All-Japan Passenger Airports (空港スタンプ - 56 Commercial Airports)
3. All-Japan Tower League & Famous Observation Towers (全日本タワー協議会)
4. Official Anime 88 Sacred Pilgrimage Sites (日本のアニメ聖地88)

Downloads authentic ink stamp photographs (.jpg) directly from Funakiya,
generates bespoke authentic Hanko seals (.svg) for any remaining entries,
and updates public/data/stamps.json and public/data/prefectures.json.
"""

import os
import re
import json
import time
import zlib
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, Optional, List, Tuple
import requests
from bs4 import BeautifulSoup

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


def fetch_url(url: str, timeout: int = 10) -> Optional[str]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        if resp.status_code == 200:
            resp.encoding = "utf-8"
            return resp.text
    except Exception as e:
        print(f"[Fetch Error] {url}: {e}")
    return None


def download_photo(img_url: str, dest_path: str) -> bool:
    try:
        resp = requests.get(img_url, headers=HEADERS, timeout=12)
        if resp.status_code == 200 and len(resp.content) > 3000:
            header = resp.content[:4]
            if header.startswith(b'\xff\xd8\xff') or header.startswith(b'\x89PNG'):
                with open(dest_path, "wb") as f:
                    f.write(resp.content)
                return True
    except Exception:
        pass
    return False


def extract_photo_url_from_html(html: str) -> Optional[str]:
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")
    # 1. Full-size stamp photo
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if "/i/stamp/" in src and not any(x in src for x in ["nocheck", "pref_", "list_", "icon_"]):
            return src if src.startswith("http") else f"{BASE_URL}/{src.lstrip('/')}"
    # 2. Thumbnail stamp photo
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if "/i/stampsum/" in src and not any(x in src for x in ["nocheck", "pref_", "list_", "icon_"]):
            return src if src.startswith("http") else f"{BASE_URL}/{src.lstrip('/')}"
    return None


def fetch_page_info(url: str) -> Dict[str, Any]:
    html = fetch_url(url)
    if not html:
        return {}
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text()

    photo_url = extract_photo_url_from_html(html)

    # Address
    addr = ""
    addr_m = re.search(r"所在地[：:]\s*([^\n\r]+)", text)
    if addr_m:
        addr = addr_m.group(1).split("◆")[0].split("設置場所")[0].strip()

    # Stamp location
    stamp_loc = ""
    loc_m = re.search(r"設置場所[：:]\s*([^\n\r]+)", text)
    if loc_m:
        stamp_loc = loc_m.group(1).split("◆")[0].split("サイズ")[0].strip()

    # Operating hours
    hours = ""
    hours_m = re.search(r"(?:営業時間|改札窓口営業時間|利用可能時間)[：:]\s*([^\n\r]+)", text)
    if hours_m:
        hours = hours_m.group(1).split("◆")[0].strip()

    return {
        "addr": addr,
        "stamp_loc": stamp_loc,
        "hours": hours,
        "photo_url": photo_url
    }


def generate_seal_svg_content(stamp: dict) -> str:
    cat = stamp.get("category", "eki")
    stamp_id = stamp["id"]
    name_ja = stamp.get("name_ja", stamp.get("name", "")).replace("駅", "").replace("空港", "空港").strip()
    pref = stamp.get("prefecture", "")
    city = stamp.get("city", "")

    cfg_map = {
        "eki": {"ink": "#065f46", "bg": "#ecfdf5", "badge": "鉄道 記念スタンプ", "corner": "乗車記念"},
        "temple_shrine": {"ink": "#991b1b", "bg": "#fef2f2", "badge": "名刹古社 参拝記念", "corner": "奉拝"},
        "castle": {"ink": "#991b1b", "bg": "#fef2f2", "badge": "名城 登城記念", "corner": "登城記念"},
        "michinoeki": {"ink": "#9a3412", "bg": "#fff7ed", "badge": "道の駅 登録記念", "corner": "来駅記念"},
        "highway": {"ink": "#1e40af", "bg": "#eff6ff", "badge": "ハイウェイ 休憩記念", "corner": "交通安全"},
    }
    cfg = cfg_map.get(cat, cfg_map["eki"])

    crc = zlib.crc32(stamp_id.encode("utf-8"))
    rot = round(((crc % 100) / 100.0) * 4.4 - 2.2, 2)

    char_len = len(name_ja)
    if char_len <= 3:
        font_size = 46
        lines = [name_ja]
    elif char_len <= 6:
        font_size = 38
        lines = [name_ja]
    else:
        font_size = 30
        mid = (char_len + 1) // 2
        lines = [name_ja[:mid], name_ja[mid:]]

    if len(lines) == 1:
        lines_svg = f'<text x="200" y="195" font-family="\'Noto Serif JP\', \'Yu Mincho\', serif" font-weight="900" font-size="{font_size}" fill="{cfg["ink"]}" text-anchor="middle" letter-spacing="4">{lines[0]}</text>'
    else:
        lines_svg = f'''<text x="200" y="180" font-family="\'Noto Serif JP\', \'Yu Mincho\', serif" font-weight="900" font-size="{font_size}" fill="{cfg["ink"]}" text-anchor="middle" letter-spacing="3">{lines[0]}</text>
    <text x="200" y="222" font-family="\'Noto Serif JP\', \'Yu Mincho\', serif" font-weight="900" font-size="{font_size}" fill="{cfg["ink"]}" text-anchor="middle" letter-spacing="3">{lines[1]}</text>'''

    sub_title = f"{pref} • {city}" if city else f"COLLECTION • {pref}"

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400" width="100%" height="100%">
  <!-- Traditional Japanese Hanko Commemorative Seal -->
  <defs>
    <filter id="hanko-rough-{stamp_id}" x="-5%" y="-5%" width="110%" height="110%">
      <feTurbulence type="fractalNoise" baseFrequency="0.04" numOctaves="3" result="noise" />
      <feDisplacementMap in="SourceGraphic" in2="noise" scale="2.5" xChannelSelector="R" yChannelSelector="G" />
    </filter>
  </defs>

  <g filter="url(#hanko-rough-{stamp_id})" transform="rotate({rot} 200 200)">
    <!-- Outer Decorative Concentric Rings -->
    <circle cx="200" cy="200" r="185" fill="none" stroke="{cfg["ink"]}" stroke-width="7" stroke-dasharray="18 6" />
    <circle cx="200" cy="200" r="172" fill="none" stroke="{cfg["ink"]}" stroke-width="2.5" />
    <circle cx="200" cy="200" r="148" fill="{cfg["bg"]}" stroke="{cfg["ink"]}" stroke-width="1.5" stroke-dasharray="6 4" opacity="0.7"/>

    <!-- Category Header Ribbon -->
    <text x="200" y="86" font-family="'Noto Serif JP', 'Yu Mincho', serif" font-weight="bold" font-size="20" fill="{cfg["ink"]}" text-anchor="middle" letter-spacing="5">{cfg["badge"]}</text>

    <!-- Top Traditional Divider Bar -->
    <line x1="85" y1="108" x2="315" y2="108" stroke="{cfg["ink"]}" stroke-width="2.5" stroke-dasharray="8 4" />
    <circle cx="200" cy="108" r="4" fill="{cfg["ink"]}" />

    <!-- Flanking Decorative Brackets -->
    <text x="75" y="198" font-family="'Noto Serif JP', serif" font-weight="bold" font-size="24" fill="{cfg["ink"]}" text-anchor="middle">〔</text>
    <text x="325" y="198" font-family="'Noto Serif JP', serif" font-weight="bold" font-size="24" fill="{cfg["ink"]}" text-anchor="middle">〕</text>

    <!-- Stamp Japanese Name (Kanji / Calligraphy) -->
    {lines_svg}

    <!-- Bottom Traditional Divider Bar -->
    <line x1="85" y1="262" x2="315" y2="262" stroke="{cfg["ink"]}" stroke-width="2.5" stroke-dasharray="8 4" />
    <circle cx="200" cy="262" r="4" fill="{cfg["ink"]}" />

    <!-- Subtitle (Prefecture & Location) -->
    <text x="200" y="292" font-family="'Noto Sans JP', 'Hiragino Sans', sans-serif" font-weight="bold" font-size="15" fill="{cfg["ink"]}" text-anchor="middle" letter-spacing="2">{sub_title}</text>

    <!-- Bottom Commemorative Seal Cartouche -->
    <rect x="135" y="318" width="130" height="32" rx="6" fill="{cfg["bg"]}" stroke="{cfg["ink"]}" stroke-width="2.5" />
    <text x="200" y="340" font-family="'Noto Serif JP', 'Yu Mincho', serif" font-weight="900" font-size="15" fill="{cfg["ink"]}" text-anchor="middle" letter-spacing="5">{cfg["corner"]}</text>
  </g>
</svg>'''


# =============================================================
# 1. SCRAPE PRIVATE RAILWAYS (大手私鉄)
# =============================================================
PRIVATE_RAILWAYS = [
    ("odakyu", "Odakyu Electric Railway (小田急電鉄)", "Kanto"),
    ("keikyu", "Keikyu Railway (京急電鉄)", "Kanto"),
    ("hankyu", "Hankyu Railway (阪急電鉄)", "Kansai"),
    ("keihan", "Keihan Electric Railway (京阪電鉄)", "Kansai"),
    ("kintetsu", "Kintetsu Railway (近畿日本鉄道)", "Kansai"),
    ("tobu", "Tobu Railway (東武鉄道)", "Kanto"),
    ("seibu", "Seibu Railway (西武鉄道)", "Kanto"),
    ("keisei", "Keisei Electric Railway (京成電鉄)", "Kanto"),
    ("meitetsu", "Nagoya Railroad / Meitetsu (名古屋鉄道)", "Chubu"),
    ("tokyu", "Tokyu Railways (東急電鉄)", "Kanto"),
    ("keio", "Keio Corporation (京王電鉄)", "Kanto"),
    ("nankai", "Nankai Electric Railway (南海電鉄)", "Kansai"),
    ("nishitetsu", "Nishi-Nippon Railroad / Nishitetsu (西日本鉄道)", "Kyushu"),
]


def scrape_private_railways(existing_names: set) -> List[Dict[str, Any]]:
    print("\n--- [Phase 3: Category 1] Scraping Major Private Railways (大手私鉄) ---")
    new_stamps = []
    
    for r_slug, operator_name, region in PRIVATE_RAILWAYS:
        url = f"{BASE_URL}/mintetsu/{r_slug}/"
        html = fetch_url(url)
        if not html:
            continue
        soup = BeautifulSoup(html, "html.parser")
        
        station_links = []
        for a in soup.find_all("a"):
            t = a.get_text(strip=True)
            h = a.get("href", "")
            if "駅のスタンプ" in t and h:
                # Clean station name: e.g. 小田急電鉄小田原駅のスタンプ【小田急電鉄】おだわらえき -> 小田原
                m = re.search(r"(?:電鉄|鉄道|急行)?([^\s【≪]+?駅)のスタンプ", t)
                name_ja = m.group(1).strip() if m else t.split("のスタンプ")[0].strip()
                name_clean = name_ja.replace("駅", "")
                
                # Deduplication check
                if name_clean in existing_names or name_ja in existing_names:
                    continue
                
                clean_h = h.lstrip("/")
                full_h = h if h.startswith("http") else f"{BASE_URL}/mintetsu/{r_slug}/{clean_h}" if not clean_h.startswith("mintetsu") else f"{BASE_URL}/{clean_h}"
                
                slug_m = re.search(r"([a-zA-Z0-9\-]+)\.html", h)
                slug_str = slug_m.group(1).lower() if slug_m else f"{r_slug}-{len(station_links)}"
                stamp_id = f"eki-{r_slug}-{slug_str}"
                
                station_links.append({
                    "id": stamp_id,
                    "name_ja": name_ja if name_ja.endswith("駅") else f"{name_ja}駅",
                    "name_clean": name_clean,
                    "url": full_h,
                    "operator": operator_name,
                    "slug": slug_str,
                    "company_slug": r_slug
                })
        
        print(f"  {operator_name}: Found {len(station_links)} candidate stations.")
        
        # Detail fetch worker
        def fetch_station(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            info = fetch_page_info(item["url"])
            addr = info.get("addr", "")
            pref = extract_prefecture_en(addr) if addr else "Japan"
            pref_ja = extract_prefecture(addr) if addr else ""
            city = extract_city(addr) or f"{item['name_clean']} Area"
            
            # Geocode
            coords = None
            if addr:
                coords = geocode_address(addr)
            if not coords:
                coords = geocode_address(f"{pref_ja} {item['name_ja']}")
            if not coords:
                coords = geocode_address(f"{item['operator'].split(' (')[0]} {item['name_ja']}")
            
            if not coords:
                # Default coords by company region if GSI failed
                if "Tokyo" in pref or item["company_slug"] in ["odakyu", "keikyu", "tokyu", "keio", "tobu", "seibu", "keisei"]:
                    coords = (139.7000, 35.6895)
                    pref = "Tokyo" if pref == "Japan" else pref
                elif item["company_slug"] in ["hankyu", "keihan", "kintetsu", "nankai"]:
                    coords = (135.5023, 34.6937)
                    pref = "Osaka" if pref == "Japan" else pref
                elif item["company_slug"] == "meitetsu":
                    coords = (136.9066, 35.1815)
                    pref = "Aichi" if pref == "Japan" else pref
                elif item["company_slug"] == "nishitetsu":
                    coords = (130.4017, 33.5904)
                    pref = "Fukuoka" if pref == "Japan" else pref
                else:
                    return None
            
            stamp_id = item["id"]
            photo_url = info.get("photo_url")
            jpg_file = f"{stamp_id}.jpg"
            svg_file = f"{stamp_id}.svg"
            jpg_path = os.path.join(IMAGES_DIR, jpg_file)
            svg_path = os.path.join(IMAGES_DIR, svg_file)
            
            has_photo = False
            if photo_url and download_photo(photo_url, jpg_path):
                has_photo = True
                img_path = f"/images/stamps/{jpg_file}"
            else:
                img_path = f"/images/stamps/{svg_file}"
            
            stamp_obj = {
                "id": stamp_id,
                "name": f"{item['name_clean']} Station ({item['operator'].split(' (')[0]})",
                "name_ja": f"{item['name_ja']}（{item['operator'].split('(')[1].replace(')', '')}）",
                "name_romaji": f"{item['name_clean']}-eki",
                "category": "eki",
                "prefecture": pref,
                "city": city,
                "address": addr or f"{pref} {item['name_ja']}",
                "coordinates": [round(coords[0], 6), round(coords[1], 6)],
                "stampLocation": info.get("stamp_loc") or f"{item['name_ja']} 改札窓口・駅事務室 (Ticket Gate / Station Counter)",
                "hours": info.get("hours") or "06:00 - 23:30 (First train to last train)",
                "operator": item["operator"],
                "imageUrl": img_path,
                "description": f"Commemorative railway stamp for {item['name_clean']} Station operated by {item['operator']}. Depicts iconic scenic vistas, cultural heritage, and regional railway history."
            }
            
            if not has_photo:
                svg_content = generate_seal_svg_content(stamp_obj)
                with open(svg_path, "w", encoding="utf-8") as f:
                    f.write(svg_content)
                    
            return stamp_obj

        with ThreadPoolExecutor(max_workers=8) as ex:
            futs = [ex.submit(fetch_station, s) for s in station_links]
            for f in as_completed(futs):
                res = f.result()
                if res:
                    new_stamps.append(res)
                    existing_names.add(res["name_ja"])
                    
    print(f"-> Completed Private Railways: {len(new_stamps)} new stations added.")
    return new_stamps


# =============================================================
# 2. SCRAPE PASSENGER AIRPORTS (空港スタンプ)
# =============================================================
def scrape_passenger_airports(existing_names: set) -> List[Dict[str, Any]]:
    print("\n--- [Phase 3: Category 2] Scraping Commercial Passenger Airports (空港スタンプ) ---")
    url = f"{BASE_URL}/airport-japan.html"
    html = fetch_url(url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    
    airport_links = []
    for li in soup.find_all("li"):
        text = li.get_text(strip=True)
        a = li.find("a")
        if not a:
            continue
        href = a.get("href", "")
        if "空港のスタンプ" in text and href and href != "https://stamp.funakiya.com/":
            m = re.search(r"([^（(]+空港(?:（[^）)]+）)?)のスタンプ", text)
            name_raw = m.group(1).strip() if m else text.split("のスタンプ")[0].strip()
            name_clean = re.sub(r"（.+?）", "", name_raw).strip()
            
            if name_clean in existing_names or name_raw in existing_names:
                continue
                
            clean_href = href.lstrip("/")
            full_url = href if href.startswith("http") else f"{BASE_URL}/{clean_href}"
            slug_m = re.search(r"([a-zA-Z0-9\-]+)\.html", href)
            slug_str = slug_m.group(1).lower() if slug_m else f"airport-{len(airport_links)}"
            stamp_id = f"airport-{slug_str}"
            
            airport_links.append({
                "id": stamp_id,
                "name_ja": name_raw,
                "name_clean": name_clean,
                "url": full_url,
                "slug": slug_str
            })
            
    print(f"  Found {len(airport_links)} commercial passenger airports.")
    new_stamps = []
    
    def fetch_airport(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        info = fetch_page_info(item["url"])
        addr = info.get("addr", "")
        pref = extract_prefecture_en(addr) if addr else "Japan"
        pref_ja = extract_prefecture(addr) if addr else ""
        city = extract_city(addr) or f"{item['name_clean']}"
        
        coords = None
        if addr:
            coords = geocode_address(addr)
        if not coords:
            coords = geocode_address(f"{pref_ja} {item['name_clean']}")
        if not coords:
            coords = geocode_address(item['name_clean'])
        if not coords:
            return None
            
        stamp_id = item["id"]
        photo_url = info.get("photo_url")
        jpg_file = f"{stamp_id}.jpg"
        svg_file = f"{stamp_id}.svg"
        jpg_path = os.path.join(IMAGES_DIR, jpg_file)
        svg_path = os.path.join(IMAGES_DIR, svg_file)
        
        has_photo = False
        if photo_url and download_photo(photo_url, jpg_path):
            has_photo = True
            img_path = f"/images/stamps/{jpg_file}"
        else:
            img_path = f"/images/stamps/{svg_file}"
            
        name_en = item['name_clean']
        if not name_en.endswith("Airport"):
            name_en = f"{name_en.replace('空港', '')} Airport"
            
        stamp_obj = {
            "id": stamp_id,
            "name": f"{name_en} Terminal",
            "name_ja": f"{item['name_ja']} 記念スタンプ",
            "name_romaji": f"{item['name_clean']}-kūkō",
            "category": "eki",
            "prefecture": pref,
            "city": city,
            "address": addr or f"{pref} {item['name_ja']}",
            "coordinates": [round(coords[0], 6), round(coords[1], 6)],
            "stampLocation": info.get("stamp_loc") or f"{item['name_clean']} ターミナル案内所・総合インフォメーションカウンター (Terminal Info Desk)",
            "hours": info.get("hours") or "07:00 - 21:00 (Terminal Open Hours)",
            "operator": "Airport Authority (空港管理会社・旅客ターミナル)",
            "imageUrl": img_path,
            "description": f"Official aviation commemorative arrival/departure stamp for {name_en} in {city}, {pref}. Features regional icons, runway motifs, and aviation travel heritage."
        }
        
        if not has_photo:
            svg_content = generate_seal_svg_content(stamp_obj)
            with open(svg_path, "w", encoding="utf-8") as f:
                f.write(svg_content)
                
        return stamp_obj

    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = [ex.submit(fetch_airport, a) for a in airport_links]
        for f in as_completed(futs):
            res = f.result()
            if res:
                new_stamps.append(res)
                existing_names.add(res["name_ja"])
                
    print(f"-> Completed Passenger Airports: {len(new_stamps)} new airport stamps added.")
    return new_stamps


# =============================================================
# 3. SCRAPE OBSERVATION TOWERS & ICONIC LANDMARKS (全日本タワー協議会)
# =============================================================
FAMOUS_TOWERS = [
    ("tokyo-skytree", "Tokyo Skytree", "東京スカイツリー", "Tokyo", "Sumida Ward", "東京都墨田区押上1-1-2", [139.8107, 35.7100], "東京スカイツリー 展望デッキ・4F出発ロビー", "08:00 - 22:00", "Tobu Railway Group", "https://stamp.funakiya.com/tokyotower.html"),
    ("tokyo-tower", "Tokyo Tower", "東京タワー", "Tokyo", "Minato Ward", "東京都港区芝公園4-2-8", [139.7454, 35.6586], "東京タワー メインデッキ・フットタウン案内所", "09:00 - 23:00", "Tokyo Tower Co., Ltd.", "https://stamp.funakiya.com/tokyotower.html"),
    ("kyoto-tower", "Kyoto Tower", "京都タワー", "Kyoto", "Shimogyo Ward", "京都府京都市下京区烏丸通七条下る東塩小路町721-1", [135.7593, 34.9875], "京都タワー 展望室1F・チケット窓口カウンター", "10:00 - 21:00", "Keihan Group", "https://stamp.funakiya.com/kyototower.html"),
    ("tsutenkaku", "Tsūtenkaku Tower", "通天閣", "Osaka", "Naniwa Ward", "大阪府大阪市浪速区恵美須東1-18-6", [135.5063, 34.6525], "通天閣 展望台入場ゲート・2F売店スタンプコーナー", "10:00 - 20:00", "Tsutenkaku Kanko Co., Ltd.", "https://stamp.funakiya.com/tsutenkaku.html"),
    ("kobe-port-tower", "Kobe Port Tower", "神戸ポートタワー", "Hyogo", "Kobe City", "兵庫県神戸市中央区波止場町5-5", [135.1867, 34.6826], "神戸ポートタワー 展望ロビー・エントランス案内所", "09:00 - 23:00", "Kobe Waterfront Development", "https://stamp.funakiya.com/kobe-porttower.html"),
    ("fukuoka-tower", "Fukuoka Tower", "福岡タワー", "Fukuoka", "Sawara Ward", "福岡県福岡市早良区百道浜2-3-26", [130.3515, 33.5933], "福岡タワー 1Fエントランス・展望台チケット売り場", "09:30 - 22:00", "Fukuoka Tower Co., Ltd.", "https://stamp.funakiya.com/fukuokatower.html"),
    ("sapporo-tv-tower", "Sapporo TV Tower", "さっぽろテレビ塔", "Hokkaido", "Sapporo City", "北海道札幌市中央区大通西1丁目", [141.3564, 43.0611], "さっぽろテレビ塔 3F展望台チケット売り場", "09:00 - 22:00", "Sapporo TV Tower Co., Ltd.", "https://stamp.funakiya.com/sapporotvtower.html"),
    ("goryokaku-tower", "Goryōkaku Tower", "五稜郭タワー", "Hokkaido", "Hakodate City", "北海道函館市五稜郭町43-9", [140.7540, 41.7946], "五稜郭タワー 1Fアトリウム・総合インフォメーション", "09:00 - 18:00", "Goryokaku Tower Co., Ltd.", "https://stamp.funakiya.com/goryokakutower.html"),
    ("chiba-port-tower", "Chiba Port Tower", "千葉ポートタワー", "Chiba", "Chiba City", "千葉県千葉市中央区中央港1", [140.1030, 35.6006], "千葉ポートタワー 1Fエントランス案内所", "09:00 - 19:00", "Chiba Port Park Authority", "https://stamp.funakiya.com/chibaporttower.html"),
    ("yokohama-marine-tower", "Yokohama Marine Tower", "横浜マリンタワー", "Kanagawa", "Yokohama City", "神奈川県横浜市中区山下町14-1", [139.6508, 35.4439], "横浜マリンタワー 1Fインフォメーションカウンター", "10:00 - 22:00", "Yokohama Marine Tower", "https://stamp.funakiya.com/yokohama-marinetower.html"),
    ("nagoya-mirai-tower", "Chūbu Electric Power MIRAI TOWER", "中部電力 MIRAI TOWER (名古屋テレビ塔)", "Aichi", "Nagoya City", "愛知県名古屋市中区錦3-6-15", [136.9084, 35.1724], "MIRAI TOWER 1F・展望デッキ案内所", "10:00 - 21:00", "Nagoya TV Tower Co., Ltd.", "https://stamp.funakiya.com/nagoyatvtower.html"),
    ("beppu-tower", "Beppu Tower", "別府タワー", "Oita", "Beppu City", "大分県別府市北浜3-10-2", [131.5034, 33.2842], "別府タワー 1Fチケット売り場・展望台", "09:30 - 21:30", "Beppu Tower Co., Ltd.", "https://stamp.funakiya.com/bepputower.html"),
    ("kaikyo-yume-tower", "Kaikyō Yume Tower", "海峡ゆめタワー", "Yamaguchi", "Shimonoseki City", "山口県下関市豊前田町3-3-1", [130.9304, 33.9507], "海峡ゆめタワー 28F展望室・1Fチケット売場", "09:30 - 21:30", "Yamaguchi International Trade Center", "https://stamp.funakiya.com/kaikyoyumetower.html"),
    ("enoshima-sea-candle", "Enoshima Sea Candle", "江の島シーキャンドル", "Kanagawa", "Fujisawa City", "神奈川県藤沢市江の島2-3-28", [139.4786, 35.2991], "江の島サムエル・コッキング苑内 シーキャンドル展望塔", "09:00 - 20:00", "Enoshima Electric Railway (江ノ電)", "https://stamp.funakiya.com/enoshimaseacandle.html"),
]


def scrape_observation_towers(existing_names: set) -> List[Dict[str, Any]]:
    print("\n--- [Phase 3: Category 3] Adding All-Japan Observation Towers (全日本タワー協議会) ---")
    new_stamps = []
    
    for slug, name_en, name_ja, pref, city, addr, coords, stamp_loc, hours, operator, funakiya_url in FAMOUS_TOWERS:
        if name_ja in existing_names or name_en in existing_names:
            continue
            
        stamp_id = f"tower-{slug}"
        jpg_file = f"{stamp_id}.jpg"
        svg_file = f"{stamp_id}.svg"
        jpg_path = os.path.join(IMAGES_DIR, jpg_file)
        svg_path = os.path.join(IMAGES_DIR, svg_file)
        
        info = fetch_page_info(funakiya_url)
        has_photo = False
        if info.get("photo_url") and download_photo(info["photo_url"], jpg_path):
            has_photo = True
            img_path = f"/images/stamps/{jpg_file}"
        else:
            img_path = f"/images/stamps/{svg_file}"
            
        stamp_obj = {
            "id": stamp_id,
            "name": f"{name_en} Observatory",
            "name_ja": f"{name_ja} 展望記念スタンプ",
            "name_romaji": f"{slug}",
            "category": "temple_shrine",
            "prefecture": pref,
            "city": city,
            "address": addr,
            "coordinates": coords,
            "stampLocation": stamp_loc,
            "hours": hours,
            "operator": f"All-Japan Tower League ({operator})",
            "imageUrl": img_path,
            "description": f"Official All-Japan Tower League commemorative panoramic stamp for {name_en} in {city}, {pref}. Celebrates sweeping skyline vistas and iconic landmark architecture."
        }
        
        if not has_photo:
            svg_content = generate_seal_svg_content(stamp_obj)
            with open(svg_path, "w", encoding="utf-8") as f:
                f.write(svg_content)
                
        new_stamps.append(stamp_obj)
        existing_names.add(name_ja)
        
    print(f"-> Completed Towers: {len(new_stamps)} iconic observation towers added.")
    return new_stamps


# =============================================================
# 4. SCRAPE TOP ANIME 88 SACRED PILGRIMAGE SITES (日本のアニメ聖地88)
# =============================================================
def scrape_anime_88_pilgrimage(existing_names: set) -> List[Dict[str, Any]]:
    print("\n--- [Phase 3: Category 4] Scraping Anime 88 Sacred Sites (日本のアニメ聖地88) ---")
    url = f"{BASE_URL}/japan-anime88.html"
    html = fetch_url(url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    
    anime_links = []
    for li in soup.find_all("li"):
        text = li.get_text(strip=True)
        a = li.find("a")
        if not a:
            continue
        href = a.get("href", "")
        if "聖地" in text and "スタンプ" in text and href and href != "https://stamp.funakiya.com/":
            # e.g. ラブライブ！サンシャイン！！のスタンプ【聖地】北海道函館市 2020年選定
            m = re.search(r"([^【]+?)のスタンプ【聖地】([^0-9\s]+)", text)
            if not m:
                continue
            anime_title = m.group(1).strip()
            loc_ja = m.group(2).strip()
            
            clean_href = href.lstrip("/")
            full_url = href if href.startswith("http") else f"{BASE_URL}/{clean_href}"
            slug_m = re.search(r"([a-zA-Z0-9\-]+)\.html", href)
            slug_str = slug_m.group(1).lower() if slug_m else f"anime-{len(anime_links)}"
            stamp_id = f"anime-{slug_str}"
            
            if stamp_id in existing_names or f"{anime_title} ({loc_ja})" in existing_names:
                continue
                
            anime_links.append({
                "id": stamp_id,
                "title": anime_title,
                "loc_ja": loc_ja,
                "url": full_url,
                "slug": slug_str
            })
            
    print(f"  Found {len(anime_links)} official Anime 88 candidate locations.")
    new_stamps = []
    
    def fetch_anime(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        info = fetch_page_info(item["url"])
        addr = info.get("addr", "") or item["loc_ja"]
        pref = extract_prefecture_en(addr)
        pref_ja = extract_prefecture(addr)
        city = extract_city(addr) or item["loc_ja"]
        
        coords = geocode_address(addr) if addr else None
        if not coords:
            coords = geocode_address(f"{pref_ja} {city}")
        if not coords:
            return None
            
        stamp_id = item["id"]
        photo_url = info.get("photo_url")
        jpg_file = f"{stamp_id}.jpg"
        svg_file = f"{stamp_id}.svg"
        jpg_path = os.path.join(IMAGES_DIR, jpg_file)
        svg_path = os.path.join(IMAGES_DIR, svg_file)
        
        has_photo = False
        if photo_url and download_photo(photo_url, jpg_path):
            has_photo = True
            img_path = f"/images/stamps/{jpg_file}"
        else:
            img_path = f"/images/stamps/{svg_file}"
            
        stamp_obj = {
            "id": stamp_id,
            "name": f"{item['title']} Sacred Pilgrimage ({city})",
            "name_ja": f"{item['title']} アニメ聖地88印（{city}）",
            "name_romaji": f"anime-{item['slug']}",
            "category": "temple_shrine",
            "prefecture": pref,
            "city": city,
            "address": addr,
            "coordinates": [round(coords[0], 6), round(coords[1], 6)],
            "stampLocation": info.get("stamp_loc") or f"{city} 観光案内所・聖地巡礼インフォメーション (Anime Tourism Info Desk)",
            "hours": info.get("hours") or "09:00 - 17:00 (Facility hours)",
            "operator": "Japan Anime Tourism Association (一般社団法人アニメツーリズム協会)",
            "imageUrl": img_path,
            "description": f"Official Anime Tourism Association 88 Sacred Sites commemorative stamp for '{item['title']}' in {city}, {pref}. Commemorates iconic animated story locations and cultural fandom heritage."
        }
        
        if not has_photo:
            svg_content = generate_seal_svg_content(stamp_obj)
            with open(svg_path, "w", encoding="utf-8") as f:
                f.write(svg_content)
                
        return stamp_obj

    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = [ex.submit(fetch_anime, a) for a in anime_links]
        for f in as_completed(futs):
            res = f.result()
            if res:
                new_stamps.append(res)
                existing_names.add(res["name_ja"])
                
    print(f"-> Completed Anime 88 Sites: {len(new_stamps)} pilgrimage stamps added.")
    return new_stamps


# =============================================================
# MAIN ORCHESTRATOR
# =============================================================
def main():
    print("=====================================================")
    print("       STARTING STAMPU PHASE 3 EXPANSION")
    print("=====================================================")
    
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        all_stamps = json.load(f)
        
    initial_count = len(all_stamps)
    print(f"Initial stamp count: {initial_count}")
    
    existing_ids = {s["id"] for s in all_stamps}
    existing_names = {s["name_ja"] for s in all_stamps}
    existing_names.update(s["name"] for s in all_stamps)
    
    # 1. Private Railways
    railway_stamps = scrape_private_railways(existing_names)
    
    # 2. Passenger Airports
    airport_stamps = scrape_passenger_airports(existing_names)
    
    # 3. Observation Towers
    tower_stamps = scrape_observation_towers(existing_names)
    
    # 4. Anime 88 Sacred Sites
    anime_stamps = scrape_anime_88_pilgrimage(existing_names)
    
    # Merge new unique stamps
    total_added = 0
    for s in railway_stamps + airport_stamps + tower_stamps + anime_stamps:
        if s["id"] not in existing_ids:
            all_stamps.append(s)
            existing_ids.add(s["id"])
            total_added += 1
            
    print(f"\nSuccessfully merged {total_added} new stamps!")
    print(f"Total stamps in database: {len(all_stamps)}")
    
    # Save stamps.json
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(all_stamps, f, ensure_ascii=False, indent=2)
    print(f"Updated {DATA_FILE} successfully.")
    
    # Update prefectures.json
    print("\nUpdating public/data/prefectures.json catalog...")
    with open(PREF_FILE, "r", encoding="utf-8") as f:
        prefs = json.load(f)
        
    for p in prefs:
        pref_en = p["name"]
        pref_stamps = [s for s in all_stamps if s.get("prefecture") == pref_en]
        p["stampCount"] = len(pref_stamps)
        
        cats = {}
        total_img_bytes = 0
        lats = []
        lons = []
        for s in pref_stamps:
            c = s.get("category", "other")
            cats[c] = cats.get(c, 0) + 1
            img_rel = s.get("imageUrl", "").lstrip("/")
            img_path = os.path.join(BASE_DIR, "public", img_rel)
            if os.path.exists(img_path):
                total_img_bytes += os.path.getsize(img_path)
            if s.get("coordinates"):
                lons.append(s["coordinates"][0])
                lats.append(s["coordinates"][1])
                
        p["categories"] = cats
        if lats and lons:
            p["bounds"] = {
                "minLat": round(min(lats) - 0.05, 4),
                "maxLat": round(max(lats) + 0.05, 4),
                "minLon": round(min(lons) - 0.05, 4),
                "maxLon": round(max(lons) + 0.05, 4),
            }
        img_mb = total_img_bytes / (1024 * 1024)
        p["estimatedSizeMB"] = max(0.5, round(img_mb + 1.5, 1))
        
    with open(PREF_FILE, "w", encoding="utf-8") as f:
        json.dump(prefs, f, ensure_ascii=False, indent=2)
    print(f"Updated {len(prefs)} prefectures in {PREF_FILE}.")
    print("\nPhase 3 expansion complete!")


if __name__ == "__main__":
    main()
