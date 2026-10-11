#!/usr/bin/env python3
"""
Collects all active railway stations across all regional lines from Funakiya,
English Funakiya, and Japan Stamp Hunt.
"""
import os
import re
import json
import time
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(BASE_DIR, "scraper", "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

REGIONAL_PAGES = [
    "https://stamp.funakiya.com/pref/train-tohoku.html",
    "https://stamp.funakiya.com/pref/train-kanto.html",
    "https://stamp.funakiya.com/stamp-tokyo.html",
    "https://stamp.funakiya.com/pref/train-koshinetsu.html",
    "https://stamp.funakiya.com/pref/train-hokuriku.html",
    "https://stamp.funakiya.com/pref/train-tokai.html",
    "https://stamp.funakiya.com/pref/train-kinki.html",
    "https://stamp.funakiya.com/pref/train-chugoku.html",
    "https://stamp.funakiya.com/pref/train-shikoku.html",
    "https://stamp.funakiya.com/pref/train-kyushu.html",
    "https://stamp.funakiya.com/pref/train-hokkaido.html",
    "https://stamp.funakiya.com/jr/jreast/",
    "https://stamp.funakiya.com/jr/jrcentral/",
    "https://stamp.funakiya.com/jr/jrwest/",
    "https://stamp.funakiya.com/jr/jrshikoku/",
    "https://stamp.funakiya.com/jr/jrkyushu/",
    "https://stamp.funakiya.com/jr/jrhokkaido/",
    "https://stamp.funakiya.com/tokyometro.html",
    "https://stamp.funakiya.com/mintetsu/osaka-metro/",
    # English mirrors
    "https://stamp.funakiya.com/en/train.html",
    "https://stamp.funakiya.com/en/pref/train-tohoku.html",
    "https://stamp.funakiya.com/en/pref/train-kanto.html",
    "https://stamp.funakiya.com/en/stamp-tokyo.html",
    "https://stamp.funakiya.com/en/pref/train-koshinetsu.html",
    "https://stamp.funakiya.com/en/pref/train-hokuriku.html",
    "https://stamp.funakiya.com/en/pref/train-tokai.html",
    "https://stamp.funakiya.com/en/pref/train-kinki.html",
    "https://stamp.funakiya.com/en/pref/train-chugoku.html",
    "https://stamp.funakiya.com/en/pref/train-shikoku.html",
    "https://stamp.funakiya.com/en/pref/train-kyushu.html",
    "https://stamp.funakiya.com/en/pref/train-hokkaido.html",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://stamp.funakiya.com/",
}

def discover_line_urls():
    line_urls = set()
    for page in REGIONAL_PAGES:
        try:
            r = requests.get(page, headers=HEADERS, timeout=8)
            if r.status_code == 200:
                r.encoding = "utf-8"
                soup = BeautifulSoup(r.text, "html.parser")
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    if not href.startswith("http"):
                        href = f"https://stamp.funakiya.com/{href.lstrip('/')}"
                    if any(k in href for k in ["-line.html", "line.html", "tetsudo", "railway", "metro", "sen.html"]) and not "train-" in href and not "facebook" in href and not "twitter" in href:
                        line_urls.add(href)
        except Exception as e:
            pass
    print(f"Discovered {len(line_urls)} line catalog pages.")
    return sorted(list(line_urls))

def fetch_stations_from_line(url):
    results = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=8)
        if r.status_code == 200:
            r.encoding = "utf-8"
            soup = BeautifulSoup(r.text, "html.parser")
            line_name = ""
            if soup.title:
                line_name = soup.title.string.split("のスタンプ")[0].strip()
            for a in soup.find_all("a", href=True):
                text = a.get_text(strip=True)
                if "設置あり" in text:
                    href = a["href"]
                    if not href.startswith("http"):
                        href = f"https://stamp.funakiya.com/{href.lstrip('/')}"
                    station_name = text.split("≪")[0].replace("のスタンプ", "").strip()
                    results.append((href, station_name, line_name))
    except Exception:
        pass
    return results

def get_jsh_station_urls():
    jsh_stations = []
    try:
        for sub in [
            "https://japan-stamp-hunt.com/wp-sitemap-posts-stamps-1.xml",
            "https://japan-stamp-hunt.com/wp-sitemap-posts-stamps-2.xml"
        ]:
            r = requests.get(sub, headers=HEADERS, timeout=10)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")
                for loc in soup.find_all("loc"):
                    u = loc.text.strip()
                    if any(k in u for k in ["station", "eki"]):
                        jsh_stations.append(u)
    except Exception as e:
        print("Error getting JSH:", e)
    print(f"Discovered {len(jsh_stations)} station pages in Japan Stamp Hunt.")
    return jsh_stations

def main():
    lines = discover_line_urls()
    station_candidates = {}

    print("Fetching active stations from Funakiya lines...")
    with ThreadPoolExecutor(max_workers=20) as pool:
        futures = [pool.submit(fetch_stations_from_line, u) for u in lines]
        for fut in as_completed(futures):
            for href, st_name, line_name in fut.result():
                if href not in station_candidates:
                    station_candidates[href] = {
                        "url": href,
                        "name_hint": st_name,
                        "line_hint": line_name,
                        "source": "funakiya"
                    }

    print(f"Total active station pages on Funakiya: {len(station_candidates)}")

    jsh_urls = get_jsh_station_urls()
    out_data = {
        "funakiya_active_stations": list(station_candidates.values()),
        "jsh_station_urls": jsh_urls
    }

    out_file = os.path.join(CACHE_DIR, "all_active_station_candidates.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(out_data, f, ensure_ascii=False, indent=2)

    print(f"Saved candidate list to {out_file}")

if __name__ == "__main__":
    main()
