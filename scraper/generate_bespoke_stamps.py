#!/usr/bin/env python3
"""
Generates bespoke, authentic Japanese Hanko seals for any stamp that doesn't have
a photographed ink impression from Funakiya.
Ensures 100% of all stamps in Stampu have an individualized stamp illustration.
"""

import os
import json
import re
import zlib

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "public", "data", "stamps.json")
OUTPUT_DIR = os.path.join(BASE_DIR, "public", "images", "stamps")

CATEGORY_CONFIG = {
    "castle": {
        "ink": "#991b1b",
        "bg": "#fef2f2",
        "badge": "日本名城 登城記念",
        "corner": "登城記念",
    },
    "michinoeki": {
        "ink": "#9a3412",
        "bg": "#fff7ed",
        "badge": "全国道の駅 登録記念",
        "corner": "来駅記念",
    },
    "highway": {
        "ink": "#1e40af",
        "bg": "#eff6ff",
        "badge": "ハイウェイ 休憩記念",
        "corner": "交通安全",
    },
    "temple_shrine": {
        "ink": "#991b1b",
        "bg": "#fef2f2",
        "badge": "名刹古社 参拝記念",
        "corner": "奉拝",
    },
    "eki": {
        "ink": "#065f46",
        "bg": "#ecfdf5",
        "badge": "鉄道 記念スタンプ",
        "corner": "乗車記念",
    }
}


def clean_name_for_seal(name_ja: str) -> str:
    cleaned = re.sub(r'\(.+?\)|（.+?）', '', name_ja).strip()
    cleaned = cleaned.replace("道の駅", "").replace("JR", "").strip()
    return cleaned or name_ja


def get_stamp_rotation(stamp_id: str) -> float:
    crc = zlib.crc32(stamp_id.encode("utf-8"))
    return round(((crc % 100) / 100.0) * 4.4 - 2.2, 2)


def generate_seal_svg(stamp: dict) -> str:
    cat = stamp.get("category", "castle")
    cfg = CATEGORY_CONFIG.get(cat, CATEGORY_CONFIG["castle"])
    stamp_id = stamp["id"]

    name_ja = clean_name_for_seal(stamp.get("name_ja", stamp.get("name", "")))
    pref = stamp.get("prefecture", "")
    city = stamp.get("city", "")

    # Castle number or ID
    no_match = re.search(r'No\.(\d+)', stamp.get("name", "") + " " + stamp.get("name_ja", ""))
    if no_match:
        sub_title = f"No.{int(no_match.group(1)):03d} • {pref}"
    elif city:
        sub_title = f"{pref} • {city}"
    else:
        sub_title = f"COLLECTION • {pref}"

    rot = get_stamp_rotation(stamp_id)

    # Calculate font sizes and layout based on character count
    char_len = len(name_ja)
    if char_len <= 3:
        font_size = 46
        lines = [name_ja]
    elif char_len <= 6:
        font_size = 38
        lines = [name_ja]
    elif char_len <= 10:
        font_size = 30
        mid = (char_len + 1) // 2
        lines = [name_ja[:mid], name_ja[mid:]]
    elif char_len <= 14:
        font_size = 24
        mid = (char_len + 1) // 2
        lines = [name_ja[:mid], name_ja[mid:]]
    else:
        font_size = 20
        mid = (char_len + 1) // 2
        lines = [name_ja[:mid], name_ja[mid:]]

    if len(lines) == 1:
        lines_svg = f'<text x="200" y="195" font-family="\'Noto Serif JP\', \'Yu Mincho\', serif" font-weight="900" font-size="{font_size}" fill="{cfg["ink"]}" text-anchor="middle" letter-spacing="4">{lines[0]}</text>'
    else:
        lines_svg = f'''<text x="200" y="180" font-family="\'Noto Serif JP\', \'Yu Mincho\', serif" font-weight="900" font-size="{font_size}" fill="{cfg["ink"]}" text-anchor="middle" letter-spacing="3">{lines[0]}</text>
    <text x="200" y="222" font-family="\'Noto Serif JP\', \'Yu Mincho\', serif" font-weight="900" font-size="{font_size}" fill="{cfg["ink"]}" text-anchor="middle" letter-spacing="3">{lines[1]}</text>'''

    badge_text = cfg["badge"]
    if cat == "castle":
        if "zoku" in stamp_id or "続" in stamp.get("name_ja", ""):
            badge_text = "続日本100名城 登城印"
        else:
            badge_text = "日本100名城 登城記念"

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400" width="100%" height="100%">
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
    <text x="200" y="86" font-family="'Noto Serif JP', 'Yu Mincho', serif" font-weight="bold" font-size="20" fill="{cfg["ink"]}" text-anchor="middle" letter-spacing="5">{badge_text}</text>

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
    return svg


def main():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        stamps = json.load(f)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    existing_files = set(os.listdir(OUTPUT_DIR))

    regenerated_count = 0

    for stamp in stamps:
        stamp_id = stamp["id"]
        img_url = stamp.get("imageUrl", "")

        # If it uses an SVG, regenerate with the authentic Japanese Hanko design without generic clipart icon
        if img_url.endswith(".svg"):
            svg_name = f"{stamp_id}.svg"
            svg_path = os.path.join(OUTPUT_DIR, svg_name)
            svg_content = generate_seal_svg(stamp)
            with open(svg_path, "w", encoding="utf-8") as f:
                f.write(svg_content)
            regenerated_count += 1

    print(f"Total stamps: {len(stamps)}")
    print(f"Regenerated authentic Hanko SVGs: {regenerated_count}")


if __name__ == "__main__":
    main()
