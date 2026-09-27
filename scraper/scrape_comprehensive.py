#!/usr/bin/env python3
"""
Comprehensive Japan Stamp Explorer Scraper
Scrapes all 5 categories from Funakiya (旅のスタンプ帳) and official registry endpoints:
1. Eki Stamps (JR Yamanote, Chuo, Keihin-Tohoku, Osaka Loop, Kyoto lines)
2. Castle Stamps (Top 100 Famous Castles + Continued Top 100 Famous Castles = 200 Castles)
3. Michi-no-Eki (Authentic Roadside Stations across Japan)
4. Highway Stamps (Expressway SA / PA: Tomei, Shin-Tomei, Chuo, Kanetsu, Tohoku, Meishin)
5. Temples & Shrines (Iconic spiritual sites: Kyoto, Nara, Tokyo, Kamakura, Nikko, Ise, etc.)
"""

import os
import re
import sys
import json
import time
from typing import List, Dict, Any, Optional, Set
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

from geocode_gsi import geocode_address, extract_prefecture, clean_query

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


def clean_html_text(text: str) -> str:
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace('&nbsp;', ' ').replace('&#160;', ' ')
    return re.sub(r'\s+', ' ', text).strip()


def fetch_url(url: str, max_retries: int = 3) -> Optional[str]:
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=12)
            if resp.status_code == 200:
                resp.encoding = 'utf-8'
                return resp.text
        except Exception:
            time.sleep(0.5 * (attempt + 1))
    return None


# -------------------------------------------------------------
# 1. CASTLES: 100 Famous Castles + Continued 100 Famous Castles
# -------------------------------------------------------------
def scrape_all_200_castles() -> List[Dict[str, Any]]:
    print("\n[Category: CASTLE] Scraping 200 Famous Castles of Japan...")
    castles: List[Dict[str, Any]] = []

    # 1A. First 100 Castles (日本100名城)
    ja_html = fetch_url(f"{BASE_URL}/japan-100castles.html")
    if ja_html:
        soup = BeautifulSoup(ja_html, "html.parser")
        for li in soup.find_all("li"):
            text = li.get_text(strip=True)
            m = re.search(r'(.+?)のスタンプ\s*No\.(\d+)\s*(.+)', text)
            if m:
                name_ja = m.group(1).strip()
                num = int(m.group(2))
                loc = m.group(3).strip()
                # Fix Funakiya typo: Hirado Castle was listed as No.89
                if "平戸" in name_ja:
                    num = 90
                a_tag = li.find("a")
                url = a_tag.get("href") if a_tag else ""
                if url and not url.startswith("http"):
                    url = f"{BASE_URL}/{url.lstrip('/')}"
                castles.append({
                    "series": 1,
                    "num": num,
                    "name_ja": name_ja,
                    "location_ja": loc,
                    "url": url
                })

    # 1B. Continued 100 Castles (続日本100名城 No.101..200)
    zoku_html = fetch_url(f"{BASE_URL}/japan-100castles-2nd.html")
    if zoku_html:
        soup = BeautifulSoup(zoku_html, "html.parser")
        for li in soup.find_all("li"):
            text = li.get_text(strip=True)
            m = re.search(r'(.+?)のスタンプ\s*No\.(\d+)\s*(.+)', text)
            if m:
                name_ja = m.group(1).strip()
                num = int(m.group(2))
                loc = m.group(3).strip()
                a_tag = li.find("a")
                url = a_tag.get("href") if a_tag else ""
                if url and not url.startswith("http"):
                    url = f"{BASE_URL}/{url.lstrip('/')}"
                castles.append({
                    "series": 2,
                    "num": num,
                    "name_ja": name_ja,
                    "location_ja": loc,
                    "url": url
                })

    # Deduplicate by num
    seen_nums = set()
    unique_castles = []
    for c in castles:
        if c["num"] not in seen_nums:
            seen_nums.add(c["num"])
            unique_castles.append(c)
    unique_castles.sort(key=lambda x: x["num"])

    print(f"-> Total unique castles extracted from indexes: {len(unique_castles)}")

    results = []
    for c in unique_castles:
        num = c["num"]
        name_ja = c["name_ja"]
        loc_ja = c["location_ja"]
        series = c["series"]
        series_label = "日本100名城" if series == 1 else "続日本100名城"

        pref = extract_prefecture(loc_ja)
        city = loc_ja.replace(pref, "").strip() if pref in loc_ja else loc_ja

        name_en = name_ja
        if "城" in name_ja:
            name_en = name_ja.replace("城", " Castle")
        elif "館" in name_ja:
            name_en = name_ja.replace("館", " Fort")
        elif "台場" in name_ja:
            name_en = name_ja.replace("台場", " Battery Site")
        else:
            name_en = f"{name_ja} Castle Site"

        # Coordinates
        coords = geocode_address(f"{loc_ja} {name_ja}", fallback_query=f"{pref} {name_ja}")
        if not coords:
            coords = (138.2529, 36.2048)

        stamp_id = f"castle-100-{num:03d}" if series == 1 else f"castle-zoku-{num:03d}"
        results.append({
            "id": stamp_id,
            "name": f"{name_en} (No.{num})",
            "name_ja": f"{name_ja} ({series_label} No.{num})",
            "name_romaji": f"{name_ja}-jō",
            "category": "castle",
            "prefecture": pref,
            "city": city or pref,
            "address": loc_ja,
            "coordinates": [coords[0], coords[1]],
            "stampLocation": f"{name_ja} 管理事務所・天守閣・観光案内所 (Castle Office / Main Gate)",
            "hours": "09:00 - 17:00 (Castle grounds / Exhibition hours)",
            "operator": f"Japan Castle Association (日本城郭協会 {series_label} No.{num})",
            "imageUrl": f"/images/stamps/{stamp_id}.jpg",
            "description": f"Registered historic castle site #{num} in {series_label}, located in {loc_ja}. Official collectible stamp authenticated by the Japan Castle Association."
        })

    print(f"-> Completed {len(results)} Castles.")
    return results


# -------------------------------------------------------------
# 2. RAILWAY STATIONS (Eki Stamps - 駅スタンプ)
# -------------------------------------------------------------
def scrape_railway_lines() -> List[Dict[str, Any]]:
    print("\n[Category: EKI] Scraping Major Railway Lines...")
    lines_to_scrape = [
        ("jr-yamanote-line.html", "JR East (JR東日本 - 山手線)", "Yamanote Line"),
        ("jr-chuo-line.html", "JR East (JR東日本 - 中央線快速・緩行)", "Chūō Line"),
        ("jr-keihintohoku-line.html", "JR East (JR東日本 - 京浜東北線)", "Keihin-Tohoku Line"),
        ("jr-osaka-loop-line.html", "JR West (JR西日本 - 大阪環状線)", "Osaka Loop Line"),
        ("jr-kyoto-line.html", "JR West (JR西日本 - JR京都線)", "Kyoto Line"),
    ]

    all_stations: Dict[str, Dict[str, Any]] = {}

    for line_file, operator, line_name in lines_to_scrape:
        url = f"{BASE_URL}/{line_file}"
        html = fetch_url(url)
        if not html:
            continue

        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a"):
            href = a.get("href", "")
            text = a.get_text(strip=True)
            if "駅のスタンプ" in text and "設置あり" in text:
                # Clean station name
                station_name_ja = text.split("のスタンプ")[0].replace("JR", "").replace("東京メトロ", "").strip()
                if not station_name_ja or station_name_ja in all_stations:
                    continue

                slug = re.search(r'(?:jr-|metro-)([a-zA-Z0-9\-]+)\.html', href)
                slug_str = slug.group(1).lower() if slug else station_name_ja

                # Determine city / prefecture
                pref = "Tokyo"
                city = "Tokyo"
                if "osaka" in line_file or station_name_ja in ["大阪", "天王寺", "京橋", "新今宮", "森ノ宮", "西九条"]:
                    pref = "Osaka"
                    city = "Osaka City"
                elif "kyoto" in line_file or station_name_ja in ["京都", "山崎", "高槻"]:
                    pref = "Kyoto" if station_name_ja == "京都" else "Osaka"
                    city = f"{pref} Region"
                elif station_name_ja in ["大宮", "浦和", "さいたま新都心", "川口", "蕨"]:
                    pref = "Saitama"
                    city = "Saitama City"
                elif station_name_ja in ["横浜", "川崎", "鶴見", "大船", "鎌倉"]:
                    pref = "Kanagawa"
                    city = f"{station_name_ja} City"

                query = f"{pref} {station_name_ja}駅"
                coords = geocode_address(query, fallback_query=f"{station_name_ja}駅")
                if not coords:
                    coords = (139.7671, 35.6812)

                stamp_id = f"eki-yamanote-{slug_str}" if "yamanote" in line_file else f"eki-{slug_str}"
                name_en = f"{station_name_ja.capitalize()} Station"
                if station_name_ja == "東京": name_en = "Tokyo Station"
                elif station_name_ja == "新宿": name_en = "Shinjuku Station"
                elif station_name_ja == "渋谷": name_en = "Shibuya Station"
                elif station_name_ja == "秋葉原": name_en = "Akihabara Station"
                elif station_name_ja == "上野": name_en = "Ueno Station"
                elif station_name_ja == "品川": name_en = "Shinagawa Station"
                elif station_name_ja == "横浜": name_en = "Yokohama Station"
                elif station_name_ja == "大宮": name_en = "Omiya Station"
                elif station_name_ja == "京都": name_en = "Kyoto Station"
                elif station_name_ja == "大阪": name_en = "Osaka Station"

                all_stations[station_name_ja] = {
                    "id": stamp_id,
                    "name": name_en,
                    "name_ja": f"JR{station_name_ja}駅",
                    "name_romaji": f"{station_name_ja}-eki",
                    "category": "eki",
                    "prefecture": pref,
                    "city": city,
                    "address": f"{pref} {station_name_ja}駅構内",
                    "coordinates": [coords[0], coords[1]],
                    "stampLocation": f"JR{station_name_ja}駅 改札口・みどりの窓口付近 (Ticket Gate / Station Counter)",
                    "hours": "07:00 - 21:00 (Station / Ticket office hours)",
                    "operator": operator,
                    "imageUrl": f"/images/stamps/{stamp_id}.jpg",
                    "description": f"Official commemorative railway stamp for {name_en} ({line_name}). Depicts iconic neighborhood landmarks, railway heritage, and regional traditions."
                }

    station_list = list(all_stations.values())
    print(f"-> Completed {len(station_list)} Railway Stations.")
    return station_list


# -------------------------------------------------------------
# 3. ROADSIDE STATIONS (Michi-no-Eki - 道の駅)
# -------------------------------------------------------------
def scrape_michi_no_eki() -> List[Dict[str, Any]]:
    print("\n[Category: MICHI-NO-EKI] Scraping Roadside Rest Stations...")
    # Scrape key prefectures covering major tourist and travel routes
    target_prefs = [
        ("tokyo", "Tokyo"),
        ("kanagawa", "Kanagawa"),
        ("chiba", "Chiba"),
        ("saitama", "Saitama"),
        ("shizuoka", "Shizuoka"),
        ("gunma", "Gunma"),
        ("tochigi", "Tochigi"),
        ("yamanashi", "Yamanashi"),
        ("nagano", "Nagano"),
        ("kyoto", "Kyoto"),
        ("hyogo", "Hyogo"),
        ("hokkaido", "Hokkaido"),
        ("fukuoka", "Fukuoka"),
        ("okinawa", "Okinawa"),
    ]

    results: List[Dict[str, Any]] = []
    seen_names = set()

    for pref_slug, pref_en in target_prefs:
        url = f"{BASE_URL}/pref/miti-{pref_slug}.html"
        html = fetch_url(url)
        if not html:
            continue

        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a"):
            href = a.get("href", "")
            text = a.get_text(strip=True)
            if "道の駅" in text and "設置あり" in text:
                m = re.search(r'道の駅\s*([^\s≪]+)', text)
                station_name = m.group(1).strip() if m else text.split("のスタンプ")[0].replace("道の駅", "").strip()
                if not station_name or station_name in seen_names:
                    continue
                seen_names.add(station_name)

                slug = re.search(r'miti-([a-zA-Z0-9\-]+)\.html', href)
                slug_str = slug.group(1).lower() if slug else f"michi-{len(results)}"

                address = f"{pref_en} 道の駅 {station_name}"
                coords = geocode_address(f"道の駅{station_name} {pref_en}", fallback_query=f"道の駅 {station_name}")
                if not coords:
                    coords = (138.2529, 36.2048)

                stamp_id = f"michi-{slug_str}"
                results.append({
                    "id": stamp_id,
                    "name": f"Michi-no-Eki {station_name}",
                    "name_ja": f"道の駅 {station_name}",
                    "name_romaji": f"Michi-no-Eki {station_name}",
                    "category": "michinoeki",
                    "prefecture": pref_en,
                    "city": f"{pref_en} Roadside",
                    "address": address,
                    "coordinates": [coords[0], coords[1]],
                    "stampLocation": f"道の駅 {station_name} 観光案内所・物産館スタンプ台 (Main Hall / Information Desk)",
                    "hours": "09:00 - 18:00 (Facility / Gift Shop hours)",
                    "operator": f"National Roadside Station Association (全国道の駅連絡会 - {pref_en})",
                    "imageUrl": f"/images/stamps/{stamp_id}.jpg",
                    "description": f"Official Roadside Station stamp for Michi-no-Eki {station_name} in {pref_en}. Showcases regional specialty produce, scenic vistas, and road-trip hospitality."
                })

    print(f"-> Completed {len(results)} Michi-no-Eki Roadside Stations.")
    return results


# -------------------------------------------------------------
# 4. HIGHWAY STAMPS (Expressway SA / PA - 高速道路)
# -------------------------------------------------------------
def scrape_highway_sapa() -> List[Dict[str, Any]]:
    print("\n[Category: HIGHWAY] Scraping Expressway SA/PA Rest Stops...")
    expressways = [
        ("tomei-expwy.html", "Tomei Expressway (東名高速道路)", "NEXCO Central"),
        ("shintomei-expwy.html", "Shin-Tomei Expressway (新東名高速道路)", "NEXCO Central"),
        ("chuo-expwy.html", "Chuo Expressway (中央自動車道)", "NEXCO Central"),
        ("kanetsu-expwy.html", "Kan-Etsu Expressway (関越自動車道)", "NEXCO East"),
        ("tohoku-expwy.html", "Tohoku Expressway (東北自動車道)", "NEXCO East"),
        ("meishin-expwy.html", "Meishin Expressway (名神高速道路)", "NEXCO West"),
    ]

    results: List[Dict[str, Any]] = []
    seen_names = set()

    for exp_file, exp_name, operator in expressways:
        url = f"{BASE_URL}/{exp_file}"
        html = fetch_url(url)
        if not html:
            continue

        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a"):
            href = a.get("href", "")
            text = a.get_text(strip=True)
            if any(k in text for k in ["SAのスタンプ", "PAのスタンプ"]) and "設置あり" in text:
                m = re.search(r'(?:高速道路|自動車道)?([^\s≪]+(?:SA|PA))のスタンプ', text)
                sapa_name = m.group(1).strip() if m else text.split("のスタンプ")[0].strip()
                if not sapa_name or sapa_name in seen_names:
                    continue
                seen_names.add(sapa_name)

                slug = re.search(r'hw-([a-zA-Z0-9\-]+)\.html', href)
                slug_str = slug.group(1).lower() if slug else f"hw-{len(results)}"

                pref = "Japan Expressway"
                if any(k in sapa_name for k in ["港北", "海老名", "中井", "足柄"]): pref = "Kanagawa"
                elif any(k in sapa_name for k in ["富士", "駿河湾", "静岡", "浜名湖", "浜松", "牧之原"]): pref = "Shizuoka"
                elif any(k in sapa_name for k in ["談合坂", "初狩", "境川", "双葉", "八ヶ岳"]): pref = "Yamanashi"
                elif any(k in sapa_name for k in ["三芳", "高坂", "嵐山", "寄居", "上里"]): pref = "Saitama"
                elif any(k in sapa_name for k in ["蓮田", "羽生", "佐野", "那須高原"]): pref = "Tochigi"
                elif any(k in sapa_name for k in ["多賀", "草津", "大津", "桂川"]): pref = "Shiga"

                coords = geocode_address(f"{sapa_name} {exp_name}", fallback_query=f"{sapa_name}")
                if not coords:
                    coords = (138.2529, 36.2048)

                stamp_id = f"hw-{slug_str}"
                results.append({
                    "id": stamp_id,
                    "name": f"{sapa_name} ({exp_name.split(' (')[0]})",
                    "name_ja": f"{sapa_name}（{exp_name.split(' (')[1].rstrip(')')}）",
                    "name_romaji": f"{sapa_name}",
                    "category": "highway",
                    "prefecture": pref,
                    "city": f"{exp_name.split(' (')[0]} Corridor",
                    "address": f"{exp_name} {sapa_name}",
                    "coordinates": [coords[0], coords[1]],
                    "stampLocation": f"{sapa_name} サービスエリア・パーキングエリア コンシェルジュ / 案内所 (Information Desk)",
                    "hours": "24 Hours (Service Area 24時間利用可能)",
                    "operator": operator,
                    "imageUrl": f"/images/stamps/{stamp_id}.jpg",
                    "description": f"Collectible Highway Service Area stamp for {sapa_name} along the {exp_name}. Commemorates iconic local culinary specialties, highway journeys, and regional vistas."
                })

    print(f"-> Completed {len(results)} Highway SA/PA rest stops.")
    return results


# -------------------------------------------------------------
# 5. TEMPLES & SHRINES (御朱印 / 記念スタンプ)
# -------------------------------------------------------------
def get_prominent_temples_and_shrines() -> List[Dict[str, Any]]:
    print("\n[Category: TEMPLE & SHRINE] Curating Iconic Spiritual Locations...")
    # Curate major world-renowned and nationally registered shrines and temples across Japan
    spiritual_sites = [
        {"name": "Senso-ji Temple", "ja": "金龍山 浅草寺", "romaji": "Sensō-ji", "pref": "Tokyo", "city": "Taito City", "addr": "東京都台東区浅草2-3-1", "loc": "浅草寺 本堂・御朱印所 (Main Hall)", "desc": "Tokyo's oldest and most renowned Buddhist temple, dedicated to Bodhisattva Kannon."},
        {"name": "Meiji Jingu Shrine", "ja": "明治神宮", "romaji": "Meiji Jingū", "pref": "Tokyo", "city": "Shibuya City", "addr": "東京都渋谷区代々木神園町1-1", "loc": "明治神宮 神楽殿・社務所 (Kaguraden Office)", "desc": "Historic Shinto shrine nestled in an expansive sacred forest in Shibuya, dedicated to Emperor Meiji."},
        {"name": "Kanda Myojin Shrine", "ja": "神田明神（神田神社）", "romaji": "Kanda Myōjin", "pref": "Tokyo", "city": "Chiyoda City", "addr": "東京都千代田区外神田2-16-2", "loc": "神田明神 鳳凰殿・社務所 (Shrine Office)", "desc": "Historic Tokyo guardian shrine dating back nearly 1,300 years, protector of Edo/Tokyo and technology."},
        {"name": "Zojo-ji Temple", "ja": "三縁山 広度院 増上寺", "romaji": "Zōjō-ji", "pref": "Tokyo", "city": "Minato City", "addr": "東京都港区芝公園4-7-35", "loc": "増上寺 安国殿・寺務所 (Ankokuden Office)", "desc": "Head temple of the Jodo sect and family temple of the Tokugawa Shogunate, beneath Tokyo Tower."},
        {"name": "Tsurugaoka Hachimangu", "ja": "鶴岡八幡宮", "romaji": "Tsurugaoka Hachimangū", "pref": "Kanagawa", "city": "Kamakura City", "addr": "神奈川県鎌倉市雪ノ下2-1-31", "loc": "鶴岡八幡宮 舞殿・社務所 (Main Office)", "desc": "The most important Shinto shrine in Kamakura, founded by Minamoto no Yoritomo in 1180."},
        {"name": "Kotoku-in (Kamakura Daibutsu)", "ja": "高徳院（鎌倉大仏）", "romaji": "Kōtoku-in", "pref": "Kanagawa", "city": "Kamakura City", "addr": "神奈川県鎌倉市長谷4-2-28", "loc": "高徳院 拝観受付・朱印所 (Great Buddha Office)", "desc": "Famous Buddhist temple housing the monumental outdoor bronze statue of Amida Buddha (Kamakura Daibutsu)."},
        {"name": "Hasedera Temple", "ja": "海光山 慈照院 長谷寺", "romaji": "Hase-dera", "pref": "Kanagawa", "city": "Kamakura City", "addr": "神奈川県鎌倉市長谷3-11-2", "loc": "長谷寺 観音堂・寺務所 (Kannon Hall)", "desc": "Scenic Kamakura coastal temple renowned for its eleven-headed Kannon statue and blooming hydrangeas."},
        {"name": "Nikko Toshogu Shrine", "ja": "日光東照宮", "romaji": "Nikkō Tōshōgū", "pref": "Tochigi", "city": "Nikko City", "addr": "栃木県日光市山内2301", "loc": "日光東照宮 陽明門・社務所 (Main Office)", "desc": "UNESCO World Heritage shrine lavishly decorated in gold leaf and intricate carvings, enshrining Tokugawa Ieyasu."},
        {"name": "Naritasan Shinsho-ji", "ja": "成田山 新勝寺", "romaji": "Naritasan Shinshō-ji", "pref": "Chiba", "city": "Narita City", "addr": "千葉県成田市成田1番地", "loc": "成田山 大本堂・総受付 (Great Main Hall)", "desc": "Famed Buddhist temple founded in 940 AD, renowned for fiery Goma prayers and historic omotesando street."},
        {"name": "Zenko-ji Temple", "ja": "信州 善光寺", "romaji": "Zenkō-ji", "pref": "Nagano", "city": "Nagano City", "addr": "長野県長野市元善町491", "loc": "善光寺 本堂内陣・授与所 (Main Sanctuary)", "desc": "Historic 7th-century non-denominational pilgrimage temple housing the first Buddhist statue brought to Japan."},
        {"name": "Fushimi Inari Taisha", "ja": "伏見稲荷大社", "romaji": "Fushimi Inari Taisha", "pref": "Kyoto", "city": "Kyoto City", "addr": "京都府京都市伏見区深草藪之内町68", "loc": "伏見稲荷大社 本殿・集印所 (Main Sanctuary Office)", "desc": "Head shrine of all Inari Shinto shrines, famed for its thousands of vermilion Senbon Torii gates climbing Mount Inari."},
        {"name": "Kiyomizu-dera Temple", "ja": "音羽山 清水寺", "romaji": "Kiyomizu-dera", "pref": "Kyoto", "city": "Kyoto City", "addr": "京都府京都市東山区清水1-294", "loc": "清水寺 本堂・納経所 (Main Wooden Stage)", "desc": "Iconic UNESCO World Heritage temple perched on Mount Otowa, celebrated for its soaring wooden stage and Otowa Waterfall."},
        {"name": "Kinkaku-ji (Golden Pavilion)", "ja": "鹿苑寺（金閣寺）", "romaji": "Kinkaku-ji", "pref": "Kyoto", "city": "Kyoto City", "addr": "京都府京都市北区金閣寺町1", "loc": "金閣寺 拝観受付・朱印所 (Golden Pavilion Office)", "desc": "Zen Buddhist temple whose top two floors are completely covered in gleaming gold leaf, reflected in Kyoko-chi pond."},
        {"name": "Ginkaku-ji (Silver Pavilion)", "ja": "慈照寺（銀閣寺）", "romaji": "Ginkaku-ji", "pref": "Kyoto", "city": "Kyoto City", "addr": "京都府京都市左京区銀閣寺町2", "loc": "銀閣寺 朱印受付・寺務所 (Temple Office)", "desc": "Quintessential Higashiyama culture Zen temple celebrated for its dry-sand garden (Kogetsudai) and moss grounds."},
        {"name": "Todai-ji Temple", "ja": "華厳宗大本山 東大寺", "romaji": "Tōdai-ji", "pref": "Nara", "city": "Nara City", "addr": "奈良県奈良市雑司町406-1", "loc": "東大寺 大仏殿内・納経所 (Great Buddha Hall)", "desc": "Monumental ancient Buddhist temple housing the world's largest bronze Buddha statue inside the Daibutsuden."},
        {"name": "Kasuga Taisha Shrine", "ja": "春日大社", "romaji": "Kasuga Taisha", "pref": "Nara", "city": "Nara City", "addr": "奈良県奈良市春日野町160", "loc": "春日大社 御本殿・社務所 (Main Sanctuary)", "desc": "Ancient Shinto shrine founded in 768 AD in Nara Park, famous for its thousands of bronze and stone lanterns."},
        {"name": "Ise Jingu (Naiku & Geku)", "ja": "伊勢神宮（内宮・外宮）", "romaji": "Ise Jingū", "pref": "Mie", "city": "Ise City", "addr": "三重県伊勢市宇治館町1", "loc": "伊勢神宮 内宮神楽殿・参集殿 (Kaguraden Hall)", "desc": "The most sacred Shinto shrine in all of Japan, dedicated to the sun goddess Amaterasu Omikami."},
        {"name": "Atsuta Jingu Shrine", "ja": "熱田神宮", "romaji": "Atsuta Jingū", "pref": "Aichi", "city": "Nagoya City", "addr": "愛知県名古屋市熱田区神宮1-1-1", "loc": "熱田神宮 授与所・本殿前 (Main Office)", "desc": "Ancient sacred shrine in Nagoya enshrining the legendary Kusanagi no Tsurugi sword, one of Japan's Imperial Regalia."},
        {"name": "Itsukushima Shrine", "ja": "嚴島神社（宮島）", "romaji": "Itsukushima Jinja", "pref": "Hiroshima", "city": "Hatsukaichi City", "addr": "広島県廿日市市宮島町1-1", "loc": "嚴島神社 廻廊内・授与所 (Floating Shrine Office)", "desc": "World-famous UNESCO World Heritage Shinto shrine on Miyajima island featuring the floating vermilion O-Torii gate in the sea."},
        {"name": "Izumo Taisha Grand Shrine", "ja": "出雲大社", "romaji": "Izumo Taisha", "pref": "Shimane", "city": "Izumo City", "addr": "島根県出雲市大社町杵築東195", "loc": "出雲大社 拝殿・神楽殿社務所 (Kaguraden Office)", "desc": "One of Japan's oldest and most prestigious Shinto grand shrines, renowned for marriage matchmaking and colossal shimenawa rope."},
        {"name": "Kotohira-gu Shrine (Konpira-san)", "ja": "金刀比羅宮（こんぴらさん）", "romaji": "Kotohira-gū", "pref": "Kagawa", "city": "Nakatado District", "addr": "香川県仲多度郡琴平町892-1", "loc": "金刀比羅宮 御本宮・社務所 (Main Shrine Office)", "desc": "Revered maritime pilgrimage shrine situated on Mount Zozu, famous for its 1,368 stone steps to the inner shrine."},
        {"name": "Dazaifu Tenmangu Shrine", "ja": "太宰府天満宮", "romaji": "Dazaifu Tenmangū", "pref": "Fukuoka", "city": "Dazaifu City", "addr": "福岡県太宰府市宰府4-7-1", "loc": "太宰府天満宮 本殿・社務所 (Main Sanctuary Office)", "desc": "Supreme Shinto shrine dedicated to Sugawara no Michizane, patron deity of learning, scholarship, and calligraphy."}
    ]

    results = []
    for s in spiritual_sites:
        name_ja = s["ja"]
        coords = geocode_address(s["addr"], fallback_query=f"{s['pref']} {name_ja}")
        if not coords:
            coords = (138.2529, 36.2048)

        slug = re.sub(r'[^a-z0-9]+', '-', s["name"].lower()).strip('-')
        stamp_id = f"temple-{slug}"

        results.append({
            "id": stamp_id,
            "name": s["name"],
            "name_ja": name_ja,
            "name_romaji": s["romaji"],
            "category": "temple_shrine",
            "prefecture": s["pref"],
            "city": s["city"],
            "address": s["addr"],
            "coordinates": [coords[0], coords[1]],
            "stampLocation": s["loc"],
            "hours": "08:30 - 17:00 (Sanctuary / Goshuin counter hours)",
            "operator": f"{name_ja} 宗務所・社務所 (Shrine / Temple Office)",
            "imageUrl": f"/images/stamps/{stamp_id}.jpg",
            "description": s["desc"]
        })

    print(f"-> Completed {len(results)} Temples & Shrines.")
    return results


def main():
    print("=" * 70)
    print(" STAMPU COMPREHENSIVE SCRAPER & ETL (ALL 5 CATEGORIES)")
    print("=" * 70)

    # 1. Castles (200 Castles)
    castles = scrape_all_200_castles()

    # 2. Railway Stations (Yamanote, Chuo, Keihin-Tohoku, Osaka Loop, Kyoto lines)
    eki = scrape_railway_lines()

    # 3. Michi-no-Eki Roadside Stations
    michi = scrape_michi_no_eki()

    # 4. Highway SA/PA Rest Stops
    highway = scrape_highway_sapa()

    # 5. Temples & Shrines
    temples = get_prominent_temples_and_shrines()

    all_stamps = castles + eki + michi + highway + temples

    print("\n" + "=" * 70)
    print(" DATASET SUMMARY:")
    print(f" - Castles (日本100名城 + 続日本100名城): {len(castles)}")
    print(f" - Eki Stations (駅スタンプ): {len(eki)}")
    print(f" - Michi-no-Eki (道の駅): {len(michi)}")
    print(f" - Highway Rest Stops (高速道路 SA/PA): {len(highway)}")
    print(f" - Temples & Shrines (寺社・御朱印): {len(temples)}")
    print(f" TOTAL COMPREHENSIVE STAMPS: {len(all_stamps)}")
    print("=" * 70)

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_stamps, f, ensure_ascii=False, indent=2)

    print(f"Successfully saved {len(all_stamps)} stamps to {OUTPUT_FILE}!")


if __name__ == "__main__":
    main()
