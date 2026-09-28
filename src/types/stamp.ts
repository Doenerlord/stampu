export type StampCategory = 'eki' | 'michinoeki' | 'highway' | 'castle' | 'temple_shrine' | 'tower';

export interface Stamp {
  id: string;
  name: string;
  name_ja: string;
  name_romaji: string;
  category: StampCategory;
  prefecture: string;
  city: string;
  address: string;
  coordinates: [number, number]; // [lng, lat]
  stampLocation: string; // e.g., 設置場所 (ticket gate, information counter)
  hours: string; // e.g., 利用可能時間
  operator?: string; // e.g., JR East, NEXCO Central
  description: string;
  imageUrl?: string;
  visited?: boolean;
}

export interface VisitedRecord {
  id?: number;
  stampId: string;
  visitedAt: string;
  notes?: string;
  rating?: number;
}

export interface WishlistRecord {
  id?: number;
  stampId: string;
  addedAt: string;
  notes?: string;
}

export interface CategoryMeta {
  id: StampCategory;
  name: string;
  name_ja: string;
  iconName: string;
  color: string;
  badgeBg: string;
  badgeText: string;
  markerColor: string;
}

export interface PrefecturePack {
  id: string; // e.g. "tokyo", "hokkaido"
  name: string; // "Tokyo"
  name_ja: string; // "東京都"
  region: string; // "Kanto", "Tohoku", etc.
  stampCount: number;
  categories: Record<string, number>;
  bounds: {
    minLat: number;
    maxLat: number;
    minLon: number;
    maxLon: number;
  } | null;
  estimatedSizeMB: number;
}

export interface OfflinePackRecord {
  id?: number;
  prefectureId: string;
  downloadedAt: string;
  stampCount: number;
  sizeBytes: number;
}
