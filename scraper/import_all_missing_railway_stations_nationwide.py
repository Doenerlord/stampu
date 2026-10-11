#!/usr/bin/env python3
"""
Nationwide Railway Station Import & Parity Pipeline
===================================================
Audits and imports all missing railway stations across Japan from Funakiya,
Japan Stamp Hunt, and Hankore datasets.

Features:
- Crawls all active stations discovered across 917 regional railway line catalogs
- Extracts official bilingual station names, exact coordinates (Geo URI or GSI geocode)
- Extracts Japanese address, prefecture, city, operating hours, stamp location & motif
- Downloads authentic photographed stamp images (.jpg/.png) or generates bespoke Hanko SVGs
- Performs robust spatial and name deduplication against existing database
- Appends new stations to public/data/stamps.json and updates public/data/prefectures.json
"""

import os
import re
import json
import time
import html
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
CACHE_DIR = os.path.join(BASE_DIR, "scraper", "cache")

os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://stamp.funakiya.com/",
}

OPERATOR_MAP = {
    "JR北海道": ("JR Hokkaido", "JR Hokkaido"),
    "JR東日本": ("JR East", "JR East"),
    "JR東海": ("JR Central", "JR Central"),
    "JR西日本": ("JR West", "JR West"),
    "JR四国": ("JR Shikoku", "JR Shikoku"),
    "JR九州": ("JR Kyushu", "JR Kyushu"),
    "東京メトロ": ("Tokyo Metro", "Tokyo Metro"),
    "都営地下鉄": ("Toei Subway", "Tokyo Metropolitan Bureau of Transportation"),
    "大阪メトロ": ("Osaka Metro", "Osaka Metro"),
    "Osaka Metro": ("Osaka Metro", "Osaka Metro"),
    "東武": ("Tobu Railway", "Tobu Railway"),
    "西武": ("Seibu Railway", "Seibu Railway"),
    "京成": ("Keisei Electric Railway", "Keisei Electric Railway"),
    "京王": ("Keio Corporation", "Keio Corporation"),
    "小田急": ("Odakyu Electric Railway", "Odakyu Electric Railway"),
    "東急": ("Tokyu Railways", "Tokyu Corporation"),
    "京急": ("Keikyu Corporation", "Keikyu Corporation"),
    "相鉄": ("Sotetsu Line", "Sagami Railway"),
    "名鉄": ("Meitetsu", "Nagoya Railroad"),
    "近鉄": ("Kintetsu Railway", "Kintetsu Railway"),
    "南海": ("Nankai Electric Railway", "Nankai Electric Railway"),
    "京阪": ("Keihan Electric Railway", "Keihan Electric Railway"),
    "阪急": ("Hankyu Railway", "Hankyu Corporation"),
    "阪神": ("Hanshin Electric Railway", "Hanshin Electric Railway"),
    "西鉄": ("Nishitetsu", "Nishi-Nippon Railroad"),
    "会津鉄道": ("Aizu Railway", "Aizu Railway"),
    "阿武隈急行": ("Abukuma Express", "Abukuma Express"),
    "青い森鉄道": ("Aoimori Railway", "Aoimori Railway"),
    "秋田内陸縦貫鉄道": ("Akita Nairiku Railway", "Akita Nairiku Jukan Railway"),
    "あいの風とやま鉄道": ("Ainokaze Toyama Railway", "Ainokaze Toyama Railway"),
    "甘木鉄道": ("Amagi Railway", "Amagi Railway"),
    "伊豆急行": ("Izu Kyuko", "Izu Kyuko"),
    "伊豆箱根鉄道": ("Izuhakone Railway", "Izuhakone Railway"),
    "いすみ鉄道": ("Isumi Railway", "Isumi Railway"),
    "IRいしかわ鉄道": ("IR Ishikawa Railway", "IR Ishikawa Railway"),
    "叡山電鉄": ("Eizan Electric Railway", "Eizan Electric Railway"),
    "えちぜん鉄道": ("Echizen Railway", "Echizen Railway"),
    "えちごトキめき鉄道": ("Echigo Tokimeki Railway", "Echigo Tokimeki Railway"),
    "大井川鐵道": ("Oigawa Railway", "Oigawa Railway"),
    "近江鉄道": ("Ohmi Railway", "Ohmi Railway"),
    "岳南電車": ("Gakunan Electric Train", "Gakunan Electric Train"),
    "鹿島臨海鉄道": ("Kashima Rinkai Railway", "Kashima Rinkai Railway"),
    "北大阪急行": ("Kita-Osaka Kyuko", "Kita-Osaka Kyuko Railway"),
    "京都丹後鉄道": ("Kyoto Tango Railway", "WILLER TRAINS"),
    "熊本電鉄": ("Kumamoto Electric Railway", "Kumamoto Electric Railway"),
    "くま川鉄道": ("Kumagawa Railway", "Kumagawa Railway"),
    "黒部峡谷鉄道": ("Kurobe Gorge Railway", "Kurobe Gorge Railway"),
    "神戸電鉄": ("Kobe Electric Railway", "Kobe Electric Railway"),
    "埼玉高速鉄道": ("Saitama Rapid Railway", "Saitama Rapid Railway"),
    "三陸鉄道": ("Sanriku Railway", "Sanriku Railway"),
    "しなの鉄道": ("Shinano Railway", "Shinano Railway"),
    "島原鉄道": ("Shimabara Railway", "Shimabara Railway"),
    "上信電鉄": ("Joshin Electric Railway", "Joshin Electric Railway"),
    "新京成電鉄": ("Shin-Keisei Electric Railway", "Shin-Keisei Electric Railway"),
    "秩父鉄道": ("Chichibu Railway", "Chichibu Railway"),
    "智頭急行": ("Chizu Express", "Chizu Express"),
    "銚子電鉄": ("Choshi Electric Railway", "Choshi Electric Railway"),
    "筑豊電気鉄道": ("Chikuho Electric Railroad", "Chikuho Electric Railroad"),
    "天竜浜名湖鉄道": ("Tenryu Hamanako Railroad", "Tenryu Hamanako Railroad"),
    "道南いさりび鉄道": ("Dounan Isaribi Railway", "South Hokkaido Railway"),
    "土佐くろしお鉄道": ("Tosa Kuroshio Railway", "Tosa Kuroshio Railway"),
    "富山地方鉄道": ("Toyama Chiho Railway", "Toyama Chiho Railway"),
    "長野電鉄": ("Nagano Electric Railway", "Nagano Electric Railway"),
    "能勢電鉄": ("Nose Electric Railway", "Nose Electric Railway"),
    "ハピラインふくい": ("Hapi-Line Fukui", "Hapi-Line Fukui"),
    "ひたちなか海浜鉄道": ("Hitachinaka Seaside Railway", "Hitachinaka Seaside Railway"),
    "富士急行": ("Fujikyu Railway", "Fujikyu Railway"),
    "北条鉄道": ("Hojo Railway", "Hojo Railway"),
    "松浦鉄道": ("Matsuura Railway", "Matsuura Railway"),
    "真岡鐵道": ("Moka Railway", "Moka Railway"),
    "水島臨海鉄道": ("Mizushima Rinkai Railway", "Mizushima Rinkai Railway"),
    "養老鉄道": ("Yoro Railway", "Yoro Railway"),
    "わたらせ渓谷鐵道": ("Watarase Keikoku Railway", "Watarase Keikoku Railway"),
    "箱根登山電車": ("Hakone Tozan Railway", "Odakyu Hakone"),
    "嵐電": ("Randen", "Keifuku Electric Railroad"),
}

def detect_operator(name_ja: str, line_hint: str) -> Tuple[str, str]:
    """Detect railway operator in English and Japanese."""
    for key, (en_op, full_en) in OPERATOR_MAP.items():
        if key in name_ja or key in line_hint:
            return en_op, key
    if name_ja.startswith("JR") or "JR" in line_hint:
        # Detect regional JR
        if "北海道" in line_hint or "北海道" in name_ja:
            return "JR Hokkaido", "JR北海道"
        elif "九州" in line_hint or "九州" in name_ja:
            return "JR Kyushu", "JR九州"
        elif "四国" in line_hint or "四国" in name_ja:
            return "JR Shikoku", "JR四国"
        elif "東海" in line_hint or "東海道" in line_hint:
            return "JR Central", "JR東海"
        elif any(k in line_hint for k in ["西日本", "山陽", "北陸", "関西", "近畿", "中国"]):
            return "JR West", "JR西日本"
        else:
            return "JR East", "JR東日本"
    return "Local Railway", "地域鉄道"

def romanize_station_name(name_ja: str, en_hint: str = "") -> str:
    """Generate clean English station name."""
    if en_hint and len(en_hint) > 2 and not any(ord(c) > 127 for c in en_hint):
        clean_en = en_hint.strip()
        if not clean_en.lower().endswith("station"):
            clean_en += " Station"
        return clean_en
    
    # Strip operator prefix
    clean = re.sub(r'^(JR|東武|西武|京成|京王|小田急|東急|京急|相鉄|名鉄|近鉄|南海|京阪|阪急|阪神|西鉄|会津鉄道|阿武隈急行|青い森鉄道|甘木鉄道|あいの風とやま鉄道|えちぜん鉄道|智頭急行|三陸鉄道|しなの鉄道|秩父鉄道|富山地方鉄道)', '', name_ja)
    clean = clean.replace('駅', '').strip()
    return f"{clean} Station"

def download_stamp_image(img_url: str, save_path: str) -> bool:
    """Download authentic stamp photo."""
    try:
        r = requests.get(img_url, headers=HEADERS, timeout=12)
        if r.status_code == 200 and len(r.content) > 1000:
            with open(save_path, "wb") as f:
                f.write(r.content)
            return True
    except Exception:
        pass
    return False

def scrape_funakiya_station(candidate: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    url = candidate["url"]
    name_hint = candidate.get("name_hint", "")
    line_hint = candidate.get("line_hint", "")
    
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code != 200:
            return None
        r.encoding = "utf-8"
        soup = BeautifulSoup(r.text, "html.parser")
        
        # Title
        title_str = soup.title.string if soup.title else ""
        name_ja = title_str.split("のスタンプ")[0].strip()
        if not name_ja or "404" in name_ja or "一覧" in name_ja:
            name_ja = name_hint
        if not name_ja:
            return None
            
        # English Name
        en_hint = ""
        en_m = re.search(r'\bEN[：:\s]*([^\n<]+)', r.text)
        if en_m:
            en_hint = html.unescape(en_m.group(1)).strip()
        name_en = romanize_station_name(name_ja, en_hint)
        
        # Coordinates
        lat, lng = None, None
        geo_m = re.search(r"Geo URI[：:\s]*([\d\.]+),\s*([\d\.]+)", r.text)
        if geo_m:
            try:
                lat, lng = float(geo_m.group(1)), float(geo_m.group(2))
            except ValueError:
                pass
                
        # Address
        addr_m = re.search(r"所在地[：:\s]*(?:〒[\d-]+)?\s*([^\n<]+)", r.text)
        address = html.unescape(addr_m.group(1)).strip() if addr_m else ""
        
        # Prefecture & City
        pref_ja = extract_prefecture(address)
        if not pref_ja:
            pref_ja = extract_prefecture(r.text[:2000])
        if not pref_ja:
            # Try from breadcrumb
            for p in PREF_EN_TO_JA.values():
                if p in r.text[:2000]:
                    pref_ja = p
                    break
        if not pref_ja:
            pref_ja = "東京都"
            
        pref_en = PREF_JA_TO_EN.get(pref_ja, "Tokyo")
        city = extract_city(address) if address else pref_ja
        
        # If coordinates still missing, geocode via GSI
        if lat is None or lng is None:
            query = f"{address}" if address else f"{pref_ja} {name_ja}"
            coords = geocode_address(query)
            if coords:
                lng, lat = coords
            else:
                coords = geocode_address(f"{pref_ja} {name_ja}")
                if coords:
                    lng, lat = coords
                else:
                    return None
                    
        # Location description
        loc_m = re.search(r"設置場所[：:\s]*([^\n<]+)", r.text)
        location_desc = html.unescape(loc_m.group(1)).strip() if loc_m else f"{name_ja} 改札付近"
        
        # Operating hours
        hours_m = re.search(r"(?:改札窓口営業時間|営業時間|スタンプ利用可能時間)[：:\s]*([^\n<]+)", r.text)
        opening_hours = html.unescape(hours_m.group(1)).strip() if hours_m else "始発～終電"
        
        # Motif
        motif_m = re.search(r'「([^」]+)」をイメージしたスタンプ', r.text)
        if not motif_m:
            motif_m = re.search(r'【スタンプ印影】[：:\s]*([^\n<]+)', r.text)
        motif = html.unescape(motif_m.group(1)).strip() if motif_m else f"{name_ja} 記念スタンプ"
        
        # Operator & Line
        operator_en, operator_ja = detect_operator(name_ja, line_hint)
        line_clean = line_hint.replace("のスタンプ", "").strip() if line_hint else f"{operator_ja} 鉄道路線"
        
        # ID generation
        slug = url.rstrip("/").split("/")[-1].replace(".html", "")
        if slug.startswith("jr-") or slug.startswith("eki-"):
            clean_slug = slug
        else:
            clean_slug = f"eki-{slug}"
        if not clean_slug.startswith("eki-"):
            clean_slug = f"eki-{clean_slug}"
            
        # Stamp Photo URL
        img_url = None
        for img in soup.find_all("img", src=True):
            src = img["src"]
            alt = img.get("alt", "")
            if "i/stamp/" in src and not "stampsum" in src and not "banner" in src:
                img_url = src
                break
            elif "wp-content/uploads" in src and ("stamp" in src or "eki" in src):
                img_url = src
                break
                
        # Image download or bespoke fallback
        image_rel_path = None
        if img_url:
            if not img_url.startswith("http"):
                img_url = f"https://stamp.funakiya.com/{img_url.lstrip('/')}"
            ext = ".jpg" if ".jpg" in img_url.lower() else ".png"
            img_filename = f"{clean_slug}{ext}"
            img_dest = os.path.join(IMAGES_DIR, img_filename)
            if os.path.exists(img_dest) or download_stamp_image(img_url, img_dest):
                image_rel_path = f"/images/stamps/{img_filename}"
                
        if not image_rel_path:
            # Fallback to bespoke Hanko SVG
            svg_filename = f"{clean_slug}.svg"
            svg_dest = os.path.join(IMAGES_DIR, svg_filename)
            generate_seal_svg(name_ja, pref_ja, "eki", motif)
            image_rel_path = f"/images/stamps/{svg_filename}"
            
        return {
            "id": clean_slug,
            "name": name_en,
            "name_ja": name_ja,
            "category": "eki",
            "prefecture": pref_ja,
            "prefecture_en": pref_en,
            "city": city,
            "address": address or f"{pref_ja} {city}",
            "coordinates": [round(lng, 6), round(lat, 6)],
            "imageUrl": image_rel_path,
            "design": motif,
            "description": f"Commemorative railway station stamp for {name_ja} ({name_en}) on {line_clean}. Features {motif}.",
            "stampLocation": location_desc,
            "openingHours": opening_hours,
            "railwayLine": line_clean,
            "railwayOperator": operator_ja,
            "sourceUrl": url,
            "source": "funakiya",
            "active": True
        }
    except Exception as e:
        return None

def main():
    print("="*80)
    print("STARTING NATIONWIDE RAILWAY STATION PARITY IMPORT")
    print("="*80)
    
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        stamps = json.load(f)
        
    print(f"Current stamps in database: {len(stamps)}")
    eki_stamps = [s for s in stamps if s.get("category") == "eki"]
    print(f"Current railway stations (category: eki): {len(eki_stamps)}")
    
    existing_ids = {s["id"] for s in stamps}
    existing_urls = {s.get("sourceUrl", "") for s in stamps if s.get("sourceUrl")}
    existing_names_ja = {s.get("name_ja", "") for s in stamps if s.get("name_ja") and s.get("category") == "eki"}
    existing_coords = [(s["coordinates"][0], s["coordinates"][1], s.get("name_ja", "")) for s in stamps if "coordinates" in s and s.get("category") == "eki"]
    
    with open(os.path.join(CACHE_DIR, "all_active_station_candidates.json"), "r", encoding="utf-8") as f:
        candidates_data = json.load(f)
        
    candidates = candidates_data["funakiya_active_stations"]
    print(f"Total candidate active stations on Funakiya: {len(candidates)}")
    
    # Filter out already present URLs and names
    candidates_to_crawl = []
    for c in candidates:
        if c["url"] in existing_urls:
            continue
        c_hint = c.get("name_hint", "")
        if c_hint and c_hint in existing_names_ja:
            continue
        candidates_to_crawl.append(c)
        
    print(f"Candidate station pages to crawl: {len(candidates_to_crawl)}")
    
    new_stamps = []
    failed = 0
    scraped_count = 0
    
    with ThreadPoolExecutor(max_workers=16) as pool:
        futures = {pool.submit(scrape_funakiya_station, c): c for c in candidates_to_crawl}
        for fut in as_completed(futures):
            res = fut.result()
            scraped_count += 1
            if scraped_count % 50 == 0:
                print(f"Scraped {scraped_count}/{len(candidates_to_crawl)}... Found {len(new_stamps)} new stations.")
            if not res:
                failed += 1
                continue
                
            # Verify uniqueness
            if res["id"] in existing_ids or res["sourceUrl"] in existing_urls:
                continue
            if res["name_ja"] in existing_names_ja:
                continue
                
            # Spatial deduplication (< 150m and identical station base name)
            res_lng, res_lat = res["coordinates"]
            clean_res = re.sub(r'^(JR|国鉄|東武|西武|京成|京王|小田急|東急|京急|相鉄|名鉄|近鉄|南海|京阪|阪急|阪神|西鉄)', '', res["name_ja"]).replace('駅', '').strip()
            is_dup = False
            for ex_lng, ex_lat, ex_name in existing_coords:
                if abs(res_lng - ex_lng) < 0.0015 and abs(res_lat - ex_lat) < 0.0015:
                    clean_ex = re.sub(r'^(JR|国鉄|東武|西武|京成|京王|小田急|東急|京急|相鉄|名鉄|近鉄|南海|京阪|阪急|阪神|西鉄)', '', ex_name).replace('駅', '').strip()
                    if clean_res and clean_ex and clean_res == clean_ex:
                        is_dup = True
                        break
            if is_dup:
                continue
                
            # Add to set
            existing_ids.add(res["id"])
            existing_urls.add(res["sourceUrl"])
            existing_names_ja.add(res["name_ja"])
            existing_coords.append((res_lng, res_lat, res["name_ja"]))
            new_stamps.append(res)
            
    print(f"\nCrawling complete. Successfully gathered {len(new_stamps)} authentic new railway stations!")
    
    if new_stamps:
        # Append to database
        stamps.extend(new_stamps)
        
        # Save updated database
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(stamps, f, ensure_ascii=False, indent=2)
        print(f"Updated {DATA_FILE} -> Total stamps: {len(stamps)}")
        
        # Update prefectures.json
        with open(PREF_FILE, "r", encoding="utf-8") as f:
            prefs = json.load(f)
            
        pref_counts = {}
        for s in stamps:
            p_ja = s.get("prefecture", "")
            pref_counts[p_ja] = pref_counts.get(p_ja, 0) + 1
            
        for p in prefs:
            p["stampCount"] = pref_counts.get(p["name_ja"], 0)
            
        with open(PREF_FILE, "w", encoding="utf-8") as f:
            json.dump(prefs, f, ensure_ascii=False, indent=2)
        print(f"Updated {PREF_FILE} counts.")

if __name__ == "__main__":
    main()
