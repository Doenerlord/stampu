<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue';
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
  ChevronRight,
  SlidersHorizontal,
  Palette,
  Info,
  ZoomIn,
  ShieldCheck,
} from 'lucide-vue-next';
import AskStaffModal from './AskStaffModal.vue';
import StampSourceModal from './StampSourceModal.vue';
import { openInGoogleMaps, calculateDistanceKm, formatDistance } from '../utils/geo';
import { PRESET_PALETTES, applyMonetPalette, getDetectedMonetHex } from '../utils/theme';

const isThemeMenuOpen = ref(false);
const currentPaletteId = ref(
  (typeof localStorage !== 'undefined' && localStorage.getItem('stampu_theme_palette')) || 'monet'
);
const detectedMonetColor = ref(getDetectedMonetHex());

const activeThemeHex = computed(() => {
  if (currentPaletteId.value === 'monet') {
    return detectedMonetColor.value;
  }
  const found = PRESET_PALETTES.find((p) => p.id === currentPaletteId.value);
  return found ? found.seedHex : detectedMonetColor.value;
});

function selectPalette(id: string) {
  currentPaletteId.value = id;
  applyMonetPalette(id);
  detectedMonetColor.value = getDetectedMonetHex();
  isThemeMenuOpen.value = false;
}

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
const isSourceModalOpen = ref(false);
const hasImageError = ref(false);

watch(
  () => props.selectedStamp,
  () => {
    isImageModalOpen.value = false;
    isSourceModalOpen.value = false;
    hasImageError.value = false;
    isAskStaffOpen.value = false;
  }
);

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
  if (e.key === 'Escape') {
    if (isImageModalOpen.value) {
      isImageModalOpen.value = false;
      return;
    }
    if (isSourceModalOpen.value) {
      isSourceModalOpen.value = false;
      return;
    }
    if (isThemeMenuOpen.value) {
      isThemeMenuOpen.value = false;
      return;
    }
    if (isAskStaffOpen.value) {
      isAskStaffOpen.value = false;
      return;
    }
  }
  // Command+K / Ctrl+K to focus search
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault();
    searchInputRef.value?.focus();
  }
}

function onMonetColorDetected() {
  detectedMonetColor.value = getDetectedMonetHex();
}

onMounted(() => {
  window.addEventListener('keydown', handleKeyDown);
  window.addEventListener('monet-color-detected', onMonetColorDetected);
});

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown);
  window.removeEventListener('monet-color-detected', onMonetColorDetected);
});
</script>

<template>
  <header role="region" aria-label="Filter and Search Controls">
    <!-- ========================================================================= -->
    <!-- DESKTOP ADAPTIVE SIDEBAR (Hidden on mobile < md, visible md:flex)        -->
    <!-- ========================================================================= -->
    <aside
      class="hidden md:flex fixed top-3 left-3 bottom-3 w-[390px] xl:w-[420px] z-30 flex-col backdrop-blur-2xl shadow-2xl rounded-[28px] overflow-hidden pointer-events-auto text-slate-100 transition-all duration-300"
      style="background: var(--m3-surface-card, rgba(15, 23, 42, 0.95)); border: 1px solid var(--m3-border, rgba(51, 65, 85, 0.6)); box-shadow: 0 20px 50px rgba(0,0,0,0.5), 0 0 25px var(--m3-glow-subtle, transparent);"
    >
      <!-- Sidebar Header -->
      <div class="p-4 border-b border-slate-800/80 flex flex-col gap-3">
        <!-- Top Row: Brand & Progress Badge -->
        <div class="flex items-center justify-between gap-2">
          <div class="flex items-center gap-2.5">
            <div
              class="w-9 h-9 rounded-2xl flex items-center justify-center text-white shadow-md flex-shrink-0 cursor-pointer active:scale-95 transition-transform"
              style="background: var(--m3-primary); box-shadow: 0 4px 14px var(--m3-glow);"
              @click="isThemeMenuOpen = true"
              title="Change Theme Palette (Monet)"
            >
              <span class="font-bold text-lg leading-none font-serif">印</span>
            </div>
            <div>
              <h1 class="text-sm font-bold text-slate-100 leading-tight tracking-wide flex items-center gap-1.5">
                STAMPU
                <span
                  class="text-[10px] font-normal px-1.5 py-0.5 rounded border"
                  style="background: var(--m3-badge-bg); color: var(--m3-on-primary-container); border-color: var(--m3-border-subtle);"
                >スタンプ</span>
              </h1>
              <p class="text-[11px] text-slate-400">Japan Explorer</p>
            </div>
          </div>

          <div class="flex items-center gap-2">
            <!-- Palette Selector Trigger -->
            <button
              type="button"
              @click="isThemeMenuOpen = true"
              class="p-1.5 rounded-xl transition-colors hover:bg-white/10"
              style="color: var(--m3-primary);"
              title="Change Theme Palette (Monet)"
            >
              <Palette class="w-4 h-4" />
            </button>

            <!-- Progress Pill -->
            <div
              class="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs flex-shrink-0 border"
              style="background: var(--m3-badge-bg); border-color: var(--m3-border-subtle); color: var(--m3-on-primary-container);"
              :title="`${visitedCount} of ${totalCount} collected`"
            >
              <CheckCircle2 class="w-3.5 h-3.5 text-emerald-400" />
              <span class="font-medium">
                <strong class="text-emerald-400">{{ visitedCount }}</strong> / {{ totalCount }}
              </span>
              <span class="text-[10px] bg-black/30 px-1 rounded-sm">{{ visitedPercentage }}%</span>
            </div>
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
                ? 'text-white shadow-xs font-semibold'
                : 'text-slate-400 hover:text-slate-200'
            ]"
            :style="visitedFilter === 'all' ? { background: 'var(--m3-primary)', boxShadow: '0 2px 8px var(--m3-glow)' } : {}"
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

          <!-- Titles & Source Info Trigger -->
          <div class="flex items-start justify-between gap-2">
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

            <!-- Data Source & Verification Info Trigger Icon -->
            <button
              type="button"
              @click="isSourceModalOpen = true"
              class="p-2 rounded-xl border border-slate-700/80 bg-slate-800/80 hover:bg-slate-700 text-slate-400 hover:text-emerald-300 hover:border-emerald-500/40 transition-all flex-shrink-0 flex items-center gap-1 active:scale-95 shadow-xs"
              title="Stamp Data Sources & Verification (Datenquellen & Nachweise)"
              aria-label="Stamp sources and verification info"
            >
              <Info class="w-4 h-4 text-emerald-400" />
              <span class="text-[10px] font-semibold text-slate-300 hidden xl:inline">Quellen</span>
            </button>
          </div>

          <!-- Stamp Showcase Card -->
          <div
            class="relative rounded-2xl p-3 border flex items-center gap-3 transition-all"
            style="background: var(--m3-surface-highlight, #1e332a); border-color: var(--m3-border-subtle, #334155);"
          >
            <div
              class="relative flex-shrink-0 w-20 h-20 bg-stone-50 rounded-xl p-1 shadow-md border border-stone-200 flex items-center justify-center overflow-hidden cursor-pointer group hover:ring-2 hover:ring-rose-400 transition-all"
              @click="selectedStamp.imageUrl ? (isImageModalOpen = true) : null"
              title="Klicken zum Vergrößern (Click to enlarge stamp image)"
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

              <!-- Zoom Overlay on Hover -->
              <div
                v-if="selectedStamp.imageUrl && !hasImageError"
                class="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity rounded-lg"
              >
                <ZoomIn class="w-5 h-5 text-white filter drop-shadow-md" />
              </div>
            </div>

            <div class="flex-1 min-w-0">
              <p class="text-xs text-slate-300 leading-relaxed line-clamp-3">
                {{ selectedStamp.description }}
              </p>
              <div class="mt-2 flex items-center gap-1.5 flex-wrap">
                <button
                  v-if="selectedStamp.imageUrl"
                  type="button"
                  @click="isImageModalOpen = true"
                  class="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg bg-slate-700/80 hover:bg-slate-700 text-xs text-slate-200 hover:text-white font-medium border border-slate-600/60 transition-colors"
                  title="Enlarge stamp image"
                >
                  <ZoomIn class="w-3 h-3 text-slate-300" />
                  <span>Zoom</span>
                </button>
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
            <div
              class="border rounded-xl p-2.5 flex items-start gap-2 transition-all"
              style="background: var(--m3-surface-container, #0f1d18); border-color: var(--m3-border-subtle, #334155);"
            >
              <Clock class="w-3.5 h-3.5 text-slate-400 mt-0.5 flex-shrink-0" />
              <div>
                <span class="text-slate-400">Hours: </span>
                <span class="text-slate-200 font-medium">{{ selectedStamp.hours }}</span>
              </div>
            </div>

            <div
              v-if="selectedStamp.operator"
              class="border rounded-xl p-2.5 flex items-start gap-2 transition-all"
              style="background: var(--m3-surface-container, #0f1d18); border-color: var(--m3-border-subtle, #334155);"
            >
              <Navigation class="w-3.5 h-3.5 text-slate-400 mt-0.5 flex-shrink-0" />
              <div>
                <span class="text-slate-400">Operator: </span>
                <span class="text-slate-200 font-medium">{{ selectedStamp.operator }}</span>
              </div>
            </div>

            <div
              class="border rounded-xl p-2.5 flex items-start gap-2 transition-all"
              style="background: var(--m3-surface-container, #0f1d18); border-color: var(--m3-border-subtle, #334155);"
            >
              <MapPin class="w-3.5 h-3.5 text-slate-400 mt-0.5 flex-shrink-0" />
              <div>
                <span class="text-slate-400">Address: </span>
                <span class="text-slate-200 font-medium">{{ selectedStamp.address }} ({{ selectedStamp.city }}, {{ selectedStamp.prefecture }})</span>
              </div>
            </div>

            <!-- Data Source & Registry Trigger Card -->
            <div
              class="border rounded-xl p-2.5 flex items-center justify-between gap-2 transition-all cursor-pointer hover:border-emerald-500/50 hover:brightness-110 active:scale-[0.99]"
              style="background: var(--m3-surface-container, #0f1d18); border-color: var(--m3-border-subtle, #334155);"
              @click="isSourceModalOpen = true"
              title="Datenquellen & Offizielle Nachweise öffnen"
            >
              <div class="flex items-center gap-2 min-w-0">
                <ShieldCheck class="w-3.5 h-3.5 text-emerald-400 mt-0.5 flex-shrink-0" />
                <div class="truncate text-[11px]">
                  <span class="text-slate-400">Quelle: </span>
                  <span class="text-slate-200 font-semibold">{{ selectedStamp.source || selectedStamp.operator || 'Offizielles Register' }}</span>
                </div>
              </div>
              <span class="text-[10px] text-emerald-400 font-bold flex items-center gap-0.5 flex-shrink-0">
                Info <ChevronRight class="w-3 h-3" />
              </span>
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
                  ? 'text-white border-transparent'
                  : 'bg-slate-800/70 text-slate-300 border-slate-700/80 hover:bg-slate-800'
              ]"
              :style="selectedCategory === 'all' ? { background: 'var(--m3-primary)', boxShadow: '0 4px 14px var(--m3-glow)' } : {}"
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
                class="w-full flex items-center justify-between p-2 rounded-xl transition-all text-left group hover:brightness-110 active:scale-98"
                style="background: var(--m3-surface-container, #0f1d18); border: 1px solid var(--m3-border-subtle, #334155);"
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
      class="md:hidden fixed top-0 inset-x-0 z-30 pointer-events-none px-3 transition-all"
      style="padding-top: calc(max(env(safe-area-inset-top, 0px), 2.75rem) + 0.25rem);"
    >
      <div
        class="pointer-events-auto flex items-center gap-2 backdrop-blur-xl shadow-2xl rounded-full px-3 py-1.5 mx-auto max-w-lg transition-all"
        style="background: var(--m3-surface-card, rgba(15, 23, 42, 0.92)); border: 1px solid var(--m3-border, rgba(51, 65, 85, 0.7)); box-shadow: 0 10px 30px rgba(0,0,0,0.5), 0 0 20px var(--m3-glow-subtle, transparent);"
      >
        <!-- Brand Icon Seal with Monet primary color -->
        <div
          class="w-8 h-8 rounded-full flex items-center justify-center text-white shadow-md flex-shrink-0 cursor-pointer active:scale-95 transition-all"
          style="background: var(--m3-primary); box-shadow: 0 4px 14px var(--m3-glow);"
          @click="isThemeMenuOpen = true"
          title="Change Theme Palette (Monet)"
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

        <!-- Palette Theme Selector Button -->
        <button
          type="button"
          @click="isThemeMenuOpen = true"
          class="p-1.5 rounded-full flex-shrink-0 transition-colors hover:bg-white/10"
          style="color: var(--m3-primary);"
          title="Monet Theme Colors"
        >
          <Palette class="w-4 h-4" />
        </button>

        <!-- Progress Mini Pill -->
        <div
          class="flex items-center gap-1 px-2.5 py-1 rounded-full text-xs flex-shrink-0 transition-all border"
          style="background: var(--m3-badge-bg); border-color: var(--m3-border-subtle); color: var(--m3-on-primary-container);"
          :title="`${visitedCount} of ${totalCount} collected`"
        >
          <CheckCircle2 class="w-3 h-3 text-emerald-400" />
          <span class="font-semibold text-[11px]">{{ visitedPercentage }}%</span>
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
          class="flex-shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold transition-all shadow-md active:scale-95"
          :style="selectedCategory === 'all'
            ? { background: 'var(--m3-primary)', color: 'white', border: '1px solid transparent', boxShadow: '0 4px 16px var(--m3-glow)' }
            : { background: 'var(--m3-surface-card)', color: '#cbd5e1', border: '1px solid var(--m3-border-subtle)' }"
        >
          <Layers class="w-3.5 h-3.5" />
          <span>All Stamps</span>
          <span
            class="text-[10px] px-1.5 py-0.2 rounded-full font-bold"
            :style="selectedCategory === 'all' ? { background: 'rgba(0,0,0,0.25)', color: 'white' } : { background: 'rgba(255,255,255,0.1)', color: '#94a3b8' }"
          >
            {{ categoryCounts.all }}
          </span>
        </button>

        <!-- 6 Category Pills -->
        <button
          v-for="cat in ALL_CATEGORIES"
          :key="cat.id"
          type="button"
          @click="selectCategory(cat.id)"
          class="flex-shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold border transition-all shadow-md active:scale-95"
          :class="selectedCategory === cat.id ? cat.activeClass : 'text-slate-300 hover:bg-slate-800'"
          :style="selectedCategory === cat.id
            ? { borderColor: 'var(--m3-primary)', boxShadow: '0 4px 14px var(--m3-glow)' }
            : { background: 'var(--m3-surface-card)', borderColor: 'var(--m3-border-subtle)' }"
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
        class="pointer-events-auto mx-auto max-w-sm w-[calc(100%-1.5rem)] backdrop-blur-xl shadow-2xl rounded-full p-1.5 flex items-center justify-around transition-all"
        style="background: var(--m3-surface-card, rgba(15, 23, 42, 0.92)); border: 1px solid var(--m3-border, rgba(51, 65, 85, 0.8)); box-shadow: 0 8px 32px rgba(0,0,0,0.5), 0 0 20px var(--m3-glow-subtle, transparent);"
        aria-label="Mobile Navigation Dock"
      >
        <!-- Tab 1: Status Filter Cycle Button -->
        <button
          type="button"
          @click="cycleMobileStatusFilter"
          class="flex-1 flex flex-col items-center justify-center py-1 px-1 rounded-full transition-all active:scale-95 text-[10px] font-semibold"
          :style="visitedFilter !== 'all' ? { background: 'var(--m3-badge-bg)', color: 'var(--m3-on-primary-container)' } : { color: '#94a3b8' }"
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

    <!-- Theme Palette Selector Modal -->
    <div
      v-if="isThemeMenuOpen"
      class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md pointer-events-auto"
      @click.self="isThemeMenuOpen = false"
    >
      <div
        class="w-full max-w-xs border rounded-3xl shadow-2xl p-4 space-y-3 animate-in zoom-in-95 duration-150 text-slate-100"
        style="background: var(--m3-surface-elevated, #1e293b); border-color: var(--m3-border, #475569); box-shadow: 0 20px 50px rgba(0,0,0,0.7), 0 0 30px var(--m3-glow, transparent);"
      >
        <div class="flex items-center justify-between pb-2 border-b border-slate-800">
          <div class="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-200">
            <Palette class="w-4 h-4" style="color: var(--m3-primary);" />
            <span>Theme Colors (テーマ)</span>
          </div>
          <button
            type="button"
            @click="isThemeMenuOpen = false"
            class="p-1 text-slate-400 hover:text-white rounded-full"
            aria-label="Close theme menu"
          >
            <X class="w-4 h-4" />
          </button>
        </div>

        <p class="text-[11px] text-slate-400 leading-relaxed">
          Wähle dein bevorzugtes Farbschema. Auf Android passt sich <strong>Monet</strong> automatisch deinen Wallpaper-Farben an.
        </p>

        <!-- Dynamic Monet Status Pill -->
        <div
          class="flex items-center justify-between p-2 rounded-xl text-[11px] border"
          style="background: var(--m3-badge-bg); border-color: var(--m3-border-subtle); color: var(--m3-on-primary-container);"
        >
          <span class="flex items-center gap-1.5 font-medium">
            <span class="w-2.5 h-2.5 rounded-full" :style="{ backgroundColor: activeThemeHex }" />
            Aktives Farbschema:
          </span>
          <span class="font-mono font-bold uppercase px-1.5 py-0.5 rounded text-[10px]" style="background: rgba(0,0,0,0.35);">
            {{ activeThemeHex }}
          </span>
        </div>

        <div class="space-y-1.5 max-h-[50vh] overflow-y-auto pr-1">
          <button
            v-for="p in PRESET_PALETTES"
            :key="p.id"
            type="button"
            @click="selectPalette(p.id)"
            class="w-full flex items-center justify-between p-2.5 rounded-2xl border text-xs font-semibold transition-all active:scale-95 text-left"
            :style="currentPaletteId === p.id
              ? { background: 'var(--m3-primary)', color: 'white', borderColor: 'transparent', boxShadow: '0 4px 14px var(--m3-glow)' }
              : { background: 'rgba(15, 23, 42, 0.6)', color: '#cbd5e1', borderColor: 'var(--m3-border-subtle)' }"
          >
            <div class="flex items-center gap-2.5">
              <span
                class="w-5 h-5 rounded-full border border-white/20 shadow-xs flex items-center justify-center text-[10px] flex-shrink-0"
                :style="{ backgroundColor: p.id === 'monet' ? detectedMonetColor : p.seedHex }"
              />
              <span class="truncate">
                {{ p.id === 'monet' ? `📱 System Monet (${detectedMonetColor.toUpperCase()})` : p.label }}
              </span>
            </div>
            <span v-if="currentPaletteId === p.id" class="text-xs text-white font-bold ml-1">✓</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Desktop Fullscreen Stamp Image Lightbox Modal -->
    <div
      v-if="isImageModalOpen && selectedStamp?.imageUrl"
      class="fixed inset-0 z-[110] flex items-center justify-center p-4 bg-slate-950/85 backdrop-blur-md animate-in fade-in duration-200 pointer-events-auto"
      @click="isImageModalOpen = false"
    >
      <div
        class="relative max-w-lg w-full bg-stone-50 rounded-3xl p-6 shadow-2xl border-4 border-stone-200 flex flex-col items-center gap-4 animate-in zoom-in-95 duration-200 text-stone-900"
        @click.stop
      >
        <button
          type="button"
          @click="isImageModalOpen = false"
          class="absolute top-3 right-3 p-2 text-stone-500 hover:text-stone-900 bg-stone-200/80 hover:bg-stone-300 rounded-full transition-colors"
          aria-label="Close image lightbox"
        >
          <X class="w-5 h-5" />
        </button>

        <div class="text-center">
          <div class="text-[10px] uppercase tracking-widest font-bold text-stone-500">
            {{ selectedStampCategoryInfo?.label }} ({{ selectedStampCategoryInfo?.labelJa }})
          </div>
          <h3 class="text-xl font-bold text-stone-900 mt-0.5">{{ selectedStamp.name }}</h3>
          <p class="text-sm font-serif text-stone-600">{{ selectedStamp.name_ja }}</p>
        </div>

        <div class="w-72 h-72 sm:w-80 sm:h-80 bg-white rounded-2xl p-4 shadow-inner border border-stone-200 flex items-center justify-center overflow-hidden">
          <img
            :src="selectedStamp.imageUrl"
            :alt="selectedStamp.name"
            class="max-w-full max-h-full object-contain filter drop-shadow-sm select-none transition-transform hover:scale-125 duration-300 cursor-zoom-in"
            title="Inspect stamp in detail"
          />
        </div>

        <div class="text-center text-xs text-stone-500 max-w-xs">
          {{ selectedStamp.stampLocation }}
        </div>
      </div>
    </div>

    <!-- Stamp Source & Registry Modal for Desktop Sidebar trigger -->
    <StampSourceModal
      v-if="selectedStamp"
      :is-open="isSourceModalOpen"
      :stamp="selectedStamp"
      @close="isSourceModalOpen = false"
    />
  </header>
</template>
