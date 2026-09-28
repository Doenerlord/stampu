<script setup lang="ts">
import { ref, computed } from 'vue';
import {
  X,
  Navigation,
  Compass,
  MapPin,
  CheckCircle2,
  CircleDot,
  Star,
  ExternalLink,
  LocateFixed,
  Search,
} from 'lucide-vue-next';
import type { Stamp, StampCategory } from '../types/stamp';
import { CATEGORIES, ALL_CATEGORIES } from '../constants/categories';
import { calculateDistanceKm, formatDistance, openInGoogleMaps } from '../utils/geo';

const props = defineProps<{
  isOpen: boolean;
  stamps: Stamp[];
  visitedStampIds: Set<string>;
  wishlistStampIds?: Set<string>;
  userLocation: { lat: number; lng: number } | null;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'selectStamp', stamp: Stamp): void;
  (e: 'toggleCollected', stampId: string): void;
  (e: 'toggleWishlist', stampId: string): void;
  (e: 'requestLocation'): void;
}>();

const selectedRadiusKm = ref<number | 'all'>('all');
const filterUncollectedOnly = ref<boolean>(false);
const selectedCategory = ref<StampCategory | 'all'>('all');
const searchQuery = ref<string>('');

// Quick hubs if user wants to check a hub station
const PRESET_HUBS = [
  { name: 'Tokyo Station (東京駅)', lat: 35.6812, lng: 139.7671 },
  { name: 'Kyoto Station (京都駅)', lat: 34.9858, lng: 135.7588 },
  { name: 'Osaka / Umeda (大阪駅)', lat: 34.7024, lng: 135.4959 },
  { name: 'Fukuoka / Hakata (博多駅)', lat: 33.5904, lng: 130.4207 },
  { name: 'Sapporo (札幌駅)', lat: 43.0686, lng: 141.3508 },
];

const activeCoords = ref<{ lat: number; lng: number } | null>(null);

// Sync with props or preset
const effectiveCoords = computed(() => {
  if (activeCoords.value) return activeCoords.value;
  if (props.userLocation) return props.userLocation;
  return null;
});

function setPresetHub(hub: { lat: number; lng: number }) {
  activeCoords.value = { lat: hub.lat, lng: hub.lng };
}

function handleGetDeviceLocation() {
  activeCoords.value = null;
  emit('requestLocation');
}

// Compute distance to all stamps and sort
const nearbyStampsWithDistance = computed(() => {
  const coords = effectiveCoords.value;
  if (!coords) return [];

  const list = props.stamps.map((stamp) => {
    const distKm = calculateDistanceKm(
      coords.lat,
      coords.lng,
      stamp.coordinates[1],
      stamp.coordinates[0]
    );
    return {
      stamp,
      distanceKm: distKm,
      formattedDistance: formatDistance(distKm),
    };
  });

  // Sort ascending by distance
  list.sort((a, b) => a.distanceKm - b.distanceKm);

  // Apply filters
  let filtered = list;

  if (selectedRadiusKm.value !== 'all') {
    const maxDist = selectedRadiusKm.value;
    filtered = filtered.filter((item) => item.distanceKm <= maxDist);
  }

  if (filterUncollectedOnly.value) {
    filtered = filtered.filter((item) => !props.visitedStampIds.has(item.stamp.id));
  }

  if (selectedCategory.value !== 'all') {
    filtered = filtered.filter((item) => item.stamp.category === selectedCategory.value);
  }

  if (searchQuery.value.trim()) {
    const q = searchQuery.value.trim().toLowerCase();
    filtered = filtered.filter(
      (item) =>
        item.stamp.name.toLowerCase().includes(q) ||
        item.stamp.name_ja.includes(q) ||
        item.stamp.city.toLowerCase().includes(q) ||
        item.stamp.stampLocation.toLowerCase().includes(q)
    );
  }

  return filtered.slice(0, 100); // Top 100 nearest
});

function handleStampClick(stamp: Stamp) {
  emit('selectStamp', stamp);
}
</script>

<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition-opacity duration-200 ease-out"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition-opacity duration-150 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="isOpen"
        class="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-slate-950/80 backdrop-blur-md overflow-hidden"
        role="dialog"
        aria-modal="true"
        aria-labelledby="nearby-modal-title"
        @click.self="$emit('close')"
      >
        <div
          class="relative w-full max-w-2xl max-h-[90vh] bg-slate-900 border border-slate-700/80 rounded-3xl shadow-2xl flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200"
        >
          <!-- Modal Header -->
          <div class="px-5 py-4 bg-slate-800/90 border-b border-slate-700/80 flex items-center justify-between">
            <div class="flex items-center gap-2.5">
              <div class="w-8 h-8 rounded-xl bg-gradient-to-tr from-rose-600 to-amber-500 flex items-center justify-center text-white shadow-md">
                <Navigation class="w-4 h-4 fill-white" />
              </div>
              <div>
                <h3 id="nearby-modal-title" class="font-bold text-base sm:text-lg text-white leading-tight flex items-center gap-2">
                  Nearby Stamp Radar
                  <span class="text-[10px] font-normal px-1.5 py-0.2 rounded bg-rose-950 text-rose-300 border border-rose-800/50">周辺スタンプ</span>
                </h3>
                <p class="text-xs text-slate-400">
                  Discover collectible stamps closest to your current location
                </p>
              </div>
            </div>

            <button
              type="button"
              @click="$emit('close')"
              class="p-2 text-slate-400 hover:text-white hover:bg-slate-700/60 rounded-full transition-colors"
              title="Close modal"
              aria-label="Close modal"
            >
              <X class="w-5 h-5" />
            </button>
          </div>

          <!-- Controls & Location Bar -->
          <div class="p-4 bg-slate-950/50 border-b border-slate-800 space-y-3">
            <!-- Location Status / Request Row -->
            <div class="flex flex-wrap items-center justify-between gap-2 text-xs">
              <div class="flex items-center gap-2">
                <LocateFixed :class="['w-4 h-4', effectiveCoords ? 'text-emerald-400' : 'text-slate-400']" />
                <span v-if="effectiveCoords" class="text-slate-300 font-medium">
                  GPS Active: <strong class="text-emerald-400">{{ effectiveCoords.lat.toFixed(4) }}, {{ effectiveCoords.lng.toFixed(4) }}</strong>
                </span>
                <span v-else class="text-amber-400 font-medium">
                  Location not yet detected. Tap below to find nearby stamps:
                </span>
              </div>

              <button
                type="button"
                @click="handleGetDeviceLocation"
                class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold transition-all active:scale-95 shadow-sm"
              >
                <LocateFixed class="w-3.5 h-3.5" />
                <span>{{ effectiveCoords ? 'Refresh My GPS' : 'Acquire My GPS Location' }}</span>
              </button>
            </div>

            <!-- Quick Preset Hubs (if user is planning from abroad or GPS off) -->
            <div v-if="!effectiveCoords" class="pt-1">
              <div class="text-[11px] text-slate-400 mb-1.5 font-medium">Or simulate location near a major hub:</div>
              <div class="flex flex-wrap items-center gap-1.5">
                <button
                  v-for="hub in PRESET_HUBS"
                  :key="hub.name"
                  type="button"
                  @click="setPresetHub(hub)"
                  class="px-2.5 py-1 text-[11px] rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 transition-colors"
                >
                  {{ hub.name }}
                </button>
              </div>
            </div>

            <!-- Filter Controls Bar -->
            <div v-if="effectiveCoords" class="space-y-2.5 pt-1">
              <!-- Search & Distance Radii -->
              <div class="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
                <!-- Search input -->
                <div class="relative flex-1">
                  <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400 pointer-events-none" />
                  <input
                    type="text"
                    v-model="searchQuery"
                    placeholder="Search nearby stations, castles, shrines..."
                    class="w-full bg-slate-800/80 text-slate-100 placeholder-slate-400 text-xs pl-8 pr-3 py-1.5 rounded-xl border border-slate-700 focus:outline-none focus:border-rose-500"
                  />
                </div>

                <!-- Distance Range Pills -->
                <div class="flex items-center gap-1 bg-slate-800/80 p-0.5 rounded-xl border border-slate-700 text-[11px] overflow-x-auto no-scrollbar">
                  <button
                    type="button"
                    @click="selectedRadiusKm = 'all'"
                    :class="['px-2.5 py-1 rounded-lg font-medium transition-colors', selectedRadiusKm === 'all' ? 'bg-slate-700 text-white font-bold' : 'text-slate-400 hover:text-white']"
                  >
                    All Nearest
                  </button>
                  <button
                    type="button"
                    @click="selectedRadiusKm = 1"
                    :class="['px-2 py-1 rounded-lg font-medium transition-colors', selectedRadiusKm === 1 ? 'bg-rose-600 text-white font-bold' : 'text-slate-400 hover:text-white']"
                  >
                    &lt; 1 km
                  </button>
                  <button
                    type="button"
                    @click="selectedRadiusKm = 5"
                    :class="['px-2 py-1 rounded-lg font-medium transition-colors', selectedRadiusKm === 5 ? 'bg-rose-600 text-white font-bold' : 'text-slate-400 hover:text-white']"
                  >
                    &lt; 5 km
                  </button>
                  <button
                    type="button"
                    @click="selectedRadiusKm = 25"
                    :class="['px-2 py-1 rounded-lg font-medium transition-colors', selectedRadiusKm === 25 ? 'bg-rose-600 text-white font-bold' : 'text-slate-400 hover:text-white']"
                  >
                    &lt; 25 km
                  </button>
                </div>
              </div>

              <!-- Uncollected Toggle & Category Filter -->
              <div class="flex items-center justify-between gap-2 overflow-x-auto no-scrollbar text-xs">
                <!-- Uncollected Toggle -->
                <button
                  type="button"
                  @click="filterUncollectedOnly = !filterUncollectedOnly"
                  :class="[
                    'flex-shrink-0 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-xl text-xs font-semibold border transition-all active:scale-95',
                    filterUncollectedOnly
                      ? 'bg-emerald-600 border-emerald-500 text-white shadow-xs'
                      : 'bg-slate-800/80 border-slate-700 text-slate-300 hover:text-white'
                  ]"
                >
                  <component :is="filterUncollectedOnly ? CheckCircle2 : CircleDot" class="w-3.5 h-3.5" />
                  <span>To Find Only (Uncollected)</span>
                </button>

                <!-- Category Chips -->
                <div class="flex items-center gap-1 overflow-x-auto no-scrollbar">
                  <button
                    type="button"
                    @click="selectedCategory = 'all'"
                    :class="['px-2 py-1 rounded-lg text-[11px] font-medium transition-colors', selectedCategory === 'all' ? 'bg-slate-700 text-white font-bold' : 'text-slate-400 hover:text-white']"
                  >
                    All Types
                  </button>
                  <button
                    v-for="cat in ALL_CATEGORIES"
                    :key="cat.id"
                    type="button"
                    @click="selectedCategory = cat.id"
                    :class="[
                      'px-2 py-1 rounded-lg text-[11px] font-medium whitespace-nowrap transition-colors',
                      selectedCategory === cat.id ? cat.activeClass : 'text-slate-400 hover:text-white'
                    ]"
                  >
                    {{ cat.label }}
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- Nearby Stamps Scrollable List -->
          <div class="flex-1 overflow-y-auto p-4 space-y-2.5">
            <!-- Empty state if no location -->
            <div v-if="!effectiveCoords" class="p-8 text-center text-slate-400 space-y-3">
              <Compass class="w-12 h-12 text-slate-600 mx-auto" />
              <p class="text-sm font-medium">Please activate GPS or pick a preset station above to calculate nearby stamps.</p>
            </div>

            <!-- Empty state if no stamps found in radius -->
            <div v-else-if="nearbyStampsWithDistance.length === 0" class="p-8 text-center text-slate-400 space-y-3">
              <MapPin class="w-12 h-12 text-slate-600 mx-auto" />
              <p class="text-sm font-medium">No stamps found matching your current filter radius.</p>
              <button
                type="button"
                @click="selectedRadiusKm = 'all'; filterUncollectedOnly = false; selectedCategory = 'all'"
                class="px-3 py-1.5 rounded-xl bg-slate-800 text-xs text-rose-300 font-semibold"
              >
                Reset Distance Filters
              </button>
            </div>

            <!-- Stamp Cards -->
            <div
              v-else
              v-for="item in nearbyStampsWithDistance"
              :key="item.stamp.id"
              class="group bg-slate-800/60 hover:bg-slate-800 rounded-2xl p-3 border border-slate-700/60 hover:border-slate-600 transition-all flex items-center justify-between gap-3 shadow-md"
            >
              <!-- Left: Thumbnail & Details -->
              <div class="flex items-center gap-3 min-w-0 flex-1 cursor-pointer" @click="handleStampClick(item.stamp)">
                <!-- Stamp Photo Thumbnail -->
                <div class="w-14 h-14 flex-shrink-0 bg-white rounded-xl p-1 shadow border border-slate-700 flex items-center justify-center overflow-hidden">
                  <img
                    v-if="item.stamp.imageUrl"
                    :src="item.stamp.imageUrl"
                    :alt="item.stamp.name"
                    class="w-full h-full object-contain"
                    loading="lazy"
                  />
                  <div v-else class="text-[9px] font-bold text-slate-800 font-serif">印</div>
                </div>

                <!-- Info -->
                <div class="min-w-0 flex-1">
                  <!-- Badges & Distance Row -->
                  <div class="flex items-center gap-2 mb-0.5">
                    <span class="inline-flex items-center gap-1 text-[10px] font-extrabold px-2 py-0.5 rounded-md bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                      <Navigation class="w-2.5 h-2.5 fill-emerald-400" />
                      {{ item.formattedDistance }}
                    </span>

                    <span
                      v-if="CATEGORIES[item.stamp.category]"
                      :class="['text-[9px] px-1.5 py-0.2 rounded font-semibold border', CATEGORIES[item.stamp.category].badgeClass]"
                    >
                      {{ CATEGORIES[item.stamp.category].label }}
                    </span>

                    <span
                      v-if="props.visitedStampIds.has(item.stamp.id)"
                      class="text-[9px] font-bold text-emerald-400 flex items-center gap-0.5"
                    >
                      <CheckCircle2 class="w-3 h-3" />
                      <span>Collected</span>
                    </span>
                  </div>

                  <!-- Names -->
                  <div class="text-sm font-bold text-white leading-tight truncate group-hover:text-rose-300 transition-colors">
                    {{ item.stamp.name }}
                  </div>
                  <div class="text-xs text-slate-400 font-serif truncate">
                    {{ item.stamp.name_ja }}
                  </div>

                  <!-- Location Snippet -->
                  <div class="text-[11px] text-amber-200/90 truncate mt-1">
                    {{ item.stamp.stampLocation }}
                  </div>
                </div>
              </div>

              <!-- Right Actions: Navigation & Wishlist -->
              <div class="flex items-center gap-1 flex-shrink-0">
                <!-- Google Maps Routing Button -->
                <button
                  type="button"
                  @click.stop="openInGoogleMaps(item.stamp.coordinates[1], item.stamp.coordinates[0], item.stamp.name)"
                  class="p-2 rounded-xl bg-blue-600/20 hover:bg-blue-600/30 text-blue-300 border border-blue-500/40 transition-colors shadow-xs"
                  title="Route with Google Maps"
                  aria-label="Route with Google Maps"
                >
                  <ExternalLink class="w-4 h-4" />
                </button>

                <!-- Wishlist Toggle -->
                <button
                  type="button"
                  @click.stop="$emit('toggleWishlist', item.stamp.id)"
                  :class="[
                    'p-2 rounded-xl border transition-colors',
                    props.wishlistStampIds?.has(item.stamp.id)
                      ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                      : 'bg-slate-700/40 hover:bg-slate-700 text-slate-400 hover:text-amber-300 border-slate-600/50'
                  ]"
                  title="Toggle wishlist"
                  aria-label="Toggle wishlist"
                >
                  <Star :class="['w-4 h-4', props.wishlistStampIds?.has(item.stamp.id) ? 'fill-amber-400 text-amber-400' : '']" />
                </button>
              </div>
            </div>
          </div>

          <!-- Modal Footer -->
          <div class="px-5 py-3 bg-slate-950/90 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
            <div>
              Showing up to <strong class="text-white">{{ nearbyStampsWithDistance.length }}</strong> nearest locations
            </div>
            <button
              type="button"
              @click="$emit('close')"
              class="px-4 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-medium transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.no-scrollbar::-webkit-scrollbar {
  display: none;
}
.no-scrollbar {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
</style>
