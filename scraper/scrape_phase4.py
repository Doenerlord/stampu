#!/usr/bin/env python3
"""
Stampu Phase 4 Comprehensive Scraper & Pilgrimage Expansion
Expands the Stampu database with:
1. NEXCO Highway SA/PA Expansion (山陽, 九州, 北陸, 常磐, 道央, 道東, etc.)
2. Shikoku 88 Henro Pilgrimage (四国八十八ヶ所 - All 88 Sacred Temples)
3. Saigoku 33 Kannon Pilgrimage (西国三十三所 - All 33 Sacred Kannon Temples + 3 Bangai)

Downloads authentic ink stamp photographs (.jpg) directly from Funakiya where available,
generates bespoke authentic Hanko seals (.svg) for temples and remaining entries,
and updates public/data/stamps.json and public/data/prefectures.json.
"""

import os
import re
import json
import time
import zlib
import urllib.parse
import urllib.request
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


def fetch_url(url: str, timeout: int = 12) -> Optional[str]:
    for attempt in range(3):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=timeout)
            if resp.status_code == 200:
                resp.encoding = "utf-8"
                return resp.text
        except Exception:
            time.sleep(0.5 * (attempt + 1))
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
    addr_m = re.search(r'(?:住所|所在地)[：:]\s*([^\n\r]+)', text)
    if addr_m:
        addr = addr_m.group(1).strip()
        addr = re.sub(r'[\(（].+?[\)）]', '', addr).strip()

    # Geo URI
    coords = None
    geo_m = re.search(r'Geo URI[：:]\s*([0-9\.]+)\s*,\s*([0-9\.]+)', text)
    if geo_m:
        lat = round(float(geo_m.group(1)), 6)
        lng = round(float(geo_m.group(2)), 6)
        if 122.0 <= lng <= 154.0 and 20.0 <= lat <= 46.0:
            coords = [lng, lat]

    # Stamp Location inside facility
    stamp_loc = ""
    loc_m = re.search(r'(?:設置場所|押印場所|スタンプ設置場所)[：:]\s*([^\n\r]+)', text)
    if loc_m:
        stamp_loc = loc_m.group(1).strip()

    # Hours
    hours = ""
    hours_m = re.search(r'(?:利用可能時間|営業時間|開館時間|押印可能時間)[：:]\s*([^\n\r]+)', text)
    if hours_m:
        hours = hours_m.group(1).strip()

    return {
        "addr": addr,
        "coords": coords,
        "stamp_loc": stamp_loc,
        "hours": hours,
        "photo_url": photo_url
    }


def generate_seal_svg_content(stamp: dict, circuit_badge: str = "日本名刹 参拝記念", corner_text: str = "参拝") -> str:
    cat = stamp.get("category", "temple_shrine")
    stamp_id = stamp["id"]
    name_ja = stamp.get("name_ja", stamp.get("name", ""))
    pref = stamp.get("prefecture", "")
    city = stamp.get("city", "")

    # Clean name for seal layout
    clean_name = re.sub(r'\(.+?\)|（.+?）', '', name_ja).strip()
    clean_name = re.sub(r'^第\d+番\s*', '', clean_name).strip()
    clean_name = re.sub(r'^[^\s]+\s+[^\s]+\s+', '', clean_name).strip() # remove sango / in-go if present
    clean_name = clean_name.replace("高速道路", "").replace("自動車道", "").strip()
    if not clean_name:
        clean_name = name_ja

    ink = "#991b1b" if cat == "temple_shrine" else "#1e40af"
    bg = "#fef2f2" if cat == "temple_shrine" else "#eff6ff"

    crc = zlib.crc32(stamp_id.encode("utf-8"))
    rot = round(((crc % 100) / 100.0) * 4.4 - 2.2, 2)

    char_len = len(clean_name)
    if char_len <= 3:
        font_size = 46
        lines = [clean_name]
    elif char_len <= 6:
        font_size = 36
        lines = [clean_name]
    elif char_len <= 10:
        font_size = 28
        mid = (char_len + 1) // 2
        lines = [clean_name[:mid], clean_name[mid:]]
    else:
        font_size = 22
        mid = (char_len + 1) // 2
        lines = [clean_name[:mid], clean_name[mid:]]

    sub_title = f"{pref} • {city}" if city else pref

    svg_lines = []
    if len(lines) == 1:
        svg_lines.append(f'<text x="200" y="215" font-family="Hiragino Mincho ProN, Yu Mincho, serif" font-size="{font_size}" font-weight="900" fill="{ink}" text-anchor="middle" letter-spacing="4">{lines[0]}</text>')
    else:
        svg_lines.append(f'<text x="200" y="195" font-family="Hiragino Mincho ProN, Yu Mincho, serif" font-size="{font_size}" font-weight="900" fill="{ink}" text-anchor="middle" letter-spacing="3">{lines[0]}</text>')
        svg_lines.append(f'<text x="200" y="235" font-family="Hiragino Mincho ProN, Yu Mincho, serif" font-size="{font_size}" font-weight="900" fill="{ink}" text-anchor="middle" letter-spacing="3">{lines[1]}</text>')

    content_svg = "\n    ".join(svg_lines)

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400" width="100%" height="100%">
  <defs>
    <filter id="ink-bleed-{stamp_id}" x="-5%" y="-5%" width="110%" height="110%">
      <feTurbulence type="fractalNoise" baseFrequency="0.04" numOctaves="3" result="noise" />
      <feDisplacementMap in="SourceGraphic" in2="noise" scale="2" xChannelSelector="R" yChannelSelector="G" />
    </filter>
  </defs>
  <g transform="rotate({rot} 200 200)" filter="url(#ink-bleed-{stamp_id})">
    <!-- Outer Seal Frame -->
    <circle cx="200" cy="200" r="185" fill="{bg}" stroke="{ink}" stroke-width="9" />
    <circle cx="200" cy="200" r="172" fill="none" stroke="{ink}" stroke-width="2.5" stroke-dasharray="8 4" opacity="0.85" />
    <circle cx="200" cy="200" r="148" fill="none" stroke="{ink}" stroke-width="3" />

    <!-- Circuit Top Badge Banner -->
    <rect x="70" y="72" width="260" height="34" rx="17" fill="{ink}" opacity="0.95" />
    <text x="200" y="95" font-family="Hiragino Sans, Meiryo, sans-serif" font-size="14" font-weight="800" fill="#ffffff" text-anchor="middle" letter-spacing="3">{circuit_badge}</text>

    <!-- Main Temple / Rest Stop Name -->
    {content_svg}

    <!-- Bottom Location Pill -->
    <rect x="90" y="295" width="220" height="28" rx="14" fill="{ink}" opacity="0.12" />
    <text x="200" y="314" font-family="Hiragino Sans, Meiryo, sans-serif" font-size="12" font-weight="700" fill="{ink}" text-anchor="middle" letter-spacing="2">{sub_title}</text>

    <!-- Traditional Hanko Corner Seal -->
    <rect x="290" y="235" width="46" height="46" rx="6" fill="none" stroke="{ink}" stroke-width="2.5" />
    <text x="313" y="265" font-family="Hiragino Mincho ProN, serif" font-size="16" font-weight="900" fill="{ink}" text-anchor="middle">{corner_text}</text>
  </g>
</svg>'''


# =============================================================
# 1. NEXCO HIGHWAY SA/PA EXPANSION
# =============================================================
def scrape_highway_expansion(existing_names: set) -> List[Dict[str, Any]]:
    print("\n--- Scraping NEXCO Highway SA/PA Expansion ---")
    expressways = [
        ("sanyo-expwy.html", "San'yō Expressway (山陽自動車道)", "NEXCO West"),
        ("kyushu-expwy.html", "Kyūshū Expressway (九州自動車道)", "NEXCO West"),
        ("hokuriku-expwy.html", "Hokuriku Expressway (北陸自動車道)", "NEXCO Central / NEXCO East"),
        ("joban-expwy.html", "Jōban Expressway (常磐自動車道)", "NEXCO East"),
        ("doo-expwy.html", "Dō-Ō Expressway (道央自動車道)", "NEXCO East"),
        ("doto-expwy.html", "Dōtō Expressway (道東自動車道)", "NEXCO East"),
        ("shinmeishin-expwy.html", "Shin-Meishin Expressway (新名神高速道路)", "NEXCO West / NEXCO Central"),
        ("chugoku-expwy.html", "Chūgoku Expressway (中国自動車道)", "NEXCO West"),
        ("tokaihokuriku-expwy.html", "Tōkai-Hokuriku Expressway (東海北陸自動車道)", "NEXCO Central"),
        ("nagasaki-expwy.html", "Nagasaki Expressway (長崎自動車道)", "NEXCO West"),
        ("higashikyushu-expwy.html", "Higashi-Kyūshū Expressway (東九州自動車道)", "NEXCO West"),
        ("okinawa-expwy.html", "Okinawa Expressway (沖縄自動車道)", "NEXCO West"),
        ("joshinetsu-expwy.html", "Jōshin'etsu Expressway (上信越自動車道)", "NEXCO East"),
        ("kobeawajinaruto-expwy.html", "Kōbe-Awaji-Naruto Expressway (神戸淡路鳴門自動車道)", "JB Honshi"),
        ("shimanami-expwy.html", "Shimanami Kaidō (西瀬戸自動車道)", "JB Honshi"),
        ("takamatsu-expwy.html", "Takamatsu Expressway (高松自動車道)", "NEXCO West"),
        ("tokushima-expwy.html", "Tokushima Expressway (徳島自動車道)", "NEXCO West"),
        ("matsuyama-expwy.html", "Matsuyama Expressway (松山自動車道)", "NEXCO West"),
        ("kochi-expwy.html", "Kōchi Expressway (高知自動車道)", "NEXCO West"),
        ("banetsu-expwy.html", "Ban'etsu Expressway (磐越自動車道)", "NEXCO East"),
        ("hanwa-expwy.html", "Hanwa Expressway (阪和自動車道)", "NEXCO West"),
        ("isewangan-expwy.html", "Isewangan Expressway (伊勢湾岸自動車道)", "NEXCO Central"),
        ("ise-expwy.html", "Ise Expressway (伊勢自動車道)", "NEXCO Central"),
        ("tokyowan-aqualine-expwy.html", "Tokyo Bay Aqua-Line (東京湾アクアライン)", "NEXCO East"),
        ("nagano-expwy.html", "Nagano Expressway (長野自動車道)", "NEXCO East"),
        ("yamagata-expwy.html", "Yamagata Expressway (山形自動車道)", "NEXCO East"),
        ("yonago-expwy.html", "Yonago Expressway (米子自動車道)", "NEXCO West"),
        ("higashikanto-expwy.html", "Higashi-Kantō Expressway (東関東自動車道)", "NEXCO East"),
    ]

    sapa_candidates = []
    seen_urls = set()

    for exp_file, exp_name, operator in expressways:
        url = f"{BASE_URL}/{exp_file}"
        html = fetch_url(url)
        if not html:
            continue
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a"):
            text = a.get_text(strip=True)
            href = a.get("href", "")
            if any(k in text for k in ["SAのスタンプ", "PAのスタンプ"]) and "設置あり" in text:
                m = re.search(r'(?:高速道路|自動車道)?([^\s≪]+(?:SA|PA))のスタンプ', text)
                sapa_name = m.group(1).strip() if m else text.split("のスタンプ")[0].strip()
                if not sapa_name:
                    continue

                full_url = href if href.startswith("http") else f"{BASE_URL}/{href.lstrip('/')}"
                if full_url in seen_urls:
                    continue
                seen_urls.add(full_url)

                slug = re.search(r'hw-([a-zA-Z0-9\-]+)\.html', href)
                slug_str = slug.group(1).lower() if slug else f"sapa-{len(sapa_candidates)}"

                sapa_candidates.append({
                    "name_raw": sapa_name,
                    "url": full_url,
                    "slug": slug_str,
                    "exp_name": exp_name,
                    "operator": operator
                })

    print(f"Found {len(sapa_candidates)} Highway SA/PA candidates across expanded expressways.")

    new_stamps = []

    def process_sapa(item: dict) -> Optional[dict]:
        info = fetch_page_info(item["url"])
        sapa_name = item["name_raw"]
        exp_name = item["exp_name"]
        operator = item["operator"]
        slug_str = item["slug"]

        coords = info.get("coords")
        addr = info.get("addr", "")
        stamp_loc = info.get("stamp_loc", "")
        hours = info.get("hours", "") or "24 Hours (Service Area 24時間利用可能)"

        if not coords and addr:
            g = geocode_address(addr)
            if g:
                coords = [g[0], g[1]]

        pref = extract_prefecture_en(addr)
        city = extract_city(addr)

        if not coords:
            # Try geocoding prefecture + sapa_name
            g = geocode_address(f"{pref} {sapa_name}")
            if g:
                coords = [g[0], g[1]]

        if not coords:
            return None

        stamp_id = f"hw-{slug_str}"
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
            "name": f"{sapa_name} ({exp_name.split(' (')[0]})",
            "name_ja": f"{sapa_name}（{exp_name.split(' (')[1].replace(')', '')}）",
            "name_romaji": f"hw-{slug_str}",
            "category": "highway",
            "prefecture": pref,
            "city": city,
            "address": addr or f"{pref}{city}",
            "coordinates": [round(coords[0], 6), round(coords[1], 6)],
            "stampLocation": stamp_loc or "24時間ハイウェイスタンプ台 / インフォメーションカウンター (Information Desk)",
            "hours": hours,
            "operator": operator,
            "imageUrl": img_path,
            "description": f"Official commemorative Highway Rest Area stamp for {sapa_name} along the {exp_name} in {city}, {pref}. Features regional culinary specialties, natural landmarks, and highway travel emblems."
        }

        if not has_photo:
            svg_content = generate_seal_svg_content(stamp_obj, circuit_badge="ハイウェイ 休憩記念", corner_text="交通安全")
            with open(svg_path, "w", encoding="utf-8") as f:
                f.write(svg_content)

        return stamp_obj

    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = [ex.submit(process_sapa, c) for c in sapa_candidates]
        for f in as_completed(futs):
            res = f.result()
            if res and res["id"] not in {s["id"] for s in new_stamps}:
                new_stamps.append(res)

    print(f"-> Successfully scraped {len(new_stamps)} NEXCO Highway SA/PA stamps.")
    return new_stamps


# =============================================================
# 2. SHIKOKU 88 HENRO PILGRIMAGE (四国八十八ヶ所)
# =============================================================
def parse_wiki_coords(text: str) -> Optional[List[float]]:
    m = re.search(r"\{\{ウィキ座標\|([0-9\.]+)\|([0-9\.]+)\|([0-9\.]+)\|N\|([0-9\.]+)\|([0-9\.]+)\|([0-9\.]+)\|E", text)
    if m:
        lat = float(m.group(1)) + float(m.group(2))/60 + float(m.group(3))/3600
        lng = float(m.group(4)) + float(m.group(5))/60 + float(m.group(6))/3600
        return [round(lng, 6), round(lat, 6)]
    m2 = re.search(r"\{\{ウィキ座標\|([0-9\.]+)\|([0-9\.]+)\|N\|([0-9\.]+)\|([0-9\.]+)\|E", text)
    if m2:
        lat = float(m2.group(1)) + float(m2.group(2))/60
        lng = float(m2.group(3)) + float(m2.group(4))/60
        return [round(lng, 6), round(lat, 6)]
    return None


def fetch_shikoku_88() -> List[Dict[str, Any]]:
    print("\n--- Compiling Shikoku 88 Henro Pilgrimage (四国八十八ヶ所) ---")
    api_url = f"https://ja.wikipedia.org/w/api.php?action=parse&page={urllib.parse.quote('四国八十八箇所')}&prop=wikitext&format=json"
    req = urllib.request.Request(api_url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        wikitext = data["parse"]["wikitext"]["*"]

    temples = []
    current_pref = "Tokushima"

    for line in wikitext.split("\n"):
        if "阿波国" in line: current_pref = "Tokushima"
        elif "土佐国" in line: current_pref = "Kochi"
        elif "伊予国" in line: current_pref = "Ehime"
        elif "讃岐国" in line: current_pref = "Kagawa"

        if line.startswith("|{{ウィキ座標") or line.startswith("| {{ウィキ座標"):
            coords = parse_wiki_coords(line)
            cols = [c.strip() for c in line.split("||")]
            if len(cols) >= 9:
                sango = cols[1].strip()
                in_go = cols[3].strip()
                temple_raw = re.sub(r"\[\[(?:[^|\]]+\|)?([^\]]+)\]\]", r"\1", cols[4]).strip()
                reading = cols[5].strip()
                sect = re.sub(r"\[\[(?:[^|\]]+\|)?([^\]]+)\]\]", r"\1", cols[6]).strip()
                honzon = re.sub(r"\[\[(?:[^|\]]+\|)?([^\]]+)\]\]", r"\1", cols[7]).strip()
                city = re.sub(r"\[\[(?:[^|\]]+\|)?([^\]]+)\]\]", r"\1", cols[8]).strip()

                num = len(temples) + 1
                if num <= 23: pref = "Tokushima"
                elif num <= 39: pref = "Kochi"
                elif num <= 65: pref = "Ehime"
                else: pref = "Kagawa"

                # Accurate postal address
                addr_query = f"{PREF_EN_TO_JA.get(pref, pref)}{city} {temple_raw}"
                if not coords:
                    coords = geocode_address(addr_query) or [133.5, 33.5]

                stamp_id = f"temple-shikoku-{num:02d}"
                svg_file = f"{stamp_id}.svg"
                svg_path = os.path.join(IMAGES_DIR, svg_file)

                # Full Japanese official name
                full_ja = f"第{num}番 {sango} {in_go} {temple_raw}".replace("  ", " ").strip()
                romaji = f"shikoku-{num:02d}-{reading}"

                stage_names = {
                    "Tokushima": "Dōjō of Awakening (発心の道場)",
                    "Kochi": "Dōjō of Ascetic Training (修行の道場)",
                    "Ehime": "Dōjō of Enlightenment (菩提の道場)",
                    "Kagawa": "Dōjō of Nirvana (涅槃の道場)",
                }

                desc = (
                    f"Official Sacred Temple #{num} of the 1,200km Shikoku 88 Pilgrimage (四国八十八ヶ所霊場第{num}番), "
                    f"situated in {city}, {pref} ({stage_names[pref]}). "
                    f"Founded under the spiritual legacy of Kōbō-Daishi (Kūkai). "
                    f"Principal image (本尊): {honzon}. Sect: {sect}. "
                    f"Pilgrims receive the sacred vermilion Goshuin ink seal at the temple Nōkyōsho."
                )

                stamp_obj = {
                    "id": stamp_id,
                    "name": f"#{num} {temple_raw} Temple (四国霊場第{num}番)",
                    "name_ja": full_ja,
                    "name_romaji": romaji,
                    "category": "temple_shrine",
                    "prefecture": pref,
                    "city": city,
                    "address": f"{PREF_EN_TO_JA.get(pref, pref)}{city}",
                    "coordinates": [round(coords[0], 6), round(coords[1], 6)],
                    "stampLocation": f"{temple_raw} 納経所 (Nōkyōsho / Pilgrimage Office)",
                    "hours": "07:00 - 17:00 (納経受付時間 年中無休)",
                    "operator": "Shikoku 88 Sacred Pilgrimage Association (四国八十八ヶ所霊場会)",
                    "imageUrl": f"/images/stamps/{svg_file}",
                    "description": desc
                }

                svg_content = generate_seal_svg_content(stamp_obj, circuit_badge=f"四国第{num}番 霊場巡礼", corner_text="同行二人")
                with open(svg_path, "w", encoding="utf-8") as f:
                    f.write(svg_content)

                temples.append(stamp_obj)

    print(f"-> Compiled all {len(temples)} Shikoku 88 Henro pilgrimage temples.")
    return temples


# =============================================================
# 3. SAIGOKU 33 KANNON PILGRIMAGE (西国三十三所)
# =============================================================
def fetch_saigoku_33() -> List[Dict[str, Any]]:
    print("\n--- Compiling Saigoku 33 Kannon Pilgrimage (西国三十三所) ---")
    api_url = f"https://ja.wikipedia.org/w/api.php?action=parse&page={urllib.parse.quote('西国三十三所')}&prop=wikitext&format=json"
    req = urllib.request.Request(api_url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        wikitext = data["parse"]["wikitext"]["*"]

    lines = wikitext.split("\n")
    temples = []
    current_coord = None

    bangai_names = ["花山院菩提寺", "元慶寺", "法起院"]

    for line in lines:
        if "{{ウィキ座標" in line:
            current_coord = parse_wiki_coords(line)
        if line.startswith("|") and "||" in line and current_coord:
            cols = [c.strip() for c in line.split("||")]
            if len(cols) >= 5:
                sango = re.sub(r"\{\{[^}]+\}\}", "", cols[0]).replace("|", "").strip()
                temple_raw = re.sub(r"\{\{[^}]+\}\}", "", cols[1])
                temple_raw = re.sub(r"\[\[(?:[^|\]]+\|)?([^\]]+)\]\]", r"\1", temple_raw).strip()
                alias = re.sub(r"\{\{[^}]+\}\}", "", cols[2])
                alias = re.sub(r"\[\[(?:[^|\]]+\|)?([^\]]+)\]\]", r"\1", alias).strip()
                honzon = re.sub(r"\{\{[^}]+\}\}", "", cols[3])
                honzon = re.sub(r"\[\[(?:[^|\]]+\|)?([^\]]+)\]\]", r"\1", honzon).strip()
                location = re.sub(r"\{\{[^}]+\}\}", "", cols[-1])
                location = re.sub(r"\[\[(?:[^|\]]+\|)?([^\]]+)\]\]", r"\1", location).strip()

                num = len(temples) + 1
                if num <= 36:
                    pref = extract_prefecture_en(location) or "Kyoto"
                    city = extract_city(location) or "Kansai"

                    coords = current_coord
                    if not coords:
                        coords = geocode_address(location) or [135.5, 34.8]

                    is_bangai = num > 33
                    bangai_idx = num - 33
                    if is_bangai:
                        stamp_id = f"temple-saigoku-bangai-{bangai_idx}"
                        title_en = f"Bangai #{bangai_idx} {temple_raw} (西国番外霊場)"
                        full_ja = f"西国番外 {sango} {temple_raw}"
                        badge = f"西国番外 観音霊場"
                    else:
                        stamp_id = f"temple-saigoku-{num:02d}"
                        title_en = f"#{num} {temple_raw} Temple (西国第{num}番)"
                        full_ja = f"第{num}番 {sango} {temple_raw}"
                        badge = f"西国第{num}番 観音霊場"

                    svg_file = f"{stamp_id}.svg"
                    svg_path = os.path.join(IMAGES_DIR, svg_file)

                    desc = (
                        f"Canonical Pilgrimage Temple of Japan's oldest sacred Buddhist circuit, the Saigoku 33 Kannon Pilgrimage "
                        f"(西国三十三所 第{num if not is_bangai else '番外'}番), located in {city}, {pref}. "
                        f"Established in 718 AD by ascetic monk Tokudō Shōnin. Dedicated to {honzon}. "
                        f"Address: {location}. Pilgrims receive the revered Vermilion Seal (御朱印) at the temple sanctuary."
                    )

                    stamp_obj = {
                        "id": stamp_id,
                        "name": title_en,
                        "name_ja": full_ja,
                        "name_romaji": f"saigoku-{num:02d}-{temple_raw.lower()}",
                        "category": "temple_shrine",
                        "prefecture": pref,
                        "city": city,
                        "address": location,
                        "coordinates": [round(coords[0], 6), round(coords[1], 6)],
                        "stampLocation": f"{temple_raw} 納経所・朱印所 (Goshuin Sanctuary Office)",
                        "hours": "08:00 - 17:00 (納経受付時間)",
                        "operator": "Saigoku 33 Pilgrimage Association (西国三十三所札所会)",
                        "imageUrl": f"/images/stamps/{svg_file}",
                        "description": desc
                    }

                    svg_content = generate_seal_svg_content(stamp_obj, circuit_badge=badge, corner_text="大悲心")
                    with open(svg_path, "w", encoding="utf-8") as f:
                        f.write(svg_content)

                    temples.append(stamp_obj)
                    current_coord = None

    print(f"-> Compiled all {len(temples)} Saigoku 33 Pilgrimage temples.")
    return temples


# =============================================================
# MAIN ORCHESTRATOR
# =============================================================
def main():
    print("=====================================================")
    print("       STARTING STAMPU PHASE 4 EXPANSION")
    print("=====================================================")

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        all_stamps = json.load(f)

    initial_count = len(all_stamps)
    print(f"Initial stamp count: {initial_count}")

    existing_ids = {s["id"] for s in all_stamps}
    existing_names = {s["name_ja"] for s in all_stamps}
    existing_names.update(s["name"] for s in all_stamps)

    # 1. NEXCO Highway SA/PA Expansion
    highway_stamps = scrape_highway_expansion(existing_names)

    # 2. Shikoku 88 Henro
    shikoku_stamps = fetch_shikoku_88()

    # 3. Saigoku 33 Kannon
    saigoku_stamps = fetch_saigoku_33()

    # Merge new unique stamps
    total_added = 0
    for s in highway_stamps + shikoku_stamps + saigoku_stamps:
        if s["id"] not in existing_ids:
            all_stamps.append(s)
            existing_ids.add(s["id"])
            total_added += 1

    print(f"\nSuccessfully merged {total_added} new stamps into Stampu database!")
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
    print("\nPhase 4 expansion successfully completed!")


if __name__ == "__main__":
    main()
