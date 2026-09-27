import Dexie, { type Table } from 'dexie';
import type { VisitedRecord, WishlistRecord } from '../types/stamp';

export class StampuDatabase extends Dexie {
  visitedStamps!: Table<VisitedRecord, number>;
  wishlistStamps!: Table<WishlistRecord, number>;

  constructor() {
    super('StampuDB');
    this.version(1).stores({
      visitedStamps: '++id, &stampId, visitedAt',
    });
    this.version(2).stores({
      visitedStamps: '++id, &stampId, visitedAt',
      wishlistStamps: '++id, &stampId, addedAt',
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

