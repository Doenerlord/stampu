import type { StampCategory } from '../types/stamp';

export interface CategoryInfo {
  id: StampCategory;
  label: string;
  labelJa: string;
  iconName: 'Train' | 'Store' | 'Car' | 'Castle' | 'Sparkles' | 'Radio' | 'Bath' | 'Ship' | 'Plane';
  hexColor: string;
  badgeClass: string;
  activeClass: string;
}

export const CATEGORIES: Record<StampCategory, CategoryInfo> = {
  eki: {
    id: 'eki',
    label: 'Eki Stations',
    labelJa: '駅スタンプ',
    iconName: 'Train',
    hexColor: '#059669', // emerald-600
    badgeClass: 'bg-emerald-950/80 text-emerald-300 border-emerald-700/50',
    activeClass: 'bg-emerald-600 text-white border-emerald-500 shadow-emerald-900/40',
  },
  michinoeki: {
    id: 'michinoeki',
    label: 'Michi-no-Eki',
    labelJa: '道の駅',
    iconName: 'Store',
    hexColor: '#d97706', // amber-600
    badgeClass: 'bg-amber-950/80 text-amber-300 border-amber-700/50',
    activeClass: 'bg-amber-600 text-white border-amber-500 shadow-amber-900/40',
  },
  highway: {
    id: 'highway',
    label: 'Highway SA/PA',
    labelJa: 'ハイウェイ',
    iconName: 'Car',
    hexColor: '#2563eb', // blue-600
    badgeClass: 'bg-blue-950/80 text-blue-300 border-blue-700/50',
    activeClass: 'bg-blue-600 text-white border-blue-500 shadow-blue-900/40',
  },
  castle: {
    id: 'castle',
    label: '100 Castles',
    labelJa: '日本100名城',
    iconName: 'Castle',
    hexColor: '#e11d48', // rose-600
    badgeClass: 'bg-rose-950/80 text-rose-300 border-rose-700/50',
    activeClass: 'bg-rose-600 text-white border-rose-500 shadow-rose-900/40',
  },
  temple_shrine: {
    id: 'temple_shrine',
    label: 'Temples & Shrines',
    labelJa: '寺社・御朱印',
    iconName: 'Sparkles',
    hexColor: '#9333ea', // purple-600
    badgeClass: 'bg-purple-950/80 text-purple-300 border-purple-700/50',
    activeClass: 'bg-purple-600 text-white border-purple-500 shadow-purple-900/40',
  },
  tower: {
    id: 'tower',
    label: 'Japan Towers',
    labelJa: 'タワー・展望台',
    iconName: 'Radio',
    hexColor: '#0284c7', // sky-600
    badgeClass: 'bg-sky-950/80 text-sky-300 border-sky-700/50',
    activeClass: 'bg-sky-600 text-white border-sky-500 shadow-sky-900/40',
  },
  onsen: {
    id: 'onsen',
    label: 'Onsen & Ryokan',
    labelJa: '温泉・名湯',
    iconName: 'Bath',
    hexColor: '#ea580c', // orange-600
    badgeClass: 'bg-orange-950/80 text-orange-300 border-orange-700/50',
    activeClass: 'bg-orange-600 text-white border-orange-500 shadow-orange-900/40',
  },
  ferry: {
    id: 'ferry',
    label: 'Ferry & Port',
    labelJa: 'フェリー・御船印',
    iconName: 'Ship',
    hexColor: '#0891b2', // cyan-600
    badgeClass: 'bg-cyan-950/80 text-cyan-300 border-cyan-700/50',
    activeClass: 'bg-cyan-600 text-white border-cyan-500 shadow-cyan-900/40',
  },
  airport: {
    id: 'airport',
    label: 'Airports',
    labelJa: '空港・御翔印',
    iconName: 'Plane',
    hexColor: '#4f46e5', // indigo-600
    badgeClass: 'bg-indigo-950/80 text-indigo-300 border-indigo-700/50',
    activeClass: 'bg-indigo-600 text-white border-indigo-500 shadow-indigo-900/40',
  },
};

export const ALL_CATEGORIES = Object.values(CATEGORIES);
