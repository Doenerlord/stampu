import type { Stamp, PrefecturePack } from '../types/stamp';
import { saveDownloadedPack, deleteDownloadedPack } from '../db';
import { precacheArea } from './offlineMap';

export const IMAGE_CACHE_NAME = 'stampu-images-cache-v1';

export interface PackDownloadProgress {
  current: number;
  total: number;
  phase: 'images' | 'tiles' | 'complete';
  percent: number;
  message: string;
}

/**
 * Downloads and caches all stamp images and regional map tiles for a given prefecture pack.
 */
export async function downloadPrefecturePack(
  pack: PrefecturePack,
  allStamps: Stamp[],
  onProgress?: (progress: PackDownloadProgress) => void
): Promise<{ success: boolean; imageCount: number; sizeBytes: number }> {
  const prefStamps = allStamps.filter((s) => s.prefecture.toLowerCase() === pack.name.toLowerCase());
  const imageUrls = prefStamps
    .map((s) => s.imageUrl)
    .filter((url): url is string => Boolean(url && url.length > 0));

  let downloadedCount = 0;
  let totalBytes = 0;
  const totalItems = imageUrls.length + (pack.bounds ? 1 : 0);

  // 1. Download Stamp Images into CacheStorage
  try {
    const cache = await caches.open(IMAGE_CACHE_NAME);

    for (let i = 0; i < imageUrls.length; i++) {
      const url = imageUrls[i];
      try {
        const existing = await cache.match(url);
        if (!existing) {
          const resp = await fetch(url);
          if (resp.ok) {
            const blob = await resp.clone().blob();
            totalBytes += blob.size;
            await cache.put(url, resp);
          }
        } else {
          const blob = await existing.blob();
          totalBytes += blob.size;
        }
        downloadedCount++;
      } catch (err) {
        console.warn(`[offlinePacks] Failed to cache image: ${url}`, err);
      }

      if (onProgress) {
        const percent = Math.round(((i + 1) / totalItems) * 85);
        onProgress({
          current: i + 1,
          total: totalItems,
          phase: 'images',
          percent,
          message: `Caching stamp images (${i + 1}/${imageUrls.length})...`,
        });
      }
    }
  } catch (err) {
    console.error(`[offlinePacks] CacheStorage error while caching images for ${pack.name}:`, err);
  }

  // 2. Pre-cache regional map tiles if bounds are available
  if (pack.bounds) {
    if (onProgress) {
      onProgress({
        current: imageUrls.length + 1,
        total: totalItems,
        phase: 'tiles',
        percent: 90,
        message: `Caching regional map tiles for ${pack.name}...`,
      });
    }

    try {
      // Pre-cache tiles at overview to regional zoom (9 to 12)
      await precacheArea(pack.bounds, 9, 12, 'esri');
    } catch (err) {
      console.warn(`[offlinePacks] Failed to precache map tiles for ${pack.name}:`, err);
    }
  }

  // 3. Mark pack as downloaded in Dexie
  await saveDownloadedPack(pack.id, prefStamps.length, totalBytes);

  if (onProgress) {
    onProgress({
      current: totalItems,
      total: totalItems,
      phase: 'complete',
      percent: 100,
      message: `${pack.name} (${pack.name_ja}) offline pack ready!`,
    });
  }

  return {
    success: true,
    imageCount: downloadedCount,
    sizeBytes: totalBytes,
  };
}

/**
 * Removes cached images and database status for a prefecture pack.
 */
export async function deletePrefecturePack(
  pack: PrefecturePack,
  allStamps: Stamp[]
): Promise<boolean> {
  const prefStamps = allStamps.filter((s) => s.prefecture.toLowerCase() === pack.name.toLowerCase());
  const imageUrls = prefStamps
    .map((s) => s.imageUrl)
    .filter((url): url is string => Boolean(url && url.length > 0));

  try {
    const cache = await caches.open(IMAGE_CACHE_NAME);
    await Promise.all(imageUrls.map((url) => cache.delete(url)));
  } catch (err) {
    console.warn(`[offlinePacks] Error clearing cache for ${pack.name}:`, err);
  }

  await deleteDownloadedPack(pack.id);
  return true;
}
