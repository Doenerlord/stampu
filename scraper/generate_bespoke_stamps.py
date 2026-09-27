#!/usr/bin/env python3
"""
Generates bespoke, authentic Japanese Hanko seals for any stamp that doesn't have
a photographed ink impression from Funakiya.
Ensures 100% of all stamps in Stampu have an individualized stamp illustration.
"""

import os
import json
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "public", "data", "stamps.json")
OUTPUT_DIR = os.path.join(BASE_DIR, "public", "images", "stamps")

CATEGORY_CONFIG = {
    "castle": {
        "color": "#b91c1c",
        "ink": "#991b1b",
        "bg": "#fef2f2",
        "badge": "日本名城 登城記念",
        "corner": "登城記念",
        "icon_path": "M150 170 h100 v-20 h-15 v-15 h-20 v-15 h-30 v15 h-20 v15 h-15 z",
    },
    "michinoeki": {
        "color": "#b45309",
        "ink": "#92400e",
        "bg": "#fffbeb",
        "badge": "道の駅 登録記念",
        "corner": "来駅記念",
        "icon_path": "M155 135 l45 -25 l45 25 v45 h-90 z",
    },
    "highway": {
        "color": "#1d4ed8",
        "ink": "#1e40af",
        "bg": "#eff6ff",
        "badge": "ハイウェイスタンプ",
        "corner": "休憩記念",
        "icon_path": "M160 165 h80 M165 140 h70 l15 25 h-100 z",
    },
    "temple_shrine": {
        "color": "#7e22ce",
        "ink": "#6b21a8",
        "bg": "#faf5ff",
        "badge": "御朱印・参拝記念",
        "corner": "奉拝",
        "icon_path": "M140 125 h120 M150 140 h100 M170 140 v40 M230 140 v40",
    },
    "eki": {
        "color": "#047857",
        "ink": "#065f46",
        "bg": "#ecfdf5",
        "badge": "駅スタンプ",
        "corner": "乗車記念",
        "icon_path": "M155 110 h90 v60 h-90 z",
    }
}


def clean_name_for_seal(name_ja: str) -> str:
    cleaned = re.sub(r'\(.+?\)|（.+?）', '', name_ja).strip()
    return cleaned


def generate_seal_svg(stamp: dict) -> str:
    cat = stamp.get("category", "castle")
    cfg = CATEGORY_CONFIG.get(cat, CATEGORY_CONFIG["castle"])

    name_ja = clean_name_for_seal(stamp.get("name_ja", stamp.get("name", "")))
    pref = stamp.get("prefecture", "")

    # Castle number or ID
    no_match = re.search(r'No\.(\d+)', stamp.get("name", "") + " " + stamp.get("name_ja", ""))
    sub_title = f"No.{int(no_match.group(1)):03d} • {pref}" if no_match else f"{pref} • {stamp.get('city', '')}"

    # Calculate font sizes based on character count
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
    else:
        font_size = 24
        mid = (char_len + 1) // 2
        lines = [name_ja[:mid], name_ja[mid:]]

    if len(lines) == 1:
        lines_svg = f'<text x="200" y="210" font-family="serif" font-weight="900" font-size="{font_size}" fill="{cfg["ink"]}" text-anchor="middle" letter-spacing="4">{lines[0]}</text>'
    else:
        lines_svg = f'''<text x="200" y="195" font-family="serif" font-weight="900" font-size="{font_size}" fill="{cfg["ink"]}" text-anchor="middle" letter-spacing="3">{lines[0]}</text>
  <text x="200" y="235" font-family="serif" font-weight="900" font-size="{font_size}" fill="{cfg["ink"]}" text-anchor="middle" letter-spacing="3">{lines[1]}</text>'''

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400" width="100%" height="100%">
  <!-- Traditional Japanese Rubber Stamp / Hanko Graphic -->
  <defs>
    <filter id="hanko-rough-{stamp['id']}" x="0%" y="0%" width="100%" height="100%">
      <feTurbulence type="fractalNoise" baseFrequency="0.04" numOctaves="3" result="noise" />
      <feDisplacementMap in="SourceGraphic" in2="noise" scale="3" xChannelSelector="R" yChannelSelector="G" />
    </filter>
  </defs>

  <g filter="url(#hanko-rough-{stamp['id']})">
    <!-- Outer Decorative Stamp Border -->
    <circle cx="200" cy="200" r="185" fill="none" stroke="{cfg["ink"]}" stroke-width="8" stroke-dasharray="16 6" />
    <circle cx="200" cy="200" r="172" fill="none" stroke="{cfg["ink"]}" stroke-width="3" />
    
    <!-- Inner concentric ring -->
    <circle cx="200" cy="200" r="148" fill="{cfg["bg"]}" stroke="{cfg["ink"]}" stroke-width="2" stroke-dasharray="4 4" opacity="0.6"/>

    <!-- Category Header Ribbon / Badge -->
    <text x="200" y="85" font-family="serif" font-weight="bold" font-size="22" fill="{cfg["ink"]}" text-anchor="middle" letter-spacing="6">{cfg["badge"]}</text>
    
    <!-- Central Motif / Icon -->
    <path d="{cfg["icon_path"]}" fill="none" stroke="{cfg["ink"]}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" />

    <!-- Stamp Japanese Name (Kanji) -->
    {lines_svg}

    <!-- Registration Subtitle (Prefecture & Castle Number) -->
    <text x="200" y="285" font-family="sans-serif" font-weight="bold" font-size="16" fill="{cfg["ink"]}" text-anchor="middle" letter-spacing="2">{sub_title}</text>

    <!-- Bottom Commemorative Seal Corner -->
    <rect x="150" y="315" width="100" height="30" rx="6" fill="none" stroke="{cfg["ink"]}" stroke-width="3" />
    <text x="200" y="336" font-family="serif" font-weight="900" font-size="14" fill="{cfg["ink"]}" text-anchor="middle" letter-spacing="4">{cfg["corner"]}</text>
  </g>
</svg>'''
    return svg


def main():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        stamps = json.load(f)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    existing_files = set(os.listdir(OUTPUT_DIR))

    generated_count = 0
    assigned_count = 0

    for stamp in stamps:
        stamp_id = stamp["id"]
        jpg_name = f"{stamp_id}.jpg"
        png_name = f"{stamp_id}.png"
        svg_name = f"{stamp_id}.svg"

        if jpg_name in existing_files:
            stamp["imageUrl"] = f"/images/stamps/{jpg_name}"
            assigned_count += 1
        elif png_name in existing_files:
            stamp["imageUrl"] = f"/images/stamps/{png_name}"
            assigned_count += 1
        elif svg_name in existing_files:
            stamp["imageUrl"] = f"/images/stamps/{svg_name}"
            assigned_count += 1
        else:
            svg_path = os.path.join(OUTPUT_DIR, svg_name)
            svg_content = generate_seal_svg(stamp)
            with open(svg_path, "w", encoding="utf-8") as f:
                f.write(svg_content)
            existing_files.add(svg_name)
            stamp["imageUrl"] = f"/images/stamps/{svg_name}"
            generated_count += 1

    print(f"Assigned existing images: {assigned_count}")
    print(f"Generated new Hanko SVGs: {generated_count}")
    print(f"Total stamps processed: {len(stamps)}")

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(stamps, f, ensure_ascii=False, indent=2)

    print(f"Successfully updated {DATA_PATH} with 100% valid offline image paths.")


if __name__ == "__main__":
    main()
