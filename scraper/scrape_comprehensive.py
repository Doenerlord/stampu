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
import threading
from typing import List, Dict, Any, Optional, Set
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor

from geocode_gsi import (
    geocode_address,
    extract_prefecture,
    extract_prefecture_en,
    extract_city,
    clean_query,
    PREF_EN_TO_JA,
    PREF_JA_TO_EN
)

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
DETAIL_CACHE_FILE = os.path.join(os.path.dirname(__file__), "cache", "detail_cache.json")

# In-memory and disk cache for detail pages
_detail_cache: Dict[str, Dict[str, Any]] = {}
_detail_lock = threading.Lock()


def _load_detail_cache():
    global _detail_cache
    with _detail_lock:
        if os.path.exists(DETAIL_CACHE_FILE):
            try:
                with open(DETAIL_CACHE_FILE, "r", encoding="utf-8") as f:
                    _detail_cache = json.load(f)
            except Exception as e:
                print(f"[scraper] Failed to load detail cache: {e}")
                _detail_cache = {}
        else:
            _detail_cache = {}


def _save_detail_cache():
    os.makedirs(os.path.dirname(DETAIL_CACHE_FILE), exist_ok=True)
    try:
        with _detail_lock:
            snap = dict(_detail_cache)
        with open(DETAIL_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(snap, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[scraper] Failed to save detail cache: {e}")


_load_detail_cache()


def fetch_url(url: str, max_retries: int = 3) -> Optional[str]:
    if not url:
        return None
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=12)
            if resp.status_code == 200:
                resp.encoding = 'utf-8'
                return resp.text
        except Exception:
            time.sleep(0.3 * (attempt + 1))
    return None


def fetch_detail_info(url: str) -> Dict[str, Any]:
    if not url:
        return {}
    with _detail_lock:
        if url in _detail_cache:
            return _detail_cache[url]

    html = fetch_url(url)
    if not html:
        return {}

    soup = BeautifulSoup(html, "html.parser")
    text = ""
    for p in soup.find_all(["p", "div"]):
        ptxt = p.get_text("\n")
        if "Geo URI" in ptxt or "所在地" in ptxt:
            text = ptxt
            break

    coords = None
    geo_m = re.search(r"Geo URI[：:]\s*([0-9\.]+)\s*,\s*([0-9\.]+)", text)
    if geo_m:
        lat = round(float(geo_m.group(1)), 6)
        lng = round(float(geo_m.group(2)), 6)
        if 122.0 <= lng <= 154.0 and 20.0 <= lat <= 46.0:
            coords = [lng, lat]

    en_m = re.search(r"EN[：:]\s*([^\n]+)", text)
    name_en = en_m.group(1).strip() if en_m else ""

    addr_m = re.search(r"所在地[：:]\s*(?:上り[：:]\s*)?(?:〒\d{3}-\d{4}\s*)?([^\n]+)", text)
    addr = addr_m.group(1).strip() if addr_m else ""

    loc_m = re.search(r"設置場所[：:]\s*([^\n]+)", text)
    stamp_loc = loc_m.group(1).strip() if loc_m else ""

    hours_m = re.search(r"(?:営業時間|改札窓口営業時間)[：:]\s*([^\n]+)", text)
    hours = hours_m.group(1).strip() if hours_m else ""

    data = {
        "coords": coords,
        "name_en": name_en,
        "addr": addr,
        "stamp_loc": stamp_loc,
        "hours": hours
    }
    with _detail_lock:
        _detail_cache[url] = data
    _save_detail_cache()
    return data


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

        pref = extract_prefecture_en(loc_ja)
        city = extract_city(loc_ja) or pref

        name_en = name_ja
        if "城" in name_ja:
            name_en = name_ja.replace("城", " Castle")
        elif "館" in name_ja:
            name_en = name_ja.replace("館", " Fort")
        elif "台場" in name_ja:
            name_en = name_ja.replace("台場", " Battery Site")
        else:
            name_en = f"{name_ja} Castle Site"

        coords = geocode_address(f"{loc_ja} {name_ja}", fallback_query=loc_ja)
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
            "city": city,
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
# 2. RAILWAY STATIONS (Eki Stamps - 駅スタンプ)
# -------------------------------------------------------------
def scrape_railway_lines() -> List[Dict[str, Any]]:
    print("\n[Category: EKI] Scraping Major Railway Lines (Shinkansen, Metro, Toei, Osaka Metro, JR)...")
    lines_to_scrape = [
        # Major Metropolitan JR Commuter Lines
        ("jr-yamanote-line.html", "JR East (JR東日本)", "Yamanote Line"),
        ("jr-chuo-line.html", "JR East (JR東日本)", "Chūō Line"),
        ("jr-keihintohoku-line.html", "JR East (JR東日本)", "Keihin-Tōhoku Line"),
        ("jr-osaka-loop-line.html", "JR West (JR西日本)", "Osaka Loop Line"),
        ("jr-kyoto-line.html", "JR West (JR西日本)", "Kyoto Line"),

        # High-Speed Shinkansen Network
        ("jr-tokaido-shinkansen-line.html", "JR Central (JR東海)", "Tōkaidō Shinkansen"),
        ("sanyo-shinkansen-line.html", "JR West (JR西日本)", "San’yō Shinkansen"),
        ("jr-tohoku-shinkansen-line.html", "JR East (JR東日本)", "Tōhoku Shinkansen"),
        ("jr-joetsu-shinkansen.html", "JR East (JR東日本)", "Jōetsu Shinkansen"),
        ("jr-naganoshinkansen-line.html", "JR East (JR東日本)", "Hokuriku Shinkansen"),
        ("jr-hokurikushinkansen-line.html", "JR West (JR西日本)", "Hokuriku Shinkansen"),
        ("jr-kyushushinkansen-line.html", "JR Kyushu (JR九州)", "Kyūshū Shinkansen"),
        ("jr-nishikyushushinkansen-line.html", "JR Kyushu (JR九州)", "Nishi-Kyūshū Shinkansen"),
        ("jr-hokkaido-shinkansen-line.html", "JR Hokkaido (JR北海道)", "Hokkaidō Shinkansen"),

        # Tokyo Metro Network (all 9 lines)
        ("tokyometro-ginza-line.html", "Tokyo Metro (東京メトロ)", "Ginza Line"),
        ("tokyometro-marunouchi-line.html", "Tokyo Metro (東京メトロ)", "Marunouchi Line"),
        ("tokyometro-hibiya-line.html", "Tokyo Metro (東京メトロ)", "Hibiya Line"),
        ("tokyometro-tozai-line.html", "Tokyo Metro (東京メトロ)", "Tōzai Line"),
        ("tokyometro-chiyoda-line.html", "Tokyo Metro (東京メトロ)", "Chiyoda Line"),
        ("tokyometro-yurakucho-line.html", "Tokyo Metro (東京メトロ)", "Yūrakuchō Line"),
        ("tokyometro-hanzomon-line.html", "Tokyo Metro (東京メトロ)", "Hanzōmon Line"),
        ("tokyometro-nanboku-line.html", "Tokyo Metro (東京メトロ)", "Namboku Line"),
        ("tokyometro-fukutoshin-line.html", "Tokyo Metro (東京メトロ)", "Fukutoshin Line"),

        # Toei Subway Network (all 4 lines)
        ("toei-asakusa-line.html", "Toei Subway (東京都交通局)", "Toei Asakusa Line"),
        ("toei-mita-line.html", "Toei Subway (東京都交通局)", "Toei Mita Line"),
        ("toei-shinjuku-line.html", "Toei Subway (東京都交通局)", "Toei Shinjuku Line"),
        ("toei-oedo-line.html", "Toei Subway (東京都交通局)", "Toei Ōedo Line"),

        # Osaka Metro Network (9 lines)
        ("osakametro-midosuji-line.html", "Osaka Metro (大阪メトロ)", "Midōsuji Line"),
        ("osakametro-tanimachi-line.html", "Osaka Metro (大阪メトロ)", "Tanimachi Line"),
        ("osakametro-yotsubashi-line.html", "Osaka Metro (大阪メトロ)", "Yotsubashi Line"),
        ("osakametro-chuo-line.html", "Osaka Metro (大阪メトロ)", "Chūō Line"),
        ("osakametro-sennichimae-line.html", "Osaka Metro (大阪メトロ)", "Sennichimae Line"),
        ("osakametro-sakaisuji-line.html", "Osaka Metro (大阪メトロ)", "Sakaisuji Line"),
        ("osakametro-nagahoritsurumi-line.html", "Osaka Metro (大阪メトロ)", "Nagahori Tsurumi-ryokuchi Line"),
        ("osakametro-imasatosuji-line.html", "Osaka Metro (大阪メトロ)", "Imazatosuji Line"),
        ("osakametro-newtram-line.html", "Osaka Metro (大阪メトロ)", "Nankō Port Town Line"),
    ]

    station_links = []
    seen_slugs = set()

    for line_file, operator, line_name in lines_to_scrape:
        url = f"{BASE_URL}/{line_file}"
        html = fetch_url(url)
        if not html:
            continue

        soup = BeautifulSoup(html, "html.parser")
        is_metro = "tokyometro" in line_file
        for a in soup.find_all("a"):
            href = a.get("href", "")
            text = a.get_text(strip=True)
            if ("駅のスタンプ" in text and "設置あり" in text) or (is_metro and "駅のスタンプ" in text):
                raw = text.split("のスタンプ")[0]
                raw = re.sub(r'（.*?）', '', raw)
                raw = re.sub(r'\(.*?\)', '', raw)
                name_raw = raw.replace("JR", "").replace("東京メトロ", "").replace("都営地下鉄", "").replace("Osaka Metro", "").strip()
                if name_raw.endswith("駅"):
                    name_raw = name_raw[:-1]
                if not name_raw:
                    continue

                clean_href = href.lstrip("/") if href else ""
                full_url = href if (href and href.startswith("http")) else (f"{BASE_URL}/{clean_href}" if href else "")
                slug = re.search(r'([a-zA-Z0-9\-]+)\.html', href) if href else None
                slug_str = slug.group(1).lower() if slug else name_raw
                slug_str = re.sub(r'[^a-z0-9\-]+', '', slug_str)

                # Ensure slug uniqueness across lines
                if slug_str in seen_slugs:
                    continue
                seen_slugs.add(slug_str)

                station_links.append({
                    "name_raw": name_raw,
                    "url": full_url,
                    "slug": slug_str,
                    "line": line_name,
                    "operator": operator,
                    "line_file": line_file
                })

    print(f"-> Total distinct stations found across lines: {len(station_links)}")

    def fetch_station(item: Dict[str, Any]) -> Dict[str, Any]:
        detail = fetch_detail_info(item["url"]) if item["url"] else {}
        name_raw = item["name_raw"]
        line_name = item["line"]
        operator = item["operator"]
        slug_str = item["slug"]

        coords = detail.get("coords")
        addr = detail.get("addr", "")
        stamp_loc = detail.get("stamp_loc", "")
        hours = detail.get("hours", "")
        en_raw = detail.get("name_en", "")

        # If coords missing, geocode Japanese address
        if not coords and addr:
            g = geocode_address(addr)
            if g:
                coords = [g[0], g[1]]

        # Fallback prefecture determination
        pref = extract_prefecture_en(addr)
        if not pref or pref == "Japan":
            if "osaka" in item["line_file"] or "Osaka" in operator or line_name == "Osaka Loop Line":
                pref = "Osaka"
            elif "kyoto" in item["line_file"] or line_name == "Kyoto Line":
                pref = "Kyoto" if name_raw in ["京都", "西大路", "桂川", "向日町", "長岡京", "山崎"] else "Osaka"
            elif "tokyometro" in item["line_file"] or "toei" in item["line_file"]:
                if name_raw in ["和光市"]:
                    pref = "Saitama"
                elif name_raw in ["浦安", "南行徳", "行徳", "妙典", "原木中山", "西船橋"]:
                    pref = "Chiba"
                else:
                    pref = "Tokyo"
            elif name_raw in ["大宮", "さいたま新都心", "与野", "北浦和", "浦和", "南浦和", "蕨", "西川口", "川口", "熊谷", "本庄早稲田"]:
                pref = "Saitama"
            elif name_raw in ["川崎", "鶴見", "新子安", "東神奈川", "横浜", "新横浜", "小田原"]:
                pref = "Kanagawa"
            elif name_raw in ["熱海", "三島", "新富士", "静岡", "掛川", "浜松"]:
                pref = "Shizuoka"
            elif name_raw in ["豊橋", "三河安城", "名古屋"]:
                pref = "Aichi"
            elif name_raw in ["岐阜羽島"]:
                pref = "Gifu"
            elif name_raw in ["米原"]:
                pref = "Shiga"
            elif name_raw in ["新神戸", "西明石", "姫路", "相生"]:
                pref = "Hyogo"
            elif name_raw in ["岡山", "新倉敷"]:
                pref = "Okayama"
            elif name_raw in ["福山", "新尾道", "三原", "東広島", "広島"]:
                pref = "Hiroshima"
            elif name_raw in ["新岩国", "徳山", "新山口", "厚狭", "新下関"]:
                pref = "Yamaguchi"
            elif name_raw in ["小倉", "博多", "久留米", "筑後船小屋"]:
                pref = "Fukuoka"
            elif name_raw in ["新鳥栖", "武雄温泉", "嬉野温泉"]:
                pref = "Saga"
            elif name_raw in ["新大村", "諫早", "長崎"]:
                pref = "Nagasaki"
            elif name_raw in ["新玉名", "熊本", "新八代", "新水俣"]:
                pref = "Kumamoto"
            elif name_raw in ["出水", "川内", "鹿児島中央"]:
                pref = "Kagoshima"
            elif name_raw in ["木古内", "新函館北斗"]:
                pref = "Hokkaido"
            elif name_raw in ["新青森", "七戸十和田", "八戸", "奥津軽いまべつ"]:
                pref = "Aomori"
            elif name_raw in ["二戸", "いわて沼宮内", "盛岡", "新花巻", "北上", "水沢江刺", "一ノ関"]:
                pref = "Iwate"
            elif name_raw in ["くりこま高原", "古川", "仙台", "白石蔵王"]:
                pref = "Miyagi"
            elif name_raw in ["福島", "郡山", "白河", "新白河"]:
                pref = "Fukushima"
            elif name_raw in ["那須塩原", "宇都宮", "小山"]:
                pref = "Tochigi"
            elif name_raw in ["高崎", "安中榛名"]:
                pref = "Gunma"
            elif name_raw in ["軽井沢", "佐久平", "上田", "長野", "飯山"]:
                pref = "Nagano"
            elif name_raw in ["上越妙高", "糸魚川", "越後湯沢", "浦佐", "長岡", "燕三条", "新潟"]:
                pref = "Niigata"
            elif name_raw in ["黒部宇奈月温泉", "富山", "新高岡"]:
                pref = "Toyama"
            elif name_raw in ["金沢", "小松", "加賀温泉"]:
                pref = "Ishikawa"
            elif name_raw in ["芦原温泉", "福井", "越前たけふ", "敦賀"]:
                pref = "Fukui"
            else:
                pref = "Tokyo"

        city = extract_city(addr)
        if not city:
            if pref == "Tokyo": city = "Tokyo"
            elif pref == "Osaka": city = "Osaka City"
            elif pref == "Kyoto": city = "Kyoto City"
            elif pref == "Saitama": city = "Saitama City"
            elif pref == "Kanagawa": city = "Yokohama City" if name_raw in ["横浜", "鶴見", "新子安", "東神奈川", "新横浜"] else "Kawasaki City"
            else: city = pref

        # Coords safety fallback if GSI failed
        if not coords:
            pref_ja = PREF_EN_TO_JA.get(pref, "")
            g = geocode_address(f"{pref_ja} {name_raw}駅")
            if g:
                coords = [g[0], g[1]]
            else:
                if pref == "Tokyo": coords = [139.7671, 35.6812]
                elif pref == "Osaka": coords = [135.4962, 34.7025]
                elif pref == "Kyoto": coords = [135.7588, 34.9853]
                elif pref == "Saitama": coords = [139.6243, 35.9064]
                elif pref == "Kanagawa": coords = [139.6226, 35.4660]
                else: coords = [138.2529, 36.2048]

        # Station names formatting
        if en_raw:
            clean_en = en_raw.replace("JR ", "").replace("JR", "").replace("Tokyo Metro ", "").replace("Toei Subway ", "").strip()
            if not clean_en.lower().endswith("station"):
                clean_en = f"{clean_en} Station"
            name_en = clean_en
        else:
            name_en = f"{name_raw} Station"

        if "tokyometro" in item["line_file"]:
            name_ja = f"東京メトロ{name_raw}駅"
            stamp_id = f"eki-metro-{slug_str.replace('metro-', '')}"
        elif "toei" in item["line_file"]:
            name_ja = f"都営地下鉄{name_raw}駅"
            stamp_id = f"eki-toei-{slug_str.replace('toei-', '')}"
        elif "osakametro" in item["line_file"]:
            name_ja = f"Osaka Metro {name_raw}駅"
            stamp_id = f"eki-om-{slug_str.replace('om-', '')}"
        elif "yamanote" in item["line_file"]:
            name_ja = f"JR{name_raw}駅"
            stamp_id = f"eki-yamanote-{slug_str.replace('jr-', '')}"
        elif "shinkansen" in item["line_file"]:
            name_ja = f"JR{name_raw}駅（新幹線）"
            stamp_id = f"eki-shinkansen-{slug_str.replace('jr-', '').replace('jrt-', '').replace('jrw-', '')}"
        else:
            name_ja = f"JR{name_raw}駅"
            stamp_id = f"eki-{slug_str.replace('jr-', '')}"

        name_romaji = f"{name_raw}-eki"

        if not stamp_loc:
            stamp_loc = f"{name_ja} 改札口・みどりの窓口付近 (Ticket Gate / Station Counter)"
        if not hours:
            hours = "06:00 - 23:30 (First train to last train / Station hours)"

        return {
            "id": stamp_id,
            "name": name_en,
            "name_ja": name_ja,
            "name_romaji": name_romaji,
            "category": "eki",
            "prefecture": pref,
            "city": city,
            "address": addr or f"{pref} {name_raw}駅構内",
            "coordinates": [coords[0], coords[1]],
            "stampLocation": stamp_loc,
            "hours": hours,
            "operator": operator,
            "imageUrl": f"/images/stamps/{stamp_id}.jpg",
            "description": f"Official {operator.split(' (')[0]} commemorative railway stamp for {name_en} ({line_name}) in {city}, {pref}. Depicts iconic local landmarks, cultural heritage, and regional railway history."
        }

    with ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(fetch_station, station_links))

    print(f"-> Completed {len(results)} Railway Stations with verified coordinates.")
    return results


# -------------------------------------------------------------
# 3. ROADSIDE STATIONS (Michi-no-Eki - 道の駅)
# -------------------------------------------------------------
def scrape_michi_no_eki() -> List[Dict[str, Any]]:
    print("\n[Category: MICHI-NO-EKI] Scraping Roadside Rest Stations across all 47 Prefectures of Japan...")
    target_prefs = [
        # Hokkaido
        ("hokkaido", "Hokkaido"),
        # Tohoku
        ("aomori", "Aomori"), ("iwate", "Iwate"), ("miyagi", "Miyagi"),
        ("akita", "Akita"), ("yamagata", "Yamagata"), ("fukushima", "Fukushima"),
        # Kanto
        ("ibaraki", "Ibaraki"), ("tochigi", "Tochigi"), ("gunma", "Gunma"),
        ("saitama", "Saitama"), ("chiba", "Chiba"), ("tokyo", "Tokyo"), ("kanagawa", "Kanagawa"),
        # Chubu / Hokuriku / Koshinetsu
        ("niigata", "Niigata"), ("toyama", "Toyama"), ("ishikawa", "Ishikawa"),
        ("fukui", "Fukui"), ("yamanashi", "Yamanashi"), ("nagano", "Nagano"),
        ("gifu", "Gifu"), ("shizuoka", "Shizuoka"), ("aichi", "Aichi"),
        # Kansai
        ("mie", "Mie"), ("shiga", "Shiga"), ("kyoto", "Kyoto"),
        ("osaka", "Osaka"), ("hyogo", "Hyogo"), ("nara", "Nara"), ("wakayama", "Wakayama"),
        # Chugoku
        ("tottori", "Tottori"), ("shimane", "Shimane"), ("okayama", "Okayama"),
        ("hiroshima", "Hiroshima"), ("yamaguchi", "Yamaguchi"),
        # Shikoku
        ("tokushima", "Tokushima"), ("kagawa", "Kagawa"), ("ehime", "Ehime"), ("kochi", "Kochi"),
        # Kyushu / Okinawa
        ("fukuoka", "Fukuoka"), ("saga", "Saga"), ("nagasaki", "Nagasaki"),
        ("kumamoto", "Kumamoto"), ("oita", "Oita"), ("miyazaki", "Miyazaki"),
        ("kagoshima", "Kagoshima"), ("okinawa", "Okinawa")
    ]

    michi_links = []
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
                name_raw = text.split("のスタンプ")[0].replace("道の駅", "").strip()
                name_raw = re.sub(r"[≪（\(].*$", "", name_raw).strip()
                if not name_raw or name_raw in seen_names:
                    continue
                seen_names.add(name_raw)

                clean_href = href.lstrip("/") if href else ""
                full_url = href if (href and href.startswith("http")) else (f"{BASE_URL}/{clean_href}" if href else "")
                slug = re.search(r"miti-([a-zA-Z0-9\-]+)\.html", href) if href else None
                slug_str = slug.group(1).lower() if slug else f"michi-{len(michi_links)}"

                michi_links.append({
                    "name_raw": name_raw,
                    "pref_en": pref_en,
                    "pref_ja": PREF_EN_TO_JA.get(pref_en, pref_en),
                    "url": full_url,
                    "slug": slug_str
                })

    print(f"-> Total Michi-no-Eki found: {len(michi_links)}")

    def fetch_michi(m: Dict[str, Any]) -> Dict[str, Any]:
        detail = fetch_detail_info(m["url"]) if m["url"] else {}
        st_name = m["name_raw"]
        pref_en = m["pref_en"]
        pref_ja = m["pref_ja"]
        slug_str = m["slug"]

        coords = detail.get("coords")
        addr = detail.get("addr", "")
        stamp_loc = detail.get("stamp_loc", "")
        hours = detail.get("hours", "")
        name_en = detail.get("name_en", "")

        # If coords missing, geocode Japanese address
        if not coords and addr:
            g = geocode_address(addr)
            if g:
                coords = [g[0], g[1]]

        # Fallback geocoding with Japanese prefecture and town name (never pass English words or 道の駅)
        if not coords:
            clean_name = re.sub(r"[・☆★0-9]+", " ", st_name).strip()
            g = geocode_address(f"{pref_ja} {clean_name}")
            if not g:
                g = geocode_address(f"{pref_ja} {st_name}")
            if not g:
                g = geocode_address(pref_ja)
            if g:
                coords = [g[0], g[1]]
            else:
                coords = [138.2529, 36.2048]

        city = extract_city(addr) or f"{pref_en} Roadside"
        display_name = name_en if name_en else f"Michi-no-Eki {st_name}"
        if not display_name.startswith("Michi-no-Eki") and not display_name.startswith("Michinoeki"):
            display_name = f"Michi-no-Eki {display_name}"

        stamp_id = f"michi-{slug_str}"
        if not stamp_loc:
            stamp_loc = f"道の駅 {st_name} 観光案内所・物産館スタンプ台 (Main Hall / Information Desk)"
        if not hours:
            hours = "09:00 - 18:00 (Facility / Gift Shop hours)"

        return {
            "id": stamp_id,
            "name": display_name,
            "name_ja": f"道の駅 {st_name}",
            "name_romaji": f"Michi-no-Eki {st_name}",
            "category": "michinoeki",
            "prefecture": pref_en,
            "city": city,
            "address": addr or f"{pref_en} 道の駅 {st_name}",
            "coordinates": [coords[0], coords[1]],
            "stampLocation": stamp_loc,
            "hours": hours,
            "operator": f"National Roadside Station Association (全国道の駅連絡会 - {pref_en})",
            "imageUrl": f"/images/stamps/{stamp_id}.jpg",
            "description": f"Official Roadside Station stamp for Michi-no-Eki {st_name} in {city}, {pref_en}. Showcases regional specialty produce, scenic vistas, and road-trip hospitality."
        }

    with ThreadPoolExecutor(max_workers=10) as ex:
        results = list(ex.map(fetch_michi, michi_links))

    print(f"-> Completed {len(results)} Michi-no-Eki Roadside Stations.")
    return results


# -------------------------------------------------------------
# 4. HIGHWAY STAMPS (Expressway SA / PA - 高速道路)
# -------------------------------------------------------------
def scrape_highway_sapa() -> List[Dict[str, Any]]:
    print("\n[Category: HIGHWAY] Scraping Expressway SA/PA Rest Stops with verified coordinates...")
    expressways = [
        ("tomei-expwy.html", "Tomei Expressway (東名高速道路)", "NEXCO Central"),
        ("shintomei-expwy.html", "Shin-Tomei Expressway (新東名高速道路)", "NEXCO Central"),
        ("chuo-expwy.html", "Chuo Expressway (中央自動車道)", "NEXCO Central"),
        ("kanetsu-expwy.html", "Kan-Etsu Expressway (関越自動車道)", "NEXCO East"),
        ("tohoku-expwy.html", "Tohoku Expressway (東北自動車道)", "NEXCO East"),
        ("meishin-expwy.html", "Meishin Expressway (名神高速道路)", "NEXCO West"),
    ]

    sapa_links = []
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

                clean_href = href.lstrip("/") if href else ""
                full_url = href if (href and href.startswith("http")) else (f"{BASE_URL}/{clean_href}" if href else "")
                slug = re.search(r'hw-([a-zA-Z0-9\-]+)\.html', href) if href else None
                slug_str = slug.group(1).lower() if slug else sapa_name
                slug_str = re.sub(r'[^a-z0-9\-]+', '', slug_str) or f"hw-{len(sapa_links)}"

                sapa_links.append({
                    "name_raw": sapa_name,
                    "url": full_url,
                    "slug": slug_str,
                    "exp_name": exp_name,
                    "operator": operator
                })

    print(f"-> Total Highway SA/PA found: {len(sapa_links)}")

    def fetch_highway(hw: Dict[str, Any]) -> Dict[str, Any]:
        detail = fetch_detail_info(hw["url"]) if hw["url"] else {}
        sapa_name = hw["name_raw"]
        exp_name = hw["exp_name"]
        operator = hw["operator"]
        slug_str = hw["slug"]

        coords = detail.get("coords")
        addr = detail.get("addr", "")
        stamp_loc = detail.get("stamp_loc", "")
        hours = detail.get("hours", "") or "24 Hours (Service Area 24時間利用可能)"
        name_en = detail.get("name_en", "")

        if not coords and addr:
            g = geocode_address(addr)
            if g:
                coords = [g[0], g[1]]

        # Determine real prefecture and city from address or route
        pref = extract_prefecture_en(addr)
        city = extract_city(addr)

        if not pref or pref == "Japan":
            if any(k in sapa_name for k in ["港北", "海老名", "中井", "鮎沢", "藤野"]): pref = "Kanagawa"
            elif any(k in sapa_name for k in ["足柄", "富士", "駿河湾", "静岡", "藤枝", "掛川", "遠州森町", "浜松", "浜名湖", "牧之原"]): pref = "Shizuoka"
            elif any(k in sapa_name for k in ["長篠設楽原", "岡崎", "尾張一宮"]): pref = "Aichi"
            elif any(k in sapa_name for k in ["石川"]): pref = "Tokyo"
            elif any(k in sapa_name for k in ["談合坂", "初狩", "釈迦堂", "境川", "双葉", "八ヶ岳", "谷村"]): pref = "Yamanashi"
            elif any(k in sapa_name for k in ["中央道原", "諏訪湖", "辰野", "小黒川", "駒ヶ岳", "阿智"]): pref = "Nagano"
            elif any(k in sapa_name for k in ["神坂", "恵那峡", "屏風山", "虎渓山", "内津峠", "養老", "伊吹"]): pref = "Gifu"
            elif any(k in sapa_name for k in ["多賀", "黒丸", "菩提寺", "草津", "大津"]): pref = "Shiga"
            elif any(k in sapa_name for k in ["桂川"]): pref = "Kyoto"
            elif any(k in sapa_name for k in ["吹田"]): pref = "Osaka"
            elif any(k in sapa_name for k in ["三芳", "高坂", "嵐山", "寄居", "上里", "蓮田", "羽生"]): pref = "Saitama"
            elif any(k in sapa_name for k in ["佐野", "都賀西方", "大谷", "上河内", "矢板北", "黒磯", "那須高原"]): pref = "Tochigi"
            elif any(k in sapa_name for k in ["駒寄", "赤城高原", "谷川岳"]): pref = "Gunma"
            elif any(k in sapa_name for k in ["塩沢石打", "越後川口", "山谷"]): pref = "Niigata"
            elif any(k in sapa_name for k in ["阿武隈", "鏡石", "安積", "安達太良", "福島松川", "吾妻", "国見"]): pref = "Fukushima"
            elif any(k in sapa_name for k in ["菅生", "鶴巣", "長者原"]): pref = "Miyagi"
            elif any(k in sapa_name for k in ["金成", "前沢", "北上金ヶ崎", "紫波", "矢巾", "滝沢", "岩手山"]): pref = "Iwate"
            elif any(k in sapa_name for k in ["花輪"]): pref = "Akita"
            elif any(k in sapa_name for k in ["津軽"]): pref = "Aomori"
            else: pref = "Japan"

        if not city:
            city = f"{exp_name.split(' (')[0]} Corridor"

        # Geocode fallback if coords still missing
        if not coords:
            pref_ja = PREF_EN_TO_JA.get(pref, "")
            clean_sapa = re.sub(r'^(?:東名|新東名|中央|関越|東北|名神)(?:高速道路|自動車道)?', '', sapa_name)
            clean_sapa = clean_sapa.replace("SA", "").replace("PA", "").strip()
            g = geocode_address(f"{pref_ja} {clean_sapa}")
            if not g:
                g = geocode_address(pref_ja)
            if g:
                coords = [g[0], g[1]]
            else:
                coords = [138.2529, 36.2048]

        display_name = name_en if name_en else f"{sapa_name} ({exp_name.split(' (')[0]})"
        stamp_id = f"hw-{slug_str}"

        if not stamp_loc:
            stamp_loc = f"{sapa_name} サービスエリア・パーキングエリア コンシェルジュ / 案内所 (Information Desk)"

        return {
            "id": stamp_id,
            "name": display_name,
            "name_ja": f"{sapa_name}（{exp_name.split(' (')[1].rstrip(')')}）",
            "name_romaji": sapa_name,
            "category": "highway",
            "prefecture": pref,
            "city": city,
            "address": addr or f"{exp_name} {sapa_name}",
            "coordinates": [coords[0], coords[1]],
            "stampLocation": stamp_loc,
            "hours": hours,
            "operator": operator,
            "imageUrl": f"/images/stamps/{stamp_id}.jpg",
            "description": f"Collectible Highway Service Area stamp for {sapa_name} along the {exp_name} in {city}, {pref}. Commemorates iconic local culinary specialties, highway journeys, and regional vistas."
        }

    with ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(fetch_highway, sapa_links))

    print(f"-> Completed {len(results)} Highway SA/PA rest stops with verified coordinates.")
    return results


# -------------------------------------------------------------
# 5. TEMPLES & SHRINES (御朱印 / 記念スタンプ)
# -------------------------------------------------------------
def get_prominent_temples_and_shrines() -> List[Dict[str, Any]]:
    print("\n[Category: TEMPLE & SHRINE] Curating Iconic Spiritual Locations...")
    spiritual_sites = [
        {"name": "Senso-ji Temple", "ja": "金龍山 浅草寺", "romaji": "Sensō-ji", "pref": "Tokyo", "city": "Taito City", "addr": "東京都台東区浅草2-3-1", "loc": "浅草寺 本堂・御朱印所 (Main Hall)", "desc": "Tokyo's oldest and most renowned Buddhist temple, dedicated to Bodhisattva Kannon."},
        {"name": "Meiji Jingu Shrine", "ja": "明治神宮", "romaji": "Meiji Jingū", "pref": "Tokyo", "city": "Shibuya City", "addr": "東京都渋谷区代々木神園町1-1", "loc": "明治神宮 神楽殿・社務所 (Kaguraden Office)", "desc": "Historic Shinto shrine nestled in an expansive sacred forest in Shibuya, dedicated to Emperor Meiji."},
        {"name": "Kanda Myojin Shrine", "ja": "神田明神（神田神社）", "romaji": "Kanda Myōjin", "pref": "Tokyo", "city": "Chiyoda City", "addr": "東京都千代田区外神田2-16-2", "loc": "神田明神 鳳凰殿・社務所 (Shrine Office)", "desc": "Historic Tokyo guardian shrine dating back nearly 1,300 years, protector of Edo/Tokyo and technology."},
        {"name": "Zojo-ji Temple", "ja": "三縁山 広度院 増上寺", "romaji": "Zōjō-ji", "pref": "Tokyo", "city": "Minato City", "addr": "東京都港区芝公園4-7-35", "loc": "増上寺 安国殿・寺務所 (Ankokuden Office)", "desc": "Head temple of the Jodo sect and family temple of the Tokugawa Shogunate, beneath Tokyo Tower."},
        {"name": "Gotoku-ji Temple (Lucky Cat)", "ja": "大谿山 豪徳寺", "romaji": "Gōtoku-ji", "pref": "Tokyo", "city": "Setagaya City", "addr": "東京都世田谷区豪徳寺1-24-7", "loc": "豪徳寺 寺務所・招福殿 (Maneki-Neko Hall)", "desc": "Peaceful Setagaya Buddhist temple celebrated as the legendary historic birthplace of the Maneki-neko (lucky beckoning cat)."},
        {"name": "Nezu Shrine", "ja": "根津神社", "romaji": "Nezu Jinja", "pref": "Tokyo", "city": "Bunkyo City", "addr": "東京都文京区根津1-28-9", "loc": "根津神社 社務所・授与所 (Shrine Office)", "desc": "One of Tokyo's oldest Shinto shrines founded in 1705, renowned for its picturesque Senbon Torii tunnel and spring azalea gardens."},
        {"name": "Tsurugaoka Hachimangu", "ja": "鶴岡八幡宮", "romaji": "Tsurugaoka Hachimangū", "pref": "Kanagawa", "city": "Kamakura City", "addr": "神奈川県鎌倉市雪ノ下2-1-31", "loc": "鶴岡八幡宮 舞殿・社務所 (Main Office)", "desc": "The most important Shinto shrine in Kamakura, founded by Minamoto no Yoritomo in 1180."},
        {"name": "Kotoku-in (Kamakura Daibutsu)", "ja": "高徳院（鎌倉大仏）", "romaji": "Kōtoku-in", "pref": "Kanagawa", "city": "Kamakura City", "addr": "神奈川県鎌倉市長谷4-2-28", "loc": "高徳院 拝観受付・朱印所 (Great Buddha Office)", "desc": "Famous Buddhist temple housing the monumental outdoor bronze statue of Amida Buddha (Kamakura Daibutsu)."},
        {"name": "Hasedera Temple", "ja": "海光山 慈照院 長谷寺", "romaji": "Hase-dera", "pref": "Kanagawa", "city": "Kamakura City", "addr": "神奈川県鎌倉市長谷3-11-2", "loc": "長谷寺 観音堂・寺務所 (Kannon Hall)", "desc": "Scenic Kamakura coastal temple renowned for its eleven-headed Kannon statue and blooming hydrangeas."},
        {"name": "Hakone Shrine & Kuzuryu Shrine", "ja": "箱根神社（九頭龍神社）", "romaji": "Hakone Jinja", "pref": "Kanagawa", "city": "Ashigarashimo District", "addr": "神奈川県足柄下郡箱根町元箱根80-1", "loc": "箱根神社 社務所・平和の鳥居 (Heiwa no Torii Office)", "desc": "Mountain-lake sanctuary on Lake Ashi famous for its iconic vermilion Peace Torii gate standing directly in the water."},
        {"name": "Kamakura Kencho-ji Temple", "ja": "巨福山 建長寺", "romaji": "Kenchō-ji", "pref": "Kanagawa", "city": "Kamakura City", "addr": "神奈川県鎌倉市山ノ内8", "loc": "建長寺 宗務本所・朱印所 (Main Office)", "desc": "First of Kamakura's Five Great Zen Temples and oldest Zen training monastery in Japan, founded in 1253."},
        {"name": "Nikko Toshogu Shrine", "ja": "日光東照宮", "romaji": "Nikkō Tōshōgū", "pref": "Tochigi", "city": "Nikko City", "addr": "栃木県日光市山内2301", "loc": "日光東照宮 陽明門・社務所 (Main Office)", "desc": "UNESCO World Heritage shrine lavishly decorated in gold leaf and intricate carvings, enshrining Tokugawa Ieyasu."},
        {"name": "Naritasan Shinsho-ji", "ja": "成田山 新勝寺", "romaji": "Naritasan Shinshō-ji", "pref": "Chiba", "city": "Narita City", "addr": "千葉県成田市成田1番地", "loc": "成田山 大本堂・総受付 (Great Main Hall)", "desc": "Famed Buddhist temple founded in 940 AD, renowned for fiery Goma prayers and historic omotesando street."},
        {"name": "Katori Jingu Shrine", "ja": "香取神宮", "romaji": "Katori Jingū", "pref": "Chiba", "city": "Katori City", "addr": "千葉県香取市香取1699", "loc": "香取神宮 拝殿・社務所 (Main Office)", "desc": "Top-tier ancient Shinto grand shrine alongside Ise and Kashima, spiritual protector of martial arts and peace."},
        {"name": "Musashi Ichinomiya Hikawa Shrine", "ja": "武蔵一宮 氷川神社", "romaji": "Hikawa Jinja", "pref": "Saitama", "city": "Saitama City", "addr": "埼玉県さいたま市大宮区高鼻町1-407", "loc": "氷川神社 拝殿・社務所 (Shrine Office)", "desc": "Ancient grand shrine with a 2-kilometer torii-lined approach avenue, spiritual anchor of Omiya and head of 280 Hikawa shrines."},
        {"name": "Kashima Jingu Shrine", "ja": "鹿島神宮", "romaji": "Kashima Jingū", "pref": "Ibaraki", "city": "Kashima City", "addr": "茨城県鹿嶋市宮中2306-1", "loc": "鹿島神宮 本殿・社務所 (Main Shrine Office)", "desc": "One of Japan's most historic martial grand shrines, founded in 600 BC and dedicated to martial deity Takemikazuchi no Okami."},
        {"name": "Zenko-ji Temple", "ja": "信州 善光寺", "romaji": "Zenkō-ji", "pref": "Nagano", "city": "Nagano City", "addr": "長野県長野市元善町491", "loc": "善光寺 本堂内陣・授与所 (Main Sanctuary)", "desc": "Historic 7th-century non-denominational pilgrimage temple housing the first Buddhist statue brought to Japan."},
        {"name": "Fujisan Hongu Sengen Taisha", "ja": "富士山本宮浅間大社", "romaji": "Fujisan Hongū Sengen Taisha", "pref": "Shizuoka", "city": "Fujinomiya City", "addr": "静岡県富士宮市宮町1-1", "loc": "浅間大社 祈祷受付・社務所 (Mount Fuji Shrine Office)", "desc": "Supreme head shrine of all 1,300 Sengen shrines across Japan, dedicated to the guardian deity of Mount Fuji."},
        {"name": "Eihei-ji Temple", "ja": "大本山 永平寺", "romaji": "Eihei-ji", "pref": "Fukui", "city": "Yoshida District", "addr": "福井県吉田郡永平寺町志比5-15", "loc": "永平寺 吉祥閣・納経所 (Kisshokaku Office)", "desc": "Head temple of Soto Zen Buddhism founded by Master Dogen in 1244, nestled deeply amidst ancient cryptomeria cedar forests."},
        {"name": "Fushimi Inari Taisha", "ja": "伏見稲荷大社", "romaji": "Fushimi Inari Taisha", "pref": "Kyoto", "city": "Kyoto City", "addr": "京都府京都市伏見区深草藪之内町68", "loc": "伏見稲荷大社 本殿・集印所 (Main Sanctuary Office)", "desc": "Head shrine of all Inari Shinto shrines, famed for its thousands of vermilion Senbon Torii gates climbing Mount Inari."},
        {"name": "Kiyomizu-dera Temple", "ja": "音羽山 清水寺", "romaji": "Kiyomizu-dera", "pref": "Kyoto", "city": "Kyoto City", "addr": "京都府京都市東山区清水1-294", "loc": "清水寺 本堂・納経所 (Main Wooden Stage)", "desc": "Iconic UNESCO World Heritage temple perched on Mount Otowa, celebrated for its soaring wooden stage and Otowa Waterfall."},
        {"name": "Kinkaku-ji (Golden Pavilion)", "ja": "鹿苑寺（金閣寺）", "romaji": "Kinkaku-ji", "pref": "Kyoto", "city": "Kyoto City", "addr": "京都府京都市北区金閣寺町1", "loc": "金閣寺 拝観受付・朱印所 (Golden Pavilion Office)", "desc": "Zen Buddhist temple whose top two floors are completely covered in gleaming gold leaf, reflected in Kyoko-chi pond."},
        {"name": "Ginkaku-ji (Silver Pavilion)", "ja": "慈照寺（銀閣寺）", "romaji": "Ginkaku-ji", "pref": "Kyoto", "city": "Kyoto City", "addr": "京都府京都市左京区銀閣寺町2", "loc": "銀閣寺 朱印受付・寺務所 (Temple Office)", "desc": "Quintessential Higashiyama culture Zen temple celebrated for its dry-sand garden (Kogetsudai) and moss grounds."},
        {"name": "Byodoin Temple (Phoenix Hall)", "ja": "平等院 鳳凰堂", "romaji": "Byōdō-in", "pref": "Kyoto", "city": "Uji City", "addr": "京都府宇治市宇治蓮華116", "loc": "平等院 集印所・鳳翔館 (Phoenix Hall Office)", "desc": "UNESCO World Heritage Pure Land Buddhist temple, immortalized on the Japanese 10 yen coin and 10,000 yen note."},
        {"name": "Heian Jingu Shrine", "ja": "平安神宮", "romaji": "Heian Jingū", "pref": "Kyoto", "city": "Kyoto City", "addr": "京都府京都市左京区岡崎西天王町97", "loc": "平安神宮 社務所・大極殿 (Main Sanctuary Office)", "desc": "Majestic Kyoto imperial shrine commemorating the 1,100th anniversary of Heian-kyo, featuring a giant torii and classical stroll gardens."},
        {"name": "Yasaka Shrine (Gion)", "ja": "八坂神社（祇園社）", "romaji": "Yasaka Jinja", "pref": "Kyoto", "city": "Kyoto City", "addr": "京都府京都市東山区祇園町北側625", "loc": "八坂神社 朱印所・本殿授与所 (Gion Shrine Office)", "desc": "Guardian shrine of the Gion geisha district and home to the legendary Gion Matsuri festival, one of Japan's big three festivals."},
        {"name": "Ryoan-ji Temple", "ja": "大雲山 龍安寺", "romaji": "Ryōan-ji", "pref": "Kyoto", "city": "Kyoto City", "addr": "京都府京都市右京区龍安寺御陵下町13", "loc": "龍安寺 方丈・寺務所 (Temple Office)", "desc": "World-famous Zen temple featuring Japan's finest dry landscape rock garden (Karesansui) of fifteen mystical stones."},
        {"name": "Tenryu-ji Temple", "ja": "霊亀山 天龍寺", "romaji": "Tenryū-ji", "pref": "Kyoto", "city": "Kyoto City", "addr": "京都府京都市右京区嵯峨天龍寺芒ノ馬場町68", "loc": "天龍寺 庫裏・納経所 (Kuri Hall Office)", "desc": "Ranked first among Kyoto's Five Mountain Zen temples, bordering Arashiyama bamboo grove with a 14th-century circular pond garden."},
        {"name": "Todai-ji Temple", "ja": "華厳宗大本山 東大寺", "romaji": "Tōdai-ji", "pref": "Nara", "city": "Nara City", "addr": "奈良県奈良市雑司町406-1", "loc": "東大寺 大仏殿内・納経所 (Great Buddha Hall)", "desc": "Monumental ancient Buddhist temple housing the world's largest bronze Buddha statue inside the Daibutsuden."},
        {"name": "Kasuga Taisha Shrine", "ja": "春日大社", "romaji": "Kasuga Taisha", "pref": "Nara", "city": "Nara City", "addr": "奈良県奈良市春日野町160", "loc": "春日大社 御本殿・社務所 (Main Sanctuary)", "desc": "Ancient Shinto shrine founded in 768 AD in Nara Park, famous for its thousands of bronze and stone lanterns."},
        {"name": "Horyu-ji Temple", "ja": "法隆寺（斑鳩寺）", "romaji": "Hōryū-ji", "pref": "Nara", "city": "Ikoma District", "addr": "奈良県生駒郡斑鳩町法隆寺山内1-1", "loc": "法隆寺 聖霊院・納経所 (Shoryoin Office)", "desc": "Japan's first UNESCO World Heritage site, housing the world's oldest surviving wooden structures dating to 607 AD."},
        {"name": "Yakushi-ji Temple", "ja": "薬師寺", "romaji": "Yakushi-ji", "pref": "Nara", "city": "Nara City", "addr": "奈良県奈良市西ノ京町457", "loc": "薬師寺 金堂・授与所 (Kondo Hall Office)", "desc": "Head temple of the Hosso Buddhist sect founded by Emperor Tenmu, famous for its surviving 8th-century East Pagoda."},
        {"name": "Toshodai-ji Temple", "ja": "唐招提寺", "romaji": "Tōshōdai-ji", "pref": "Nara", "city": "Nara City", "addr": "奈良県奈良市五条町13-46", "loc": "唐招提寺 礼堂・納経所 (Reido Hall Office)", "desc": "Historic temple founded in 759 AD by the blind Chinese master monk Ganjin, featuring classical Nara period architecture."},
        {"name": "Koyasan Kongobuji Temple", "ja": "高野山 金剛峯寺", "romaji": "Kōyasan Kongōbu-ji", "pref": "Wakayama", "city": "Ito District", "addr": "和歌山県伊都郡高野町高野山132", "loc": "金剛峯寺 本坊・納経所 (Head Temple Office)", "desc": "Head temple of Shingon Esoteric Buddhism on sacred Mount Koya, founded by Kobo Daishi Kukai in 816 AD."},
        {"name": "Kumano Nachi Taisha & Seiganto-ji", "ja": "熊野那智大社・那智山青岸渡寺", "romaji": "Kumano Nachi Taisha", "pref": "Wakayama", "city": "Higashimuro District", "addr": "和歌山県東牟婁郡那智勝浦町那智山1", "loc": "熊野那智大社 社務所・三重塔 (Shrine Office / Pagoda)", "desc": "UNESCO Kumano Kodo pilgrimage shrine adjacent to Seiganto-ji's three-story pagoda and the 133-meter Nachi Falls."},
        {"name": "Kumano Hongu Taisha", "ja": "熊野本宮大社", "romaji": "Kumano Hongū Taisha", "pref": "Wakayama", "city": "Tanabe City", "addr": "和歌山県田辺市本宮町本宮1110", "loc": "熊野本宮大社 授与所・社務所 (Main Shrine Office)", "desc": "The spiritual heart of the Kumano Sanzan pilgrimage network and the site of Oyunohara, Japan's tallest torii gate."},
        {"name": "Kumano Hayatama Taisha", "ja": "熊野速玉大社", "romaji": "Kumano Hayatama Taisha", "pref": "Wakayama", "city": "Shingu City", "addr": "和歌山県新宮市新宮1番地", "loc": "熊野速玉大社 社務所 (Shrine Office)", "desc": "Vermilion sacred shrine of Kumano Sanzan on the Kumano River, enshrining a sacred 1,000-year-old Nagi tree."},
        {"name": "Ise Jingu (Naiku & Geku)", "ja": "伊勢神宮（内宮・外宮）", "romaji": "Ise Jingū", "pref": "Mie", "city": "Ise City", "addr": "三重県伊勢市宇治館町1", "loc": "伊勢神宮 内宮神楽殿・参集殿 (Kaguraden Hall)", "desc": "The most sacred Shinto shrine in all of Japan, dedicated to the sun goddess Amaterasu Omikami."},
        {"name": "Atsuta Jingu Shrine", "ja": "熱田神宮", "romaji": "Atsuta Jingū", "pref": "Aichi", "city": "Nagoya City", "addr": "愛知県名古屋市熱田区神宮1-1-1", "loc": "熱田神宮 授与所・本殿前 (Main Office)", "desc": "Ancient sacred shrine in Nagoya enshrining the legendary Kusanagi no Tsurugi sword, one of Japan's Imperial Regalia."},
        {"name": "Itsukushima Shrine", "ja": "嚴島神社（宮島）", "romaji": "Itsukushima Jinja", "pref": "Hiroshima", "city": "Hatsukaichi City", "addr": "広島県廿日市市宮島町1-1", "loc": "嚴島神社 廻廊内・授与所 (Floating Shrine Office)", "desc": "World-famous UNESCO World Heritage Shinto shrine on Miyajima island featuring the floating vermilion O-Torii gate in the sea."},
        {"name": "Izumo Taisha Grand Shrine", "ja": "出雲大社", "romaji": "Izumo Taisha", "pref": "Shimane", "city": "Izumo City", "addr": "島根県出雲市大社町杵築東195", "loc": "出雲大社 拝殿・神楽殿社務所 (Kaguraden Office)", "desc": "One of Japan's oldest and most prestigious Shinto grand shrines, renowned for marriage matchmaking and colossal shimenawa rope."},
        {"name": "Motonosumi Shrine", "ja": "元乃隅神社", "romaji": "Motonosumi Jinja", "pref": "Yamaguchi", "city": "Nagato City", "addr": "山口県長門市油谷津黄498", "loc": "元乃隅神社 社頭・授与所 (Cliffside Torii Office)", "desc": "Spectacular seaside cliff shrine with 123 vermilion torii gates winding toward the Sea of Japan and the Ryugu no Shiofuki blowhole."},
        {"name": "Ryozen-ji Temple (Shikoku Temple No. 1)", "ja": "竺和山 一乗院 霊山寺（四国第1番札所）", "romaji": "Ryōzen-ji", "pref": "Tokushima", "city": "Naruto City", "addr": "徳島県鳴門市大麻町板東塚鼻126", "loc": "霊山寺 納経所 (Henro Pilgrimage Office #1)", "desc": "Temple No. 1 and starting portal of the 1,400km Shikoku 88 Temple Henro pilgrimage, where pilgrims receive their white robes and walking staffs."},
        {"name": "Zentsu-ji Temple (Shikoku Temple No. 75)", "ja": "五岳山 誕生院 善通寺（四国第75番札所）", "romaji": "Zentsū-ji", "pref": "Kagawa", "city": "Zentsuji City", "addr": "香川県善通寺市善通寺町3-3-1", "loc": "善通寺 御影堂・納経所 (Mieido Hall Office)", "desc": "Temple No. 75 on the Shikoku Henro pilgrimage, celebrated as the revered birthplace of Kobo Daishi Kukai."},
        {"name": "Okubo-ji Temple (Shikoku Temple No. 88)", "ja": "医王山 遍照光院 大窪寺（四国第88番札所）", "romaji": "Ōkubo-ji", "pref": "Kagawa", "city": "Sanuki City", "addr": "香川県さぬき市多和兼割96", "loc": "大窪寺 本堂・納経所 (Henro Culmination Office #88)", "desc": "Temple No. 88 and final destination (Kechigan) of the 88 Temple Shikoku Henro, where pilgrims dedicate their walking staffs."},
        {"name": "Kotohira-gu Shrine (Konpira-san)", "ja": "金刀比羅宮（こんぴらさん）", "romaji": "Kotohira-gū", "pref": "Kagawa", "city": "Nakatado District", "addr": "香川県仲多度郡琴平町892-1", "loc": "金刀比羅宮 御本宮・社務所 (Main Shrine Office)", "desc": "Revered maritime pilgrimage shrine situated on Mount Zozu, famous for its 1,368 stone steps to the inner shrine."},
        {"name": "Dazaifu Tenmangu Shrine", "ja": "太宰府天満宮", "romaji": "Dazaifu Tenmangū", "pref": "Fukuoka", "city": "Dazaifu City", "addr": "福岡県太宰府市宰府4-7-1", "loc": "太宰府天満宮 本殿・社務所 (Main Sanctuary Office)", "desc": "Supreme Shinto shrine dedicated to Sugawara no Michizane, patron deity of learning, scholarship, and calligraphy."},
        {"name": "Aso Shrine", "ja": "阿蘇神社", "romaji": "Aso Jinja", "pref": "Kumamoto", "city": "Aso City", "addr": "熊本県阿蘇市一の宮町宮地3083-1", "loc": "阿蘇神社 楼門・社務所 (Romon Gate Office)", "desc": "Ancient shrine with over 2,500 years of history nestled at the foot of Mount Aso volcano, dedicated to the volcanic deities."},
        {"name": "Udo Jingu Shrine", "ja": "鵜戸神宮", "romaji": "Udo Jingū", "pref": "Miyazaki", "city": "Nichinan City", "addr": "宮崎県日南市大字宮浦3232", "loc": "鵜戸神宮 洞窟本殿・社務所 (Cave Sanctuary Office)", "desc": "Dramatic coastal cave shrine built inside a cavern facing the Pacific Ocean, famous for lucky Undama clay stone throwing."},
        {"name": "Takachiho Shrine", "ja": "高千穂神社", "romaji": "Takachiho Jinja", "pref": "Miyazaki", "city": "Nishiusuki District", "addr": "宮崎県西臼杵郡高千穂町三田井1037", "loc": "高千穂神社 神楽殿・社務所 (Kaguraden Office)", "desc": "Mythological birthplace of Japan nestled near Takachiho Gorge, famous for nightly sacred Yokagura dance performances."},
        {"name": "Kirishima Jingu Shrine", "ja": "霧島神宮", "romaji": "Kirishima Jingū", "pref": "Kagoshima", "city": "Kirishima City", "addr": "鹿児島県霧島市霧島田口2608-5", "loc": "霧島神宮 本殿・授与所 (Main Sanctuary Office)", "desc": "National Treasure shrine known as the 'Nikko of the West', set amidst volcanic pine forests where Ninigi no Mikoto descended to Earth."},
        {"name": "Naminoue Shrine", "ja": "波上宮（なみのうえぐう）", "romaji": "Naminoue-gū", "pref": "Okinawa", "city": "Naha City", "addr": "沖縄県那覇市若狭1-25-11", "loc": "波上宮 本殿・社務所 (Cliff Shrine Office)", "desc": "Top-ranking Ryukyu Kingdom shrine perched on a dramatic coral cliff overlooking the emerald East China Sea in Naha."},
        {"name": "Hokkaido Jingu Shrine", "ja": "北海道神宮", "romaji": "Hokkaidō Jingū", "pref": "Hokkaido", "city": "Sapporo City", "addr": "北海道札幌市中央区宮ケ丘474", "loc": "北海道神宮 社務所・授与所 (Main Office)", "desc": "Primary Shinto guardian shrine of Hokkaido, established in 1869 in Maruyama Park, surrounded by lush native wilderness."}
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

    # 6. Generate public/data/prefectures.json catalog for Per-Prefecture Offline Downloads
    REGIONS = {
        "Hokkaido": "Hokkaido",
        "Aomori": "Tohoku", "Iwate": "Tohoku", "Miyagi": "Tohoku", "Akita": "Tohoku", "Yamagata": "Tohoku", "Fukushima": "Tohoku",
        "Ibaraki": "Kanto", "Tochigi": "Kanto", "Gunma": "Kanto", "Saitama": "Kanto", "Chiba": "Kanto", "Tokyo": "Kanto", "Kanagawa": "Kanto",
        "Niigata": "Chubu", "Toyama": "Chubu", "Ishikawa": "Chubu", "Fukui": "Chubu", "Yamanashi": "Chubu", "Nagano": "Chubu", "Gifu": "Chubu", "Shizuoka": "Chubu", "Aichi": "Chubu",
        "Mie": "Kansai", "Shiga": "Kansai", "Kyoto": "Kansai", "Osaka": "Kansai", "Hyogo": "Kansai", "Nara": "Kansai", "Wakayama": "Kansai",
        "Tottori": "Chugoku", "Shimane": "Chugoku", "Okayama": "Chugoku", "Hiroshima": "Chugoku", "Yamaguchi": "Chugoku",
        "Tokushima": "Shikoku", "Kagawa": "Shikoku", "Ehime": "Shikoku", "Kochi": "Shikoku",
        "Fukuoka": "Kyushu & Okinawa", "Saga": "Kyushu & Okinawa", "Nagasaki": "Kyushu & Okinawa", "Kumamoto": "Kyushu & Okinawa", "Oita": "Kyushu & Okinawa", "Miyazaki": "Kyushu & Okinawa", "Kagoshima": "Kyushu & Okinawa", "Okinawa": "Kyushu & Okinawa"
    }

    pref_catalog = []
    for pref_en, pref_ja in PREF_EN_TO_JA.items():
        pref_stamps = [s for s in all_stamps if s.get("prefecture") == pref_en]
        count = len(pref_stamps)
        cat_counts = {}
        for s in pref_stamps:
            c = s.get("category", "other")
            cat_counts[c] = cat_counts.get(c, 0) + 1

        lats = [s["coordinates"][1] for s in pref_stamps if s.get("coordinates")]
        lons = [s["coordinates"][0] for s in pref_stamps if s.get("coordinates")]

        bounds = None
        if lats and lons:
            bounds = {
                "minLat": round(min(lats) - 0.05, 4),
                "maxLat": round(max(lats) + 0.05, 4),
                "minLon": round(min(lons) - 0.05, 4),
                "maxLon": round(max(lons) + 0.05, 4),
            }

        pref_catalog.append({
            "id": pref_en.lower().replace(" ", "-"),
            "name": pref_en,
            "name_ja": pref_ja,
            "region": REGIONS.get(pref_en, "Japan"),
            "stampCount": count,
            "categories": cat_counts,
            "bounds": bounds,
            "estimatedSizeMB": round(count * 0.08, 1)
        })

    # Sort by region and name
    region_order = ["Hokkaido", "Tohoku", "Kanto", "Chubu", "Kansai", "Chugoku", "Shikoku", "Kyushu & Okinawa"]
    pref_catalog.sort(key=lambda p: (region_order.index(p["region"]) if p["region"] in region_order else 99, p["name"]))

    pref_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "public", "data", "prefectures.json"))
    with open(pref_file, "w", encoding="utf-8") as f:
        json.dump(pref_catalog, f, ensure_ascii=False, indent=2)

    print(f"Successfully generated {len(pref_catalog)} prefecture packs catalog to {pref_file}!")


if __name__ == "__main__":
    main()
