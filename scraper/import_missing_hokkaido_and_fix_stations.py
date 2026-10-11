#!/usr/bin/env python3
"""
Imports Minami-Otaru Station & missing JR Hokkaido / railway stations,
and fixes mislabeled stations across Japan to category 'eki'.
"""

import os
import re
import json
import time
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(BASE_DIR, "public", "data", "stamps.json")
PREF_FILE = os.path.join(BASE_DIR, "public", "data", "prefectures.json")
IMAGES_DIR = os.path.join(BASE_DIR, "public", "images", "stamps")
os.makedirs(IMAGES_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://stamp.funakiya.com/",
}

# 1. Load existing stamps
with open(DATA_FILE, "r", encoding="utf-8") as f:
    stamps = json.load(f)

print(f"Loaded {len(stamps)} existing stamps.")

# 2. Fix misclassified railway stations
fixed_count = 0
for s in stamps:
    cat = s.get("category")
    name_ja = s.get("name_ja", "")
    sid = s.get("id", "")
    url = s.get("sourceUrl", "")
    
    is_station = False
    if "funakiya.com/jr-" in url or "funakiya.com/jnr-" in url or "funakiya.com/st-" in url:
        is_station = True
    elif ("駅" in name_ja or sid.startswith("shop-jr-") or sid.startswith("museum-jr-")) and "道の駅" not in name_ja and not sid.startswith("michi-"):
        is_station = True
        
    if is_station and cat != "eki":
        s["category"] = "eki"
        # Fix operator if it was generic store
        op = s.get("operator", "")
        if "Store" in op or "Association" in op or not op:
            if "JR" in name_ja:
                if s.get("prefecture") == "Hokkaido" or "北海道" in s.get("address", ""):
                    s["operator"] = "JR Hokkaido (JR北海道)"
                elif s.get("prefecture") in ["Aomori", "Iwate", "Miyagi", "Akita", "Yamagata", "Fukushima", "Tokyo", "Kanagawa", "Chiba", "Saitama", "Ibaraki", "Tochigi", "Gunma", "Niigata", "Nagano", "Yamanashi"]:
                    s["operator"] = "JR East (JR東日本)"
                elif s.get("prefecture") in ["Shizuoka", "Aichi", "Gifu", "Mie"]:
                    s["operator"] = "JR Central (JR東海)"
                elif s.get("prefecture") in ["Osaka", "Kyoto", "Hyogo", "Nara", "Shiga", "Wakayama", "Hiroshima", "Okayama", "Yamaguchi", "Tottori", "Shimane", "Ishikawa", "Toyama", "Fukui"]:
                    s["operator"] = "JR West (JR西日本)"
                elif s.get("prefecture") in ["Kagawa", "Tokushima", "Ehime", "Kochi"]:
                    s["operator"] = "JR Shikoku (JR四国)"
                elif s.get("prefecture") in ["Fukuoka", "Saga", "Nagasaki", "Kumamoto", "Oita", "Miyazaki", "Kagoshima"]:
                    s["operator"] = "JR Kyushu (JR九州)"
                else:
                    s["operator"] = "JR (Japan Railways)"
            elif "地下鉄" in name_ja or "メトロ" in name_ja:
                s["operator"] = "Municipal Subway / Metro"
            else:
                s["operator"] = "Railway Authority"
                
        # Fix description if it mentioned artisan boutique
        if "boutique" in s.get("description", "") or "specialty artisan" in s.get("description", ""):
            s["description"] = f"Official commemorative railway station stamp (駅スタンプ) at {name_ja} in {s.get('city', '')}, {s.get('prefecture', '')}."
        fixed_count += 1

print(f"Fixed {fixed_count} mislabeled stations to category 'eki'.")

existing_ids = {s["id"] for s in stamps}
existing_names = {s.get("name_ja", "") for s in stamps}
existing_urls = {s.get("sourceUrl", "") for s in stamps if s.get("sourceUrl")}

# 3. Add Minami-Otaru explicitly if not present
if "eki-jr-minamiotaru" not in existing_ids:
    minami_otaru = {
        "id": "eki-jr-minamiotaru",
        "name": "Minami-Otaru Station",
        "name_ja": "JR南小樽駅",
        "name_romaji": "Minami-Otaru-eki",
        "category": "eki",
        "prefecture": "Hokkaido",
        "city": "小樽市",
        "address": "北海道小樽市住吉町10-7",
        "coordinates": [141.007722, 43.187083],
        "stampLocation": "JR南小樽駅改札外 改札窓口",
        "hours": "5:30～24:30",
        "operator": "JR Hokkaido (JR北海道)",
        "description": "JR Hokkaido Hakodate Main Line station (S14). Commemorative stamp design features 'Fairy Tale & Glass Craft City - Minami-Otaru' (メルヘンとガラスの街 みなみおたる) depicting the historic Otaru steam clock tower, glassware, and seagulls.",
        "sourceUrl": "https://stamp.funakiya.com/jr-minamiotaru.html",
        "imageUrl": "/images/stamps/eki-jr-minamiotaru.jpg",
        "source": "Funakiya Railway Stamp Directory"
    }
    stamps.append(minami_otaru)
    existing_ids.add(minami_otaru["id"])
    existing_names.add(minami_otaru["name_ja"])
    existing_urls.add(minami_otaru["sourceUrl"])
    print("Added Minami-Otaru Station (JR南小樽駅) successfully.")

# 4. Crawl all Hokkaido lines to discover missing active stations
hokkaido_lines = [
    'https://stamp.funakiya.com/jr-hakodate-sapporo-line.html',
    'https://stamp.funakiya.com/jr-hakodate-niseko-line.html',
    'https://stamp.funakiya.com/jr-hakodate-line.html',
    'https://stamp.funakiya.com/jr-chitose-line.html',
    'https://stamp.funakiya.com/jr-muroran-line.html',
    'https://stamp.funakiya.com/jr-sekisho-line.html',
    'https://stamp.funakiya.com/jr-furano-line.html',
    'https://stamp.funakiya.com/jr-soya-line.html',
    'https://stamp.funakiya.com/jr-sekihoku-line.html',
    'https://stamp.funakiya.com/jr-senmo-line.html',
    'https://stamp.funakiya.com/jr-nemuro-line.html',
    'https://stamp.funakiya.com/jr-nemuro-furano-line.html',
    'https://stamp.funakiya.com/jr-hanasaki-line.html',
    'https://stamp.funakiya.com/jr-sassho-line.html',
    'https://stamp.funakiya.com/st-namboku-line.html',
    'https://stamp.funakiya.com/st-tozai-line.html',
    'https://stamp.funakiya.com/st-toho-line.html',
]

station_links = []
seen_st_urls = set()
for line_url in hokkaido_lines:
    try:
        r = requests.get(line_url, headers=HEADERS, timeout=8)
        if r.status_code == 200:
            r.encoding = "utf-8"
            soup = BeautifulSoup(r.text, "html.parser")
            for a in soup.find_all("a", href=True):
                text = a.get_text(strip=True)
                if "設置あり" in text and "駅のスタンプ" in text:
                    href = a["href"]
                    if not href.startswith("http"):
                        href = f"https://stamp.funakiya.com/{href}"
                    if href not in seen_st_urls:
                        seen_st_urls.add(href)
                        station_links.append(href)
    except Exception as e:
        print(f"Error on {line_url}: {e}")

print(f"Found {len(station_links)} active Hokkaido station links on Funakiya.")

# Function to scrape and parse a station page
def scrape_station_page(st_url):
    try:
        r = requests.get(st_url, headers=HEADERS, timeout=10)
        if r.status_code != 200:
            return None
        r.encoding = "utf-8"
        soup = BeautifulSoup(r.text, "html.parser")
        
        # Name
        h1 = soup.find("h1")
        h1_text = h1.get_text(strip=True) if h1 else ""
        m_name = re.search(r"^(JR|国鉄|地下鉄|札幌市営地下鉄)?(.+?駅)", h1_text)
        name_ja = m_name.group(0) if m_name else h1_text.replace("のスタンプ", "").strip()
        if not name_ja:
            name_ja = "駅"
            
        # Check if already in DB
        if name_ja in existing_names or st_url in existing_urls:
            return None
            
        # Address & Coordinates
        html_text = r.text
        geo_m = re.search(r"Geo URI[：:\s]*([\d\.]+),\s*([\d\.]+)", html_text)
        if not geo_m:
            return None
        lat, lng = float(geo_m.group(1)), float(geo_m.group(2))
        
        addr_m = re.search(r"所在地[：:\s]*(?:〒[\d-]+)?\s*([^\n<]+)", html_text)
        address = addr_m.group(1).strip() if addr_m else "北海道"
        
        # City
        city_m = re.search(r"北海道([^\s市町村]+[市町村])", address)
        city = city_m.group(1) if city_m else "北海道"
        
        # Stamp Location
        loc_m = re.search(r"設置場所[：:\s]*([^\n<]+)", html_text)
        stamp_location = loc_m.group(1).strip() if loc_m else "駅窓口・改札付近"
        
        # Hours
        hours_m = re.search(r"営業時間[：:\s]*([^\n<]+)", html_text)
        hours = hours_m.group(1).strip() if hours_m else "始発～終電"
        
        # Design / Description
        desc_m = re.search(r"JR.+?駅のスタンプです。「([^」]+)」", html_text)
        design = desc_m.group(1).strip() if desc_m else ""
        
        # Image
        img_url = None
        for img in soup.find_all("img"):
            src = img.get("src", "")
            if "/i/stamp/" in src and "01" not in src and "haisen" not in src:
                img_url = src if src.startswith("http") else f"https://www.funakiya.com{src}"
                break
        if not img_url:
            for img in soup.find_all("img"):
                src = img.get("src", "")
                if "/i/stamp/" in src:
                    img_url = src if src.startswith("http") else f"https://www.funakiya.com{src}"
                    break
                    
        # Clean slug ID
        slug_match = re.search(r"/([a-z0-9_-]+)\.html", st_url)
        slug = slug_match.group(1) if slug_match else f"eki-{len(stamps)}"
        station_id = f"eki-{slug}"
        if station_id in existing_ids:
            station_id = f"{station_id}-hokkaido"
            
        # Download image if available
        local_img = None
        if img_url:
            fname = f"{station_id}.jpg"
            fpath = os.path.join(IMAGES_DIR, fname)
            try:
                ir = requests.get(img_url, headers=HEADERS, timeout=10)
                if ir.status_code == 200 and len(ir.content) > 1000:
                    with open(fpath, "wb") as f_img:
                        f_img.write(ir.content)
                    local_img = f"/images/stamps/{fname}"
            except Exception:
                pass
                
        # Clean English name
        clean_core = re.sub(r"^(JR|国鉄|地下鉄|札幌市営地下鉄)", "", name_ja).replace("駅", "").strip()
        operator = "Sapporo Municipal Subway" if "地下鉄" in name_ja else "JR Hokkaido (JR北海道)"
        
        desc = f"{operator} railway station stamp at {name_ja} in {city}, Hokkaido."
        if design:
            desc += f" Motif: '{design}'."
            
        record = {
            "id": station_id,
            "name": f"{clean_core} Station",
            "name_ja": name_ja,
            "name_romaji": f"{clean_core}-eki",
            "category": "eki",
            "prefecture": "Hokkaido",
            "city": city,
            "address": address,
            "coordinates": [lng, lat],
            "stampLocation": stamp_location,
            "hours": hours,
            "operator": operator,
            "description": desc,
            "sourceUrl": st_url,
            "source": "Funakiya Railway Stamp Directory"
        }
        if local_img:
            record["imageUrl"] = local_img
            
        return record
    except Exception as e:
        print(f"Error scraping {st_url}: {e}")
        return None

new_stamps = []
with ThreadPoolExecutor(max_workers=6) as executor:
    futures = [executor.submit(scrape_station_page, u) for u in station_links]
    for fut in as_completed(futures):
        rec = fut.result()
        if rec:
            new_stamps.append(rec)
            existing_ids.add(rec["id"])
            existing_names.add(rec["name_ja"])
            existing_urls.add(rec["sourceUrl"])
            print(f"  + [{rec['category']}] {rec['name_ja']} ({rec['name']}) -> {rec['city']}")

print(f"\nDiscovered and imported {len(new_stamps)} new active Hokkaido railway stations!")

# Combine and save
all_stamps = stamps + new_stamps
with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(all_stamps, f, ensure_ascii=False, indent=2)

print(f"Updated {DATA_FILE}. Total stamps: {len(all_stamps)}.")

# Update prefectures count
if os.path.exists(PREF_FILE):
    with open(PREF_FILE, "r", encoding="utf-8") as f:
        prefs = json.load(f)
    hokkaido_count = sum(1 for s in all_stamps if s.get("prefecture") == "Hokkaido")
    for p in prefs:
        if p.get("id") == "hokkaido":
            p["stampCount"] = hokkaido_count
    with open(PREF_FILE, "w", encoding="utf-8") as f:
        json.dump(prefs, f, ensure_ascii=False, indent=2)
    print(f"Updated {PREF_FILE} (Hokkaido count: {hokkaido_count}).")

