<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';
import type { Stamp, StampCategory } from '../types/stamp';
import { CATEGORIES, ALL_CATEGORIES } from '../constants/categories';
import {
  Train,
  Store,
  Car,
  Castle,
  Sparkles,
  Radio,
  Layers,
  Search,
  X,
  CheckCircle2,
  CircleDot,
  Star,
  FolderDown,
  Navigation,
  Compass,
  MapPin,
  Clock,
  Languages,
  ExternalLink,
  ChevronLeft,
  SlidersHorizontal,
} from 'lucide-vue-next';
import AskStaffModal from './AskStaffModal.vue';
import { openInGoogleMaps, calculateDistanceKm, formatDistance } from '../utils/geo';

const props = defineProps<{
  selectedCategory: StampCategory | 'all';
  visitedFilter: 'all' | 'visited' | 'unvisited' | 'wishlist';
  searchQuery: string;
  categoryCounts: Record<string, number>;
  visitedCount: number;
  wishlistCount: number;
  totalCount: number;
  downloadedPacksCount?: number;
  selectedStamp?: Stamp | null;
  stamps?: Stamp[];
  visitedStampIds?: Set<string>;
  wishlistStampIds?: Set<string>;
  userLocation?: { lat: number; lng: number } | null;
}>();

const emit = defineEmits<{
  (e: 'update:selectedCategory', value: StampCategory | 'all'): void;
  (e: 'update:visitedFilter', value: 'all' | 'visited' | 'unvisited' | 'wishlist'): void;
  (e: 'update:searchQuery', value: string): void;
  (e: 'openWishlistModal'): void;
  (e: 'openPacksModal'): void;
  (e: 'openNearbyModal'): void;
  (e: 'selectStamp', stamp: Stamp): void;
  (e: 'closeSelectedStamp'): void;
  (e: 'toggleCollected', stampId: string): void;
  (e: 'toggleWishlist', stampId: string): void;
  (e: 'focusMap', coords: [number, number]): void;
}>();

const iconMap = {
  Train,
  Store,
  Car,
  Castle,
  Sparkles,
  Radio,
};

const searchInputRef = ref<HTMLInputElement | null>(null);
const isAskStaffOpen = ref(false);
const isImageModalOpen = ref(false);
const hasImageError = ref(false);

const visitedPercentage = computed(() => {
  if (props.totalCount === 0) return 0;
  return Math.round((props.visitedCount / props.totalCount) * 100);
});

const selectedStampCategoryInfo = computed(() => {
  if (!props.selectedStamp) return null;
  return CATEGORIES[props.selectedStamp.category];
});

// Matched stamps for desktop sidebar quick-list
const desktopStampList = computed(() => {
  if (!props.stamps) return [];
  // Limit to 100 items for silky performance in sidebar
  return props.stamps.slice(0, 80);
});

function selectCategory(cat: StampCategory | 'all') {
  emit('update:selectedCategory', cat);
}

function selectVisited(filter: 'all' | 'visited' | 'unvisited' | 'wishlist') {
  emit('update:visitedFilter', filter);
}

function cycleMobileStatusFilter() {
  const order: Array<'all' | 'unvisited' | 'visited' | 'wishlist'> = [
    'all',
    'unvisited',
    'visited',
    'wishlist',
  ];
  const idx = order.indexOf(props.visitedFilter);
  const next = order[(idx + 1) % order.length];
  emit('update:visitedFilter', next);
}

function onSearchInput(event: Event) {
  const target = event.target as HTMLInputElement;
  emit('update:searchQuery', target.value);
}

function clearSearch() {
  emit('update:searchQuery', '');
  searchInputRef.value?.focus();
}

function getStampDistance(coords: [number, number]): string | null {
  if (!props.userLocation) return null;
  const km = calculateDistanceKm(
    props.userLocation.lat,
    props.userLocation.lng,
    coords[1],
    coords[0]
  );
  return formatDistance(km);
}

function handleKeyDown(e: KeyboardEvent) {
  // Command+K / Ctrl+K to focus search
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault();
    searchInputRef.value?.focus();
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeyDown);
});

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown);
});
</script>

<template>
  <header role="region" aria-label="Filter and Search Controls">
    <!-- ========================================================================= -->
    <!-- DESKTOP ADAPTIVE SIDEBAR (Hidden on mobile < md, visible md:flex)        -->
    <!-- ========================================================================= -->
    <aside
      class="hidden md:flex fixed top-3 left-3 bottom-3 w-[390px] xl:w-[420px] z-30 flex-col bg-slate-900/95 backdrop-blur-2xl border border-slate-700/60 shadow-2xl rounded-[28px] overflow-hidden pointer-events-auto text-slate-100 transition-all duration-300"
    >
      <!-- Sidebar Header -->
      <div class="p-4 border-b border-slate-800 flex flex-col gap-3">
        <!-- Top Row: Brand & Progress Badge -->
        <div class="flex items-center justify-between gap-2">
          <div class="flex items-center gap-2.5">
            <div
              class="w-9 h-9 rounded-2xl bg-gradient-to-tr from-red-600 via-rose-500 to-amber-500 flex items-center justify-center text-white shadow-md shadow-red-900/30 flex-shrink-0"
            >
              <span class="font-bold text-lg leading-none font-serif">印</span>
            </div>
            <div>
              <h1 class="text-sm font-bold text-slate-100 leading-tight tracking-wide flex items-center gap-1.5">
                STAMPU
                <span class="text-[10px] font-normal px-1.5 py-0.5 rounded bg-red-950 text-red-300 border border-red-800/40">スタンプ</span>
              </h1>
              <p class="text-[11px] text-slate-400">Japan Explorer</p>
            </div>
          </div>

          <!-- Progress Pill -->
          <div
            class="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-800/90 border border-slate-700 text-xs flex-shrink-0"
            :title="`${visitedCount} of ${totalCount} collected`"
          >
            <CheckCircle2 class="w-3.5 h-3.5 text-emerald-400" />
            <span class="text-slate-300 font-medium">
              <strong class="text-emerald-400">{{ visitedCount }}</strong> / {{ totalCount }}
            </span>
            <span class="text-[10px] text-slate-400 bg-slate-700/60 px-1 rounded-sm">{{ visitedPercentage }}%</span>
          </div>
        </div>

        <!-- Quick Action Trigger Pills Row -->
        <div class="flex items-center gap-1.5">
          <!-- Nearby Radar -->
          <button
            type="button"
            @click="$emit('openNearbyModal')"
            class="flex-1 flex items-center justify-center gap-1.5 py-1.5 px-2 rounded-xl bg-teal-500/15 hover:bg-teal-500/25 border border-teal-500/40 text-xs text-teal-300 font-semibold transition-all active:scale-95 shadow-xs"
            title="Nearby Stamp Radar (Umkreis-Suche)"
          >
            <Navigation class="w-3.5 h-3.5 text-teal-400" />
            <span>Radar</span>
          </button>

          <!-- Wishlist Modal -->
          <button
            type="button"
            @click="$emit('openWishlistModal')"
            class="flex-1 flex items-center justify-center gap-1.5 py-1.5 px-2 rounded-xl bg-amber-500/15 hover:bg-amber-500/25 border border-amber-500/40 text-xs text-amber-300 font-semibold transition-all active:scale-95 shadow-xs"
            title="Open Stamp Wishlist"
          >
            <Star class="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
            <span>Wishlist</span>
            <span class="text-[10px] bg-amber-500/30 text-amber-200 px-1.5 py-0.2 rounded-full font-bold">
              {{ wishlistCount }}
            </span>
          </button>

          <!-- Offline Packs -->
          <button
            type="button"
            @click="$emit('openPacksModal')"
            class="flex-1 flex items-center justify-center gap-1.5 py-1.5 px-2 rounded-xl bg-blue-500/15 hover:bg-blue-500/25 border border-blue-500/40 text-xs text-blue-300 font-semibold transition-all active:scale-95 shadow-xs"
            title="Manage Prefecture Offline Packs"
          >
            <FolderDown class="w-3.5 h-3.5 text-blue-400" />
            <span>Packs</span>
            <span class="text-[10px] bg-blue-500/30 text-blue-200 px-1.5 py-0.2 rounded-full font-bold">
              {{ downloadedPacksCount ?? 47 }}
            </span>
          </button>
        </div>

        <!-- Desktop Search Bar with ⌘K Badge -->
        <div class="relative">
          <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
          <input
            ref="searchInputRef"
            type="text"
            :value="searchQuery"
            @input="onSearchInput"
            placeholder="Station, Castle, City, Romaji..."
            class="w-full bg-slate-800/80 hover:bg-slate-800 focus:bg-slate-800 text-slate-100 placeholder-slate-400 text-xs sm:text-sm pl-9 pr-16 py-2 rounded-xl border border-slate-700/80 focus:border-red-500 focus:outline-none transition-colors"
          />
          <div class="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
            <button
              v-if="searchQuery"
              @click="clearSearch"
              type="button"
              class="p-1 text-slate-400 hover:text-slate-200 transition-colors"
              title="Clear search"
            >
              <X class="w-3.5 h-3.5" />
            </button>
            <kbd class="hidden sm:inline-block text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-700/70 border border-slate-600/70 text-slate-300 pointer-events-none">
              ⌘K
            </kbd>
          </div>
        </div>

        <!-- Status Filter Segmented Controls -->
        <div class="grid grid-cols-4 gap-1 bg-slate-800/80 p-1 rounded-xl border border-slate-700/70 text-xs">
          <button
            type="button"
            @click="selectVisited('all')"
            :class="[
              'py-1 rounded-lg font-medium transition-all text-center',
              visitedFilter === 'all'
                ? 'bg-slate-700 text-white shadow-xs font-semibold'
                : 'text-slate-400 hover:text-slate-200'
            ]"
          >
            All
          </button>
          <button
            type="button"
            @click="selectVisited('visited')"
            :class="[
              'py-1 rounded-lg font-medium flex items-center justify-center gap-1 transition-all',
              visitedFilter === 'visited'
                ? 'bg-emerald-600 text-white shadow-xs font-semibold'
                : 'text-slate-400 hover:text-emerald-300'
            ]"
            title="Show collected stamps only"
          >
            <CheckCircle2 class="w-3 h-3" />
            <span>Visited</span>
          </button>
          <button
            type="button"
            @click="selectVisited('unvisited')"
            :class="[
              'py-1 rounded-lg font-medium flex items-center justify-center gap-1 transition-all',
              visitedFilter === 'unvisited'
                ? 'bg-slate-700 text-white shadow-xs font-semibold'
                : 'text-slate-400 hover:text-slate-200'
            ]"
            title="Show uncollected stamps only"
          >
            <CircleDot class="w-3 h-3" />
            <span>To Find</span>
          </button>
          <button
            type="button"
            @click="selectVisited('wishlist')"
            :class="[
              'py-1 rounded-lg font-medium flex items-center justify-center gap-1 transition-all',
              visitedFilter === 'wishlist'
                ? 'bg-amber-500 text-slate-950 font-bold shadow-xs'
                : 'text-slate-400 hover:text-amber-300'
            ]"
            title="Filter map to show wishlist target stamps"
          >
            <Star :class="['w-3 h-3', visitedFilter === 'wishlist' ? 'fill-slate-950 text-slate-950' : 'fill-amber-400 text-amber-400']" />
            <span>Wishlist</span>
          </button>
        </div>
      </div>

      <!-- Sidebar Body: Detail View vs Overview/List View -->
      <div class="flex-1 overflow-y-auto min-h-0">
        <!-- MODE A: STAMP DETAILS (When a stamp is selected on desktop) -->
        <div v-if="selectedStamp" class="p-4 space-y-4">
          <!-- Back to List Button -->
          <button
            type="button"
            @click="$emit('closeSelectedStamp')"
            class="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white font-medium transition-colors"
          >
            <ChevronLeft class="w-4 h-4" />
            <span>Back to Explorer Overview</span>
          </button>

          <!-- Category & Status Badge -->
          <div v-if="selectedStampCategoryInfo" class="flex items-center justify-between gap-2">
            <span
              :class="[
                'inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border',
                selectedStampCategoryInfo.badgeClass
              ]"
            >
              <component :is="iconMap[selectedStampCategoryInfo.iconName]" class="w-3.5 h-3.5" />
              <span>{{ selectedStampCategoryInfo.label }}</span>
              <span class="text-[10px] opacity-75">({{ selectedStampCategoryInfo.labelJa }})</span>
            </span>

            <div class="flex items-center gap-1.5">
              <span
                v-if="visitedStampIds?.has(selectedStamp.id)"
                class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-950/80 text-emerald-300 border border-emerald-700/50"
              >
                <CheckCircle2 class="w-3.5 h-3.5 text-emerald-400" />
                Collected
              </span>
              <span
                v-if="wishlistStampIds?.has(selectedStamp.id)"
                class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-950/80 text-amber-300 border border-amber-600/50"
              >
                <Star class="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
                Wishlist
              </span>
            </div>
          </div>

          <!-- Titles -->
          <div>
            <h2 class="text-xl font-bold tracking-tight text-white leading-tight">
              {{ selectedStamp.name }}
            </h2>
            <div class="flex items-center gap-2 text-xs text-slate-400 font-medium mt-1">
              <span class="text-base text-slate-200 font-serif">{{ selectedStamp.name_ja }}</span>
              <span>•</span>
              <span class="italic text-slate-300">{{ selectedStamp.name_romaji }}</span>
            </div>
          </div>

          <!-- Stamp Showcase Card -->
          <div class="relative bg-slate-800/80 rounded-2xl p-3 border border-slate-700/80 flex items-center gap-3">
            <div
              class="relative flex-shrink-0 w-20 h-20 bg-stone-50 rounded-xl p-1 shadow-md border border-stone-200 flex items-center justify-center overflow-hidden cursor-pointer group hover:ring-2 hover:ring-rose-400 transition-all"
              @click="selectedStamp.imageUrl ? (isImageModalOpen = true) : null"
              title="Inspect stamp in high resolution"
            >
              <img
                v-if="selectedStamp.imageUrl && !hasImageError"
                :src="selectedStamp.imageUrl"
                :alt="selectedStamp.name"
                class="w-full h-full object-contain filter drop-shadow-xs transition-transform duration-200 group-hover:scale-110 select-none"
                loading="eager"
                @error="hasImageError = true"
              />
              <div
                v-else
                class="w-full h-full rounded-lg border-2 border-dashed border-red-600 text-red-600 flex flex-col items-center justify-center p-1 text-center font-serif text-[10px]"
              >
                <span>記念印</span>
              </div>
            </div>

            <div class="flex-1 min-w-0">
              <p class="text-xs text-slate-300 leading-relaxed line-clamp-3">
                {{ selectedStamp.description }}
              </p>
              <div class="mt-2 flex items-center gap-1.5">
                <button
                  type="button"
                  @click="$emit('focusMap', selectedStamp.coordinates)"
                  class="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg bg-slate-700/80 hover:bg-slate-700 text-xs text-rose-300 hover:text-white font-medium border border-slate-600/60 transition-colors"
                >
                  <Compass class="w-3 h-3 text-rose-400" />
                  <span>Center</span>
                </button>
                <button
                  type="button"
                  @click="openInGoogleMaps(selectedStamp.coordinates[1], selectedStamp.coordinates[0], selectedStamp.name)"
                  class="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg bg-blue-600/20 hover:bg-blue-600/30 text-xs text-blue-300 hover:text-white font-medium border border-blue-500/40 transition-colors"
                >
                  <ExternalLink class="w-3 h-3 text-blue-400" />
                  <span>Maps</span>
                </button>
              </div>
            </div>
          </div>

          <!-- Stamp Desk Location Callout with Ask Staff Trigger -->
          <div class="bg-amber-950/30 border border-amber-500/40 rounded-2xl p-3">
            <div class="flex items-center justify-between mb-1">
              <div class="flex items-center gap-1.5 text-amber-400 text-xs font-bold uppercase tracking-wider">
                <MapPin class="w-3.5 h-3.5 flex-shrink-0" />
                <span>Stamp Desk (設置場所)</span>
              </div>
              <button
                type="button"
                @click="isAskStaffOpen = true"
                class="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg bg-gradient-to-r from-amber-500 to-rose-500 hover:from-amber-400 hover:to-rose-400 text-slate-950 font-bold text-[10px] shadow-xs transition-all active:scale-95"
              >
                <Languages class="w-3 h-3" />
                <span>Ask Staff (日本で尋ねる)</span>
              </button>
            </div>
            <p class="text-xs text-amber-100 font-medium leading-snug">
              {{ selectedStamp.stampLocation }}
            </p>
          </div>

          <!-- Info Details -->
          <div class="space-y-2 text-xs">
            <div class="bg-slate-800/60 border border-slate-700/60 rounded-xl p-2.5 flex items-start gap-2">
              <Clock class="w-3.5 h-3.5 text-slate-400 mt-0.5 flex-shrink-0" />
              <div>
                <span class="text-slate-400">Hours: </span>
                <span class="text-slate-200 font-medium">{{ selectedStamp.hours }}</span>
              </div>
            </div>

            <div v-if="selectedStamp.operator" class="bg-slate-800/60 border border-slate-700/60 rounded-xl p-2.5 flex items-start gap-2">
              <Navigation class="w-3.5 h-3.5 text-slate-400 mt-0.5 flex-shrink-0" />
              <div>
                <span class="text-slate-400">Operator: </span>
                <span class="text-slate-200 font-medium">{{ selectedStamp.operator }}</span>
              </div>
            </div>

            <div class="bg-slate-800/60 border border-slate-700/60 rounded-xl p-2.5 flex items-start gap-2">
              <MapPin class="w-3.5 h-3.5 text-slate-400 mt-0.5 flex-shrink-0" />
              <div>
                <span class="text-slate-400">Address: </span>
                <span class="text-slate-200 font-medium">{{ selectedStamp.address }} ({{ selectedStamp.city }}, {{ selectedStamp.prefecture }})</span>
              </div>
            </div>
          </div>

          <!-- Bottom Actions in Detail Mode -->
          <div class="pt-2 flex items-center gap-2">
            <button
              type="button"
              @click="$emit('toggleCollected', selectedStamp.id)"
              :class="[
                'flex-1 py-2.5 px-3 rounded-xl font-bold text-xs flex items-center justify-center gap-2 transition-all shadow-md active:scale-95',
                visitedStampIds?.has(selectedStamp.id)
                  ? 'bg-emerald-600 hover:bg-emerald-500 text-white'
                  : 'bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-500 hover:to-rose-500 text-white'
              ]"
            >
              <CheckCircle2 v-if="visitedStampIds?.has(selectedStamp.id)" class="w-3.5 h-3.5" />
              <span v-else class="font-serif">印</span>
              <span>{{ visitedStampIds?.has(selectedStamp.id) ? 'Collected!' : 'I Stamped This!' }}</span>
            </button>

            <button
              type="button"
              @click="$emit('toggleWishlist', selectedStamp.id)"
              :class="[
                'p-2.5 rounded-xl border transition-all active:scale-95',
                wishlistStampIds?.has(selectedStamp.id)
                  ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                  : 'bg-slate-800 text-slate-400 hover:text-amber-300 border-slate-700'
              ]"
              title="Toggle Wishlist"
            >
              <Star :class="['w-4 h-4', wishlistStampIds?.has(selectedStamp.id) ? 'fill-amber-400 text-amber-400' : '']" />
            </button>
          </div>
        </div>

        <!-- MODE B: OVERVIEW & CATEGORY MATRIX (When NO stamp selected) -->
        <div v-else class="p-4 space-y-4">
          <!-- Categories Matrix Header -->
          <div class="flex items-center justify-between text-xs text-slate-400 px-0.5">
            <span class="font-semibold uppercase tracking-wider text-[11px]">Categories (カテゴリ)</span>
            <span>{{ categoryCounts.all }} Total</span>
          </div>

          <!-- Category Cards Grid -->
          <div class="grid grid-cols-2 gap-2">
            <!-- All Stamps Option -->
            <button
              type="button"
              @click="selectCategory('all')"
              :class="[
                'flex items-center justify-between p-2.5 rounded-2xl border text-xs font-semibold transition-all col-span-2 shadow-xs active:scale-95',
                selectedCategory === 'all'
                  ? 'bg-slate-700 text-white border-slate-500 ring-2 ring-slate-400/40'
                  : 'bg-slate-800/70 text-slate-300 border-slate-700/80 hover:bg-slate-800'
              ]"
            >
              <div class="flex items-center gap-2">
                <Layers class="w-4 h-4 text-slate-300" />
                <span>All Stamps</span>
              </div>
              <span class="text-[10px] px-2 py-0.5 rounded-full font-bold bg-slate-700/90 text-slate-200">
                {{ categoryCounts.all }}
              </span>
            </button>

            <!-- 6 Official Stamp Categories -->
            <button
              v-for="cat in ALL_CATEGORIES"
              :key="cat.id"
              type="button"
              @click="selectCategory(cat.id)"
              :class="[
                'flex flex-col justify-between p-2.5 rounded-2xl border text-xs font-semibold transition-all shadow-xs active:scale-95 text-left h-[72px]',
                selectedCategory === cat.id
                  ? cat.activeClass + ' ring-2 ring-white/30'
                  : 'bg-slate-800/70 text-slate-300 border-slate-700/80 hover:bg-slate-800'
              ]"
            >
              <div class="flex items-center justify-between w-full">
                <component :is="iconMap[cat.iconName]" class="w-4 h-4" />
                <span class="text-[10px] px-1.5 py-0.2 rounded-full font-bold bg-slate-900/60 text-slate-200">
                  {{ categoryCounts[cat.id] || 0 }}
                </span>
              </div>
              <div>
                <div class="text-[11px] leading-tight font-bold truncate">{{ cat.label }}</div>
                <div class="text-[9px] opacity-75 font-serif">{{ cat.labelJa }}</div>
              </div>
            </button>
          </div>

          <!-- Matched Stamps List -->
          <div class="pt-2 border-t border-slate-800 space-y-2">
            <div class="flex items-center justify-between text-xs text-slate-400 px-0.5">
              <span class="font-medium">Matched Stamps</span>
              <span class="text-[11px] bg-slate-800 px-2 py-0.5 rounded-full text-slate-300">
                {{ desktopStampList.length }} shown
              </span>
            </div>

            <div class="space-y-1.5 max-h-[300px] overflow-y-auto pr-1">
              <button
                v-for="s in desktopStampList"
                :key="s.id"
                type="button"
                @click="$emit('selectStamp', s)"
                class="w-full flex items-center justify-between p-2 rounded-xl bg-slate-800/50 hover:bg-slate-800 border border-slate-700/50 transition-all text-left group"
              >
                <div class="min-w-0 flex-1 pr-2">
                  <div class="text-xs font-bold text-slate-200 truncate group-hover:text-red-400 transition-colors">
                    {{ s.name }}
                  </div>
                  <div class="text-[10px] text-slate-400 truncate flex items-center gap-1.5 mt-0.5">
                    <span class="font-serif text-slate-300">{{ s.name_ja }}</span>
                    <span>•</span>
                    <span>{{ s.prefecture }}</span>
                  </div>
                </div>

                <div class="flex items-center gap-1.5 flex-shrink-0">
                  <span
                    v-if="getStampDistance(s.coordinates)"
                    class="text-[10px] font-mono text-teal-300 bg-teal-950/60 px-1.5 py-0.5 rounded border border-teal-800/40"
                  >
                    {{ getStampDistance(s.coordinates) }}
                  </span>
                  <CheckCircle2
                    v-if="visitedStampIds?.has(s.id)"
                    class="w-3.5 h-3.5 text-emerald-400 flex-shrink-0"
                  />
                  <Star
                    v-else-if="wishlistStampIds?.has(s.id)"
                    class="w-3.5 h-3.5 fill-amber-400 text-amber-400 flex-shrink-0"
                  />
                </div>
              </button>
            </div>
          </div>
        </div>
      </div>
    </aside>

    <!-- ========================================================================= -->
    <!-- MOBILE MATERIAL 3 EXPRESSIVE UI (< md / Smartphone)                      -->
    <!-- ========================================================================= -->

    <!-- Mobile Top Bar: Sleek Material 3 Expressive Search Anchor -->
    <div
      class="md:hidden fixed top-0 inset-x-0 z-30 pointer-events-none px-3 pt-safe transition-all"
    >
      <div
        class="pointer-events-auto flex items-center gap-2 bg-slate-900/90 backdrop-blur-xl border border-slate-700/70 shadow-2xl rounded-full px-3 py-1.5 mx-auto max-w-lg"
      >
        <!-- Brand Icon Seal -->
        <div
          class="w-8 h-8 rounded-full bg-gradient-to-tr from-red-600 via-rose-500 to-amber-500 flex items-center justify-center text-white shadow-md shadow-red-900/30 flex-shrink-0"
          title="STAMPU Japan Explorer"
        >
          <span class="font-bold text-sm leading-none font-serif">印</span>
        </div>

        <!-- Search Input -->
        <div class="relative flex-1 min-w-0">
          <input
            type="text"
            :value="searchQuery"
            @input="onSearchInput"
            placeholder="Station, Castle, City..."
            class="w-full bg-transparent text-slate-100 placeholder-slate-400 text-xs sm:text-sm pl-1 pr-6 py-1 focus:outline-none"
          />
          <button
            v-if="searchQuery"
            @click="clearSearch"
            type="button"
            class="absolute right-0 top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-slate-200"
            title="Clear search"
          >
            <X class="w-3.5 h-3.5" />
          </button>
        </div>

        <!-- Progress Mini Pill -->
        <div
          class="flex items-center gap-1 px-2.5 py-1 rounded-full bg-slate-800/90 border border-slate-700 text-xs flex-shrink-0"
          :title="`${visitedCount} of ${totalCount} collected`"
        >
          <CheckCircle2 class="w-3 h-3 text-emerald-400" />
          <span class="text-slate-300 font-semibold text-[11px]">{{ visitedPercentage }}%</span>
        </div>
      </div>
    </div>

    <!-- Mobile Bottom Area: Category Chips Carousel + M3 Expressive Navigation Dock -->
    <div
      class="md:hidden fixed bottom-0 inset-x-0 z-30 pointer-events-none safe-bottom flex flex-col gap-2 transition-all"
    >
      <!-- Horizontally Scrollable M3 Category Chips -->
      <div
        class="pointer-events-auto flex items-center gap-1.5 overflow-x-auto no-scrollbar px-3 py-0.5 scroll-smooth"
        style="-webkit-overflow-scrolling: touch;"
      >
        <!-- All Stamps Pill -->
        <button
          type="button"
          @click="selectCategory('all')"
          :class="[
            'flex-shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold border transition-all shadow-md active:scale-95',
            selectedCategory === 'all'
              ? 'bg-slate-700 text-white border-slate-500 shadow-slate-900/50'
              : 'bg-slate-900/90 text-slate-300 border-slate-700/80 hover:bg-slate-800'
          ]"
        >
          <Layers class="w-3.5 h-3.5 text-slate-300" />
          <span>All Stamps</span>
          <span class="text-[10px] px-1.5 py-0.2 rounded-full font-bold bg-slate-800 text-slate-300">
            {{ categoryCounts.all }}
          </span>
        </button>

        <!-- 6 Category Pills -->
        <button
          v-for="cat in ALL_CATEGORIES"
          :key="cat.id"
          type="button"
          @click="selectCategory(cat.id)"
          :class="[
            'flex-shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold border transition-all shadow-md active:scale-95',
            selectedCategory === cat.id
              ? cat.activeClass
              : 'bg-slate-900/90 text-slate-300 border-slate-700/80 hover:bg-slate-800'
          ]"
        >
          <component :is="iconMap[cat.iconName]" class="w-3.5 h-3.5" />
          <span>{{ cat.label }}</span>
          <span class="text-[10px] px-1.5 py-0.2 rounded-full font-bold bg-slate-950/70 text-slate-200">
            {{ categoryCounts[cat.id] || 0 }}
          </span>
        </button>
      </div>

      <!-- M3 Expressive Floating Navigation Dock -->
      <nav
        class="pointer-events-auto mx-auto max-w-sm w-[calc(100%-1.5rem)] bg-slate-900/92 backdrop-blur-xl border border-slate-700/80 shadow-2xl rounded-full p-1.5 flex items-center justify-around"
        aria-label="Mobile Navigation Dock"
      >
        <!-- Tab 1: Status Filter Cycle Button -->
        <button
          type="button"
          @click="cycleMobileStatusFilter"
          :class="[
            'flex-1 flex flex-col items-center justify-center py-1 px-1 rounded-full transition-all active:scale-95 text-[10px] font-semibold',
            visitedFilter === 'visited'
              ? 'text-emerald-400 bg-emerald-500/15'
              : visitedFilter === 'unvisited'
                ? 'text-slate-300 bg-slate-800'
                : visitedFilter === 'wishlist'
                  ? 'text-amber-400 bg-amber-500/15'
                  : 'text-slate-400 hover:text-slate-200'
          ]"
          :title="`Current filter: ${visitedFilter}. Click to cycle.`"
        >
          <CheckCircle2 v-if="visitedFilter === 'visited'" class="w-4 h-4 text-emerald-400" />
          <CircleDot v-else-if="visitedFilter === 'unvisited'" class="w-4 h-4 text-slate-300" />
          <Star v-else-if="visitedFilter === 'wishlist'" class="w-4 h-4 fill-amber-400 text-amber-400" />
          <SlidersHorizontal v-else class="w-4 h-4 text-slate-400" />
          <span class="capitalize leading-none mt-0.5">{{ visitedFilter === 'all' ? 'Status' : visitedFilter }}</span>
        </button>

        <!-- Tab 2: Nearby Radar -->
        <button
          type="button"
          @click="$emit('openNearbyModal')"
          class="flex-1 flex flex-col items-center justify-center py-1 px-1 rounded-full text-slate-400 hover:text-teal-300 transition-all active:scale-95 text-[10px] font-semibold"
          title="Open Nearby Stamp Radar"
        >
          <Navigation class="w-4 h-4 text-teal-400" />
          <span class="leading-none mt-0.5">Radar</span>
        </button>

        <!-- Tab 3: Wishlist Modal -->
        <button
          type="button"
          @click="$emit('openWishlistModal')"
          class="flex-1 flex flex-col items-center justify-center py-1 px-1 rounded-full text-slate-400 hover:text-amber-300 transition-all active:scale-95 text-[10px] font-semibold relative"
          title="Open Stamp Wishlist"
        >
          <Star class="w-4 h-4 fill-amber-400 text-amber-400" />
          <span class="leading-none mt-0.5">Wishlist</span>
          <span
            v-if="wishlistCount > 0"
            class="absolute top-0.5 right-4 text-[9px] bg-amber-500 text-slate-950 px-1 rounded-full font-bold leading-tight"
          >
            {{ wishlistCount }}
          </span>
        </button>

        <!-- Tab 4: Offline Packs Modal -->
        <button
          type="button"
          @click="$emit('openPacksModal')"
          class="flex-1 flex flex-col items-center justify-center py-1 px-1 rounded-full text-slate-400 hover:text-blue-300 transition-all active:scale-95 text-[10px] font-semibold relative"
          title="Manage Offline Packs"
        >
          <FolderDown class="w-4 h-4 text-blue-400" />
          <span class="leading-none mt-0.5">Packs</span>
          <span
            class="absolute top-0.5 right-4 text-[9px] bg-blue-500 text-white px-1 rounded-full font-bold leading-tight"
          >
            {{ downloadedPacksCount ?? 47 }}
          </span>
        </button>
      </nav>
    </div>

    <!-- Ask Staff Flashcard Modal for Desktop Sidebar trigger -->
    <AskStaffModal
      v-if="selectedStamp"
      :is-open="isAskStaffOpen"
      :stamp="selectedStamp"
      @close="isAskStaffOpen = false"
    />
  </header>
</template>
