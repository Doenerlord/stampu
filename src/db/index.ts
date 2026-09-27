import Dexie, { type Table } from 'dexie';
import type { VisitedRecord, WishlistRecord, OfflinePackRecord } from '../types/stamp';

export class StampuDatabase extends Dexie {
  visitedStamps!: Table<VisitedRecord, number>;
  wishlistStamps!: Table<WishlistRecord, number>;
  offlinePacks!: Table<OfflinePackRecord, number>;

  constructor() {
    super('StampuDB');
    this.version(1).stores({
      visitedStamps: '++id, &stampId, visitedAt',
    });
    this.version(2).stores({
      visitedStamps: '++id, &stampId, visitedAt',
      wishlistStamps: '++id, &stampId, addedAt',
    });
    this.version(3).stores({
      visitedStamps: '++id, &stampId, visitedAt',
      wishlistStamps: '++id, &stampId, addedAt',
      offlinePacks: '++id, &prefectureId, downloadedAt',
    });
  }
}

export const db = new StampuDatabase();

export async function getVisitedStampIds(): Promise<Set<string>> {
  try {
    const records = await db.visitedStamps.toArray();
    return new Set(records.map((r) => r.stampId));
  } catch (err) {
    console.error('Failed to load visited stamps from Dexie', err);
    return new Set();
  }
}

export async function toggleVisitedStamp(stampId: string, notes?: string): Promise<boolean> {
  try {
    const existing = await db.visitedStamps.where('stampId').equals(stampId).first();
    if (existing && existing.id !== undefined) {
      await db.visitedStamps.delete(existing.id);
      return false;
    } else {
      await db.visitedStamps.add({
        stampId,
        visitedAt: new Date().toISOString(),
        notes: notes || '',
      });
      return true;
    }
  } catch (err) {
    console.error('Failed to toggle visited stamp in Dexie', err);
    return false;
  }
}

export async function isStampVisited(stampId: string): Promise<boolean> {
  try {
    const count = await db.visitedStamps.where('stampId').equals(stampId).count();
    return count > 0;
  } catch {
    return false;
  }
}

export async function getWishlistStampIds(): Promise<Set<string>> {
  try {
    const records = await db.wishlistStamps.toArray();
    return new Set(records.map((r) => r.stampId));
  } catch (err) {
    console.error('Failed to load wishlist stamps from Dexie', err);
    return new Set();
  }
}

export async function toggleWishlistStamp(stampId: string, notes?: string): Promise<boolean> {
  try {
    const existing = await db.wishlistStamps.where('stampId').equals(stampId).first();
    if (existing && existing.id !== undefined) {
      await db.wishlistStamps.delete(existing.id);
      return false;
    } else {
      await db.wishlistStamps.add({
        stampId,
        addedAt: new Date().toISOString(),
        notes: notes || '',
      });
      return true;
    }
  } catch (err) {
    console.error('Failed to toggle wishlist stamp in Dexie', err);
    return false;
  }
}

export async function isStampInWishlist(stampId: string): Promise<boolean> {
  try {
    const count = await db.wishlistStamps.where('stampId').equals(stampId).count();
    return count > 0;
  } catch {
    return false;
  }
}

export async function getDownloadedPackIds(): Promise<Set<string>> {
  try {
    const records = await db.offlinePacks.toArray();
    return new Set(records.map((r) => r.prefectureId));
  } catch (err) {
    console.error('Failed to load downloaded packs from Dexie', err);
    return new Set();
  }
}

export async function saveDownloadedPack(prefectureId: string, stampCount: number, sizeBytes: number): Promise<void> {
  try {
    const existing = await db.offlinePacks.where('prefectureId').equals(prefectureId).first();
    if (existing && existing.id !== undefined) {
      await db.offlinePacks.update(existing.id, {
        downloadedAt: new Date().toISOString(),
        stampCount,
        sizeBytes,
      });
    } else {
      await db.offlinePacks.add({
        prefectureId,
        downloadedAt: new Date().toISOString(),
        stampCount,
        sizeBytes,
      });
    }
  } catch (err) {
    console.error('Failed to save downloaded pack in Dexie', err);
  }
}

export async function deleteDownloadedPack(prefectureId: string): Promise<void> {
  try {
    const existing = await db.offlinePacks.where('prefectureId').equals(prefectureId).first();
    if (existing && existing.id !== undefined) {
      await db.offlinePacks.delete(existing.id);
    }
  } catch (err) {
    console.error('Failed to delete downloaded pack from Dexie', err);
  }
}

export async function getDownloadedPacks(): Promise<OfflinePackRecord[]> {
  try {
    return await db.offlinePacks.toArray();
  } catch (err) {
    console.error('Failed to load downloaded pack records from Dexie', err);
    return [];
  }
}

