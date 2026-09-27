import { addProtocol } from 'maplibre-gl';

const CACHE_NAME = 'stampu-tiles-cache-v1';

let isProtocolRegistered = false;

// Tile server mapping
export const TILE_SOURCES: Record<string, {
  remoteTemplate: (z: number, a: number, b: number) => string;
  localPath: (z: number, a: number, b: number) => string;
  ext: string;
}> = {
  esri: {
    // Esri uses {z}/{y}/{x}
    remoteTemplate: (z, y, x) =>
      `https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/${z}/${y}/${x}`,
    localPath: (z, y, x) => `/tiles/esri/${z}/${y}/${x}.jpg`,
    ext: 'jpg',
  },
  gsi_std: {
    // GSI uses {z}/{x}/{y}
    remoteTemplate: (z, x, y) =>
      `https://cyberjapandata.gsi.go.jp/xyz/std/${z}/${x}/${y}.png`,
    localPath: (z, x, y) => `/tiles/gsi_std/${z}/${x}/${y}.png`,
    ext: 'png',
  },
  gsi_pale: {
    remoteTemplate: (z, x, y) =>
      `https://cyberjapandata.gsi.go.jp/xyz/pale/${z}/${x}/${y}.png`,
    localPath: (z, x, y) => `/tiles/gsi_pale/${z}/${x}/${y}.png`,
    ext: 'png',
  },
};

/**
 * Register the 'stampu' custom protocol in MapLibre GL JS.
 * Protocol URL format: stampu://{source}/{z}/{arg1}/{arg2}
 * - For esri: stampu://esri/{z}/{y}/{x}
 * - For gsi_std: stampu://gsi_std/{z}/{x}/{y}
 * - For gsi_pale: stampu://gsi_pale/{z}/{x}/{y}
 */
export function registerOfflineTileProtocol() {
  if (isProtocolRegistered) return;
  isProtocolRegistered = true;

  addProtocol('stampu', async (params, abortController) => {
    // URL looks like: stampu://esri/4/5/13 or stampu://gsi_std/4/13/5
    const urlParts = params.url.replace(/^stampu:\/\//, '').split('/');
    if (urlParts.length < 4) {
      throw new Error(`Invalid stampu tile URL: ${params.url}`);
    }

    const [sourceKey, zStr, aStr, bStr] = urlParts;
    const z = parseInt(zStr, 10);
    const a = parseInt(aStr, 10);
    const b = parseInt(bStr, 10);

    const sourceConfig = TILE_SOURCES[sourceKey] || TILE_SOURCES.esri;
    const localUrl = sourceConfig.localPath(z, a, b);
    const remoteUrl = sourceConfig.remoteTemplate(z, a, b);

    // 1. Check local bundled assets in /tiles/...
    try {
      const localRes = await fetch(localUrl, {
        signal: abortController.signal,
        cache: 'no-cache',
      });
      if (localRes.ok) {
        const data = await localRes.arrayBuffer();
        if (data.byteLength > 200) {
          return { data };
        }
      }
    } catch {
      // Local bundled tile not found, continue to cache / network
    }

    // 2. Check CacheStorage
    let cache: Cache | null = null;
    if (typeof caches !== 'undefined') {
      try {
        cache = await caches.open(CACHE_NAME);
        const cachedResponse = await cache.match(params.url);
        if (cachedResponse) {
          const data = await cachedResponse.arrayBuffer();
          if (data.byteLength > 200) {
            return { data };
          }
        }
      } catch (err) {
        console.warn('CacheStorage read error:', err);
      }
    }

    // 3. Fetch from remote network and cache if online
    try {
      const networkRes = await fetch(remoteUrl, {
        signal: abortController.signal,
      });

      if (networkRes.ok) {
        const data = await networkRes.clone().arrayBuffer();
        if (cache && data.byteLength > 200) {
          // Asynchronously save to cache under the stampu:// URL
          cache.put(params.url, networkRes).catch(() => {});
        }
        return { data };
      }
    } catch (netErr) {
      // Network failure (offline mode)
    }

    throw new Error(`Tile ${params.url} not available offline`);
  });
}

/**
 * Get offline cache stats
 */
export async function getTileCacheStats(): Promise<{ count: number; estimatedSizeMB: number }> {
  if (typeof caches === 'undefined') {
    return { count: 0, estimatedSizeMB: 0 };
  }
  try {
    const cache = await caches.open(CACHE_NAME);
    const requests = await cache.keys();
    // Approximate 25KB per tile average
    const estimatedSizeMB = (requests.length * 25) / 1024;
    return {
      count: requests.length,
      estimatedSizeMB: Math.round(estimatedSizeMB * 10) / 10,
    };
  } catch {
    return { count: 0, estimatedSizeMB: 0 };
  }
}

/**
 * Clear the offline tile cache
 */
export async function clearTileCache(): Promise<boolean> {
  if (typeof caches === 'undefined') return false;
  try {
    return await caches.delete(CACHE_NAME);
  } catch {
    return false;
  }
}

/**
 * Math helpers to convert Lon/Lat to Slippy Tile coordinates
 */
export function lon2tile(lon: number, zoom: number): number {
  return Math.floor(((lon + 180) / 360) * Math.pow(2, zoom));
}

export function lat2tile(lat: number, zoom: number): number {
  const rad = (lat * Math.PI) / 180;
  return Math.floor(
    ((1 - Math.log(Math.tan(rad) + 1 / Math.cos(rad)) / Math.PI) / 2) *
      Math.pow(2, zoom)
  );
}

export interface PrecacheProgress {
  current: number;
  total: number;
  isComplete: boolean;
  failed: number;
}

/**
 * Pre-cache tiles for a specific bounding box and zoom levels
 */
export async function precacheArea(
  bounds: { minLat: number; maxLat: number; minLon: number; maxLon: number },
  minZoom: number,
  maxZoom: number,
  source: 'esri' | 'gsi_std' = 'esri',
  onProgress?: (progress: PrecacheProgress) => void
): Promise<{ success: number; failed: number }> {
  if (typeof caches === 'undefined') {
    throw new Error('CacheStorage API is not supported in this environment');
  }

  const cache = await caches.open(CACHE_NAME);
  const sourceConfig = TILE_SOURCES[source];
  if (!sourceConfig) throw new Error(`Unknown source: ${source}`);

  // Calculate all tile requests needed
  interface TileItem {
    url: string;
    remoteUrl: string;
  }
  const tiles: TileItem[] = [];

  for (let z = minZoom; z <= maxZoom; z++) {
    const xMin = lon2tile(bounds.minLon, z);
    const xMax = lon2tile(bounds.maxLon, z);
    const yMin = lat2tile(bounds.maxLat, z);
    const yMax = lat2tile(bounds.minLat, z);

    const x1 = Math.min(xMin, xMax);
    const x2 = Math.max(xMin, xMax);
    const y1 = Math.min(yMin, yMax);
    const y2 = Math.max(yMin, yMax);

    for (let x = x1; x <= x2; x++) {
      for (let y = y1; y <= y2; y++) {
        if (source === 'esri') {
          // esri uses z/y/x
          tiles.push({
            url: `stampu://esri/${z}/${y}/${x}`,
            remoteUrl: sourceConfig.remoteTemplate(z, y, x),
          });
        } else {
          // gsi uses z/x/y
          tiles.push({
            url: `stampu://${source}/${z}/${x}/${y}`,
            remoteUrl: sourceConfig.remoteTemplate(z, x, y),
          });
        }
      }
    }
  }

  const total = tiles.length;
  let current = 0;
  let failed = 0;

  // Process with concurrency limit of 6
  const CONCURRENCY = 6;
  const queue = [...tiles];

  const worker = async () => {
    while (queue.length > 0) {
      const item = queue.shift();
      if (!item) break;

      try {
        // Check if already in cache
        const existing = await cache.match(item.url);
        if (!existing) {
          const resp = await fetch(item.remoteUrl, { mode: 'cors' });
          if (resp.ok) {
            await cache.put(item.url, resp);
          } else {
            failed++;
          }
        }
      } catch {
        failed++;
      } finally {
        current++;
        onProgress?.({
          current,
          total,
          isComplete: current >= total,
          failed,
        });
      }
    }
  };

  const workers = Array.from({ length: Math.min(CONCURRENCY, total) }, () => worker());
  await Promise.all(workers);

  return { success: total - failed, failed };
}
