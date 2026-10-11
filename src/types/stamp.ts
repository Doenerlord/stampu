export type StampCategory =
  | 'eki'
  | 'michinoeki'
  | 'highway'
  | 'castle'
  | 'temple_shrine'
  | 'tower'
  | 'onsen'
  | 'ferry'
  | 'airport'
  | 'nature'
  | 'lighthouse'
  | 'museum'
  | 'anime'
  | 'garden'
  | 'shop'
  | 'tourist_info';

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
  railwayOperator?: string;
  railwayLine?: string;
  description: string;
  imageUrl?: string;
  visited?: boolean;
  source?: string;
  sourceUrl?: string;
  isTemporary?: boolean;
  event?: StampEventInfo;
}

export interface StampEventInfo {
  rallyId: string;
  rallyName: string;
  rallyNameJa?: string;
  validFrom: string;
  validUntil: string;
  stage?: number;
  reward?: string;
  rewardJa?: string;
  officialUrl?: string;
}

export interface StampRally {
  id: string;
  title: string;
  titleJa: string;
  organizer: string;
  description: string;
  validFrom: string;
  validUntil: string;
  stampIds: string[];
  reward?: string;
  rewardJa?: string;
  bannerGradient?: string;
  officialUrl?: string;
  source?: string;
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
