export type StampCategory = 'eki' | 'michinoeki' | 'highway' | 'castle' | 'temple_shrine';

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
