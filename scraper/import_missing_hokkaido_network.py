#!/usr/bin/env python3
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

with open(DATA_FILE, "r", encoding="utf-8") as f:
    stamps = json.load(f)

existing_ids = {s["id"] for s in stamps}
existing_names = {s.get("name_ja", "") for s in stamps}
existing_urls = {s.get("sourceUrl", "") for s in stamps if s.get("sourceUrl")}

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
seen_urls = set()

for line_url in hokkaido_lines:
    try:
        r = requests.get(line_url, headers=HEADERS, timeout=8)
        if r.status_code == 200:
            r.encoding = "utf-8"
            soup = BeautifulSoup(r.text, "html.parser")
            for a in soup.find_all("a", href=True):
                text = a.get_text(strip=True)
                if "設置あり" in text:
                    href = a["href"]
                    if not href.startswith("http"):
                        href = f"https://stamp.funakiya.com/{href}"
                    if href not in seen_urls:
                        seen_urls.add(href)
                        station_links.append(href)
    except Exception as e:
        print("Error on", line_url, e)

print(f"Total station pages to inspect: {len(station_links)}")

def scrape_station(st_url):
    try:
        r = requests.get(st_url, headers=HEADERS, timeout=10)
        if r.status_code != 200:
            return None
        r.encoding = "utf-8"
        soup = BeautifulSoup(r.text, "html.parser")
        
        title_str = soup.title.string if soup.title else ""
        name_ja = title_str.split("のスタンプ")[0].strip()
        if not name_ja or "404" in name_ja:
            return None
            
        if name_ja in existing_names or st_url in existing_urls:
            return None
            
        # Coordinates
        geo_m = re.search(r"Geo URI[：:\s]*([\d\.]+),\s*([\d\.]+)", r.text)
        if not geo_m:
            return None
        lat, lng = float(geo_m.group(1)), float(geo_m.group(2))
        
        # Address
        addr_m = re.search(r"所在地[：:\s]*(?:〒[\d-]+)?\s*([^\n<]+)", r.text)
        address = addr_m.group(1).strip() if addr_m else "北海道"
        
        # City
        city_m = re.search(r"北海道([^\s市町村]+[市町村])", address)
        city = city_m.group(1) if city_m else "北海道"
        
        # Stamp Location
        loc_m = re.search(r"設置場所[：:\s]*([^\n<]+)", r.text)
        stamp_location = loc_m.group(1).strip() if loc_m else "改札口・窓口付近"
        
        # Hours
        hours_m = re.search(r"営業時間[：:\s]*([^\n<]+)", r.text)
        hours = hours_m.group(1).strip() if hours_m else "始発～終電"
        
        # Design
        desc_m = re.search(r"のスタンプです。「([^」]+)」", r.text)
        design = desc_m.group(1).strip() if desc_m else ""
        
        # Slug & ID
        slug_m = re.search(r"/([a-z0-9_-]+)\.html", st_url)
        slug = slug_m.group(1) if slug_m else f"eki-{len(stamps)}"
        sid = f"eki-{slug}"
        if sid in existing_ids:
            sid = f"{sid}-hokkaido"
            
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
                    
        local_img = None
        if img_url:
            fname = f"{sid}.jpg"
            fpath = os.path.join(IMAGES_DIR, fname)
            try:
                ir = requests.get(img_url, headers=HEADERS, timeout=10)
                if ir.status_code == 200 and len(ir.content) > 1000:
                    with open(fpath, "wb") as f_img:
                        f_img.write(ir.content)
                    local_img = f"/images/stamps/{fname}"
            except Exception:
                pass
                
        clean_core = re.sub(r"^(JR|国鉄|地下鉄|札幌市営地下鉄)", "", name_ja).replace("駅", "").strip()
        operator = "Sapporo Municipal Subway" if "地下鉄" in name_ja else "JR Hokkaido (JR北海道)"
        desc = f"{operator} station stamp at {name_ja} in {city}, Hokkaido."
        if design:
            desc += f" Motif: '{design}'."
            
        rec = {
            "id": sid,
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
            rec["imageUrl"] = local_img
            
        return rec
    except Exception as e:
        print(f"Error scraping {st_url}: {e}")
        return None

new_records = []
with ThreadPoolExecutor(max_workers=6) as executor:
    futures = [executor.submit(scrape_station, u) for u in station_links]
    for fut in as_completed(futures):
        res = fut.result()
        if res:
            new_records.append(res)
            existing_ids.add(res["id"])
            existing_names.add(res["name_ja"])
            existing_urls.add(res["sourceUrl"])
            print(f"  + [{res['name_ja']}] {res['name']} ({res['city']})")

print(f"\nImported {len(new_records)} additional active Hokkaido stations!")

if new_records:
    all_stamps = stamps + new_records
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(all_stamps, f, ensure_ascii=False, indent=2)
    print(f"Updated {DATA_FILE}. Total stamps: {len(all_stamps)}.")
    
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

