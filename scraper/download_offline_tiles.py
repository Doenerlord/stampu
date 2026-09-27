#!/usr/bin/env python3
"""
Pre-download offline map tiles for Japan Overview & Tokyo Yamanote Line.
Stores tiles locally in public/tiles/esri/{z}/{y}/{x}.jpg
"""

import os
import math
import urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "public", "tiles", "esri")

def deg2num(lat_deg, lon_deg, zoom):
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return (xtile, ytile)

def get_tiles_for_bounds(min_lat, max_lat, min_lon, max_lon, zoom):
    x_min, y_min = deg2num(max_lat, min_lon, zoom)
    x_max, y_max = deg2num(min_lat, max_lon, zoom)
    
    # Ensure min <= max
    x1, x2 = min(x_min, x_max), max(x_min, x_max)
    y1, y2 = min(y_min, y_max), max(y_min, y_max)
    
    tiles = []
    for x in range(x1, x2 + 1):
        for y in range(y1, y2 + 1):
            tiles.append((zoom, y, x))
    return tiles

def download_tile(tile_info):
    z, y, x = tile_info
    url = f"https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}"
    
    dest_dir = os.path.join(OUTPUT_DIR, str(z), str(y))
    dest_path = os.path.join(dest_dir, f"{x}.jpg")
    
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 500:
        return True
    
    os.makedirs(dest_dir, exist_ok=True)
    
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) StampuApp/1.0"
    })
    
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                data = resp.read()
                with open(dest_path, "wb") as f:
                    f.write(data)
                return True
    except Exception as e:
        print(f"Error fetching tile {z}/{y}/{x}: {e}")
        return False
    return False

def main():
    print("=" * 60)
    print(" DOWNLOADING CORE OFFLINE BASEMAP TILES (ESRI)")
    print("=" * 60)
    
    tiles_to_download = set()
    
    # 1. Japan Overview (Zoom 4 to 7)
    # Bounds: Lat 28 to 46, Lon 128 to 146
    for z in range(4, 8):
        tiles = get_tiles_for_bounds(28.0, 46.0, 128.0, 146.0, z)
        tiles_to_download.update(tiles)
        print(f"Japan z{z}: {len(tiles)} tiles")
        
    # 2. Central Tokyo / Yamanote Loop (Zoom 10 to 14)
    # Bounds: Lat 35.60 to 35.75, Lon 139.68 to 139.80
    for z in range(10, 15):
        tiles = get_tiles_for_bounds(35.60, 35.75, 139.68, 139.80, z)
        tiles_to_download.update(tiles)
        print(f"Tokyo Yamanote z{z}: {len(tiles)} tiles")
        
    # 3. Kansai Regional Loop (Osaka / Kyoto / Nara / Himeji) (Zoom 10 to 11)
    # Bounds: Lat 34.20 to 35.10, Lon 135.00 to 136.00
    for z in range(10, 12):
        tiles = get_tiles_for_bounds(34.20, 35.10, 135.00, 136.00, z)
        tiles_to_download.update(tiles)
        print(f"Kansai z{z}: {len(tiles)} tiles")
        
    tiles_list = list(tiles_to_download)
    print(f"\nTotal unique tiles to download: {len(tiles_list)}")
    
    success = 0
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = executor.map(download_tile, tiles_list)
        for r in results:
            if r:
                success += 1
                
    print(f"\nSuccessfully downloaded: {success}/{len(tiles_list)} tiles.")
    print(f"Stored in: {OUTPUT_DIR}")
    print("=" * 60)

if __name__ == "__main__":
    main()
