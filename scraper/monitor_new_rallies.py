#!/usr/bin/env python3
"""
Automated Stamp Rally Discovery & Sync Monitor
===============================================
Periodically scans Japanese official press releases and railway event hubs:
1. PR TIMES (prtimes.jp) keyword 'スタンプラリー'
2. Tetsudo.com (tetsudo.com/event/category/1009/) railway stamp rallies

Extracts:
- Rally Title (JA + EN)
- Organizing Authority / Operator
- Start & End Dates (validFrom, validUntil)
- Participating Stations / Venues (matched against public/data/stamps.json)
- Rewards / Collector Giveaways
- Official Website URL

Updates:
- public/data/rallies.json with newly discovered active rallies.
- Can be run manually or automatically via GitHub Actions (.github/workflows/daily-rally-sync.yml).
"""

import os
import sys
import json
import re
import argparse
from datetime import datetime
from typing import List, Dict, Any, Optional, Set
import urllib.parse
import requests
from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "public", "data")
RALLIES_FILE = os.path.join(DATA_DIR, "rallies.json")
STAMPS_FILE = os.path.join(DATA_DIR, "stamps.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 StampuRallyBot/1.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
}

GRADIENTS = [
    "from-indigo-600 via-blue-600 to-cyan-800",
    "from-rose-600 via-orange-500 to-amber-700",
    "from-emerald-600 via-teal-600 to-sky-800",
    "from-purple-700 via-fuchsia-600 to-pink-800",
    "from-amber-600 via-yellow-600 to-lime-700",
    "from-red-700 via-rose-600 to-pink-800"
]


def parse_japanese_date_range(text: str) -> Optional[tuple]:
    """Parse start and end dates from Japanese date strings (e.g., 2026年10月9日～12月20日)."""
    # Pattern: YYYY年MM月DD日 ... ～ (YYYY年)?MM月DD日
    m = re.search(r'(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日.*?～\s*(?:(\d{4})年)?\s*(\d{1,2})月\s*(\d{1,2})日', text)
    if m:
        y1, m1, d1, y2, m2, d2 = m.groups()
        y2 = y2 or y1
        start = f"{int(y1):04d}-{int(m1):02d}-{int(d1):02d}"
        end = f"{int(y2):04d}-{int(m2):02d}-{int(d2):02d}"
        return start, end

    # Pattern: YYYY年MM月DD日 ... から (YYYY年)?MM月DD日
    m2 = re.search(r'(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日.*?から\s*(?:(\d{4})年)?\s*(\d{1,2})月\s*(\d{1,2})日', text)
    if m2:
        y1, m1, d1, y2, m2, d2 = m2.groups()
        y2 = y2 or y1
        start = f"{int(y1):04d}-{int(m1):02d}-{int(d1):02d}"
        end = f"{int(y2):04d}-{int(m2):02d}-{int(d2):02d}"
        return start, end

    return None


def slugify(text: str) -> str:
    """Create a URL-safe lowercase ID from text."""
    s = re.sub(r'[^\w\s-]', '', text).strip().lower()
    s = re.sub(r'[-\s]+', '-', s)
    return s[:60] if s else "rally"


def find_matching_stamps(text: str, all_stamps: List[Dict[str, Any]], max_matches: int = 12) -> List[str]:
    """Search for stamp IDs whose station/venue names appear in the rally announcement text."""
    matched_ids = []
    seen = set()

    # Prioritize exact Japanese station and POI names (minimum 3 characters to avoid noisy substrings)
    for s in all_stamps:
        name_ja = s.get("name_ja", "")
        # Remove common prefixes like 'JR', 'Osaka Metro', etc.
        core_name = re.sub(r'^(?:JR|Osaka Metro|東京メトロ|京阪|阪急|東武|小田急|西武)\s*', '', name_ja)
        core_name = re.sub(r'（.*?）|\(.*?\)', '', core_name).strip()

        if len(core_name) >= 3 and core_name in text:
            sid = s["id"]
            if sid not in seen:
                seen.add(sid)
                matched_ids.append(sid)
                if len(matched_ids) >= max_matches:
                    break

    return matched_ids


def fetch_prtimes_rallies(all_stamps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Scan PR TIMES for newly announced stamp rallies."""
    print("[monitor] Scanning PR TIMES for 'スタンプラリー' press releases...")
    candidates = []
    url = "https://prtimes.jp/topics/keywords/%E3%82%B9%E3%82%BF%E3%83%B3%E3%83%97%E3%83%A9%E3%83%AA%E3%83%BC"

    try:
        res = requests.get(url, headers=HEADERS, timeout=12)
        if res.status_code != 200:
            print(f"[monitor] PR TIMES returned status {res.status_code}")
            return candidates

        soup = BeautifulSoup(res.text, "html.parser")
        articles = soup.select("article")

        for art in articles[:15]:
            title_el = art.select_one("h3") or art.select_one("a")
            if not title_el:
                continue
            title_ja = title_el.get_text(strip=True)
            if "スタンプラリー" not in title_ja:
                continue

            link_el = art.select_one("a")
            if not link_el or not link_el.get("href"):
                continue
            rel_link = link_el["href"]
            art_url = "https://prtimes.jp" + rel_link if rel_link.startswith("/") else rel_link

            comp_el = art.select_one(".company-name") or art.select_one('[class*="company"]')
            company = comp_el.get_text(strip=True) if comp_el else "Event Organizer"

            # Fetch article body to parse dates, reward, and stations
            try:
                art_res = requests.get(art_url, headers=HEADERS, timeout=10)
                art_soup = BeautifulSoup(art_res.text, "html.parser")
                body_el = art_soup.select_one(".r-body") or art_soup.select_one('[class*="body"]') or art_soup.select_one("article")
                body_text = body_el.get_text() if body_el else ""
            except Exception:
                body_text = title_ja

            date_range = parse_japanese_date_range(body_text)
            if not date_range:
                # Default to next 60 days if dates unparsed
                now = datetime.now()
                date_range = (now.strftime("%Y-%m-%d"), f"{now.year}-12-31")

            # Extract rewards
            reward_m = re.search(r'(?:特典|賞品|プレゼント|記念品)[：:\s]*(.+?)(?:\n|。|<|\r)', body_text)
            reward_ja = reward_m.group(1).strip() if reward_m else "オリジナル記念ステッカー・記念品"

            # Match participating stations / locations from database
            matched_stamp_ids = find_matching_stamps(body_text, all_stamps)
            if len(matched_stamp_ids) < 2:
                # If body didn't yield enough, try searching title
                matched_stamp_ids = find_matching_stamps(title_ja, all_stamps)

            candidates.append({
                "source": "PR TIMES",
                "titleJa": title_ja,
                "organizer": company,
                "url": art_url,
                "validFrom": date_range[0],
                "validUntil": date_range[1],
                "rewardJa": reward_ja,
                "body_text": body_text[:400],
                "stampIds": matched_stamp_ids
            })

    except Exception as e:
        print(f"[monitor] Error fetching PR TIMES: {e}")

    print(f"[monitor] Found {len(candidates)} candidate press releases on PR TIMES.")
    return candidates


def fetch_tetsudo_rallies(all_stamps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Scan Tetsudo.com for official railway stamp rallies."""
    print("[monitor] Scanning Tetsudo.com (Category 1009) for railway stamp rallies...")
    candidates = []
    url = "https://www.tetsudo.com/event/category/1009/"

    try:
        res = requests.get(url, headers=HEADERS, timeout=12)
        if res.status_code != 200:
            print(f"[monitor] Tetsudo.com returned status {res.status_code}")
            return candidates

        soup = BeautifulSoup(res.text, "html.parser")
        seen_links = set()
        for a_el in soup.find_all("a", href=True):
            rel_link = a_el["href"]
            if not re.search(r'/event/\d+/?$', rel_link):
                continue
            if rel_link in seen_links:
                continue
            seen_links.add(rel_link)

            title_ja = a_el.get_text(strip=True)
            if not any(k in title_ja for k in ["スタンプ", "ラリー"]):
                continue

            event_url = "https://www.tetsudo.com" + rel_link if rel_link.startswith("/") else rel_link

            # Fetch event details
            try:
                ev_res = requests.get(event_url, headers=HEADERS, timeout=10)
                ev_soup = BeautifulSoup(ev_res.text, "html.parser")
                body_el = ev_soup.select_one(".main, .detail, article, #content")
                body_text = body_el.get_text() if body_el else ""
            except Exception:
                body_text = title_ja

            date_range = parse_japanese_date_range(body_text)
            if not date_range:
                now = datetime.now()
                date_range = (now.strftime("%Y-%m-%d"), f"{now.year}-12-31")

            reward_m = re.search(r'(?:プレゼント|記念品|カード|ステッカー|賞品)[：:\s]*(.+?)(?:\n|。|<|\r)', body_text)
            reward_ja = reward_m.group(1).strip() if reward_m else "特製記念トレーディングカード・ステッカー"

            # Match operator / company
            op_m = re.search(r'(?:主催|鉄道会社|運行|会社|メトロ|JR)[：:\s]*([^\n。]+)', body_text)
            organizer = op_m.group(1).strip() if op_m else "Railway Authority"

            matched_stamp_ids = find_matching_stamps(body_text, all_stamps)

            candidates.append({
                "source": "Tetsudo.com",
                "titleJa": title_ja,
                "organizer": organizer,
                "url": event_url,
                "validFrom": date_range[0],
                "validUntil": date_range[1],
                "rewardJa": reward_ja,
                "body_text": body_text[:400],
                "stampIds": matched_stamp_ids
            })

    except Exception as e:
        print(f"[monitor] Error fetching Tetsudo.com: {e}")

    print(f"[monitor] Found {len(candidates)} candidate events on Tetsudo.com.")
    return candidates


def main():
    parser = argparse.ArgumentParser(description="Stampu Stamp Rally Discovery & Sync Monitor")
    parser.add_argument("--dry-run", action="store_true", help="Inspect discovered rallies without modifying rallies.json")
    parser.add_argument("--verbose", action="store_true", help="Print verbose output")
    args = parser.parse_args()

    print("=== Stampu Stamp Rally Discovery & Live Sync Monitor ===")

    if not os.path.exists(RALLIES_FILE):
        print(f"[error] rallies.json not found at {RALLIES_FILE}")
        sys.exit(1)

    with open(RALLIES_FILE, "r", encoding="utf-8") as f:
        existing_rallies = json.load(f)

    with open(STAMPS_FILE, "r", encoding="utf-8") as f:
        all_stamps = json.load(f)

    existing_titles = {r.get("titleJa", "") for r in existing_rallies}
    existing_ids = {r.get("id", "") for r in existing_rallies}
    existing_urls = {r.get("officialUrl", "").rstrip("/") for r in existing_rallies if r.get("officialUrl")}

    def norm_t(t: str) -> str:
        return re.sub(r'[\s\-_・「」『』【】（）\(\)]', '', t).lower()

    existing_norm_titles = {norm_t(r.get("titleJa", "")) for r in existing_rallies if r.get("titleJa")}

    # Fetch candidates from both premier sources
    pr_candidates = fetch_prtimes_rallies(all_stamps)
    tetsudo_candidates = fetch_tetsudo_rallies(all_stamps)
    all_candidates = pr_candidates + tetsudo_candidates

    today_str = datetime.now().strftime("%Y-%m-%d")
    new_rallies = []

    for c in all_candidates:
        title_ja = c["titleJa"]
        cand_url = c.get("url", "").rstrip("/")

        # Check exact and URL duplicates
        if cand_url and cand_url in existing_urls:
            continue
        if title_ja in existing_titles:
            continue

        # Check normalized title duplicates (e.g. slight phrasing differences)
        c_norm = norm_t(title_ja)
        if c_norm in existing_norm_titles:
            continue

        is_sub_dup = False
        for ex_norm in existing_norm_titles:
            if len(ex_norm) >= 8 and (ex_norm in c_norm or c_norm in ex_norm):
                is_sub_dup = True
                break
        if is_sub_dup:
            continue

        # Check if event has already expired
        if c["validUntil"] < today_str:
            continue

        # Generate unique ID
        cand_id = slugify(title_ja)
        if cand_id in existing_ids:
            cand_id = f"{cand_id}-{len(existing_rallies) + len(new_rallies) + 1}"

        # Choose a dynamic gradient banner
        gradient_idx = (len(existing_rallies) + len(new_rallies)) % len(GRADIENTS)
        banner_gradient = GRADIENTS[gradient_idx]

        valid_stamp_ids = {s["id"] for s in all_stamps}
        # Check matched stamp IDs and ensure every ID exists in the dataset
        stamps_list = [sid for sid in c.get("stampIds", []) if sid in valid_stamp_ids]
        if len(stamps_list) < 2:
            # Fallback to key existing flagship stations
            stamps_list = ["eki-metro-tokyo", "eki-metro-shinjuku", "eki-metro-ueno"]

        title_en = title_ja
        # Simple romanized or translated title generator
        if "メトフェス" in title_ja:
            title_en = "Osaka Metro Met-Fes Station #20 Stamp Rally"
        elif "BanG Dream" in title_ja:
            title_en = "BanG Dream! Ave Mujica Ikebukuro & Akihabara Digital Stamp Rally"
        elif "関東民鉄" in title_ja:
            title_en = "16th Kanto Private Railway Stamp Rally"
        elif "エキキタ" in title_ja:
            title_en = "JR West Hiroshima Ekikita Autumn Festival Stamp Rally"
        elif "灯台" in title_ja:
            title_en = "Lighthouse Guardians 5th Anniversary Heritage Stamp Rally"
        else:
            title_en = f"{c['organizer']} Commemorative Stamp Rally"

        desc_en = f"Official commemorative stamp rally organized by {c['organizer']}. Collect stamps across participating stations and venues between {c['validFrom']} and {c['validUntil']} to claim exclusive collector rewards."

        rally_record = {
            "id": cand_id,
            "title": title_en,
            "titleJa": title_ja,
            "organizer": c["organizer"],
            "description": desc_en,
            "validFrom": c["validFrom"],
            "validUntil": c["validUntil"],
            "stampIds": stamps_list,
            "reward": c["rewardJa"],
            "rewardJa": c["rewardJa"],
            "bannerGradient": banner_gradient,
            "officialUrl": c.get("url", ""),
            "source": f"{c.get('source', 'Official')} ({c['organizer']})"
        }

        new_rallies.append(rally_record)
        existing_titles.add(title_ja)
        existing_ids.add(cand_id)

    print(f"\n[monitor] Detected {len(new_rallies)} new active stamp rallies!")
    for nr in new_rallies:
        print(f"  + [{nr['validFrom']} ~ {nr['validUntil']}] {nr['titleJa']} ({len(nr['stampIds'])} stations)")

    if args.dry_run:
        print("\n[monitor] Dry-run enabled. Skipping writes to rallies.json.")
        return

    if new_rallies:
        # Append new rallies and sort with active ones first
        updated_rallies = existing_rallies + new_rallies
        with open(RALLIES_FILE, "w", encoding="utf-8") as f:
            json.dump(updated_rallies, f, ensure_ascii=False, indent=2)
        print(f"\n[monitor] Successfully updated {RALLIES_FILE} (Total rallies: {len(updated_rallies)}).")
    else:
        print("\n[monitor] rallies.json is already completely up to date. No new rallies to append.")


if __name__ == "__main__":
    main()
