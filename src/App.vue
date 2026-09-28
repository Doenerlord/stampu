<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue';
import type { Stamp, StampCategory, PrefecturePack } from './types/stamp';
import {
  getVisitedStampIds,
  toggleVisitedStamp,
  getWishlistStampIds,
  toggleWishlistStamp,
  getDownloadedPackIds,
} from './db';
import MapContainer from './components/MapContainer.vue';
import CategoryFilters from './components/CategoryFilters.vue';
import StampDrawer from './components/StampDrawer.vue';
import WishlistModal from './components/WishlistModal.vue';
import PrefectureDownloadModal from './components/PrefectureDownloadModal.vue';

const allStamps = ref<Stamp[]>([]);
const prefectures = ref<PrefecturePack[]>([]);
const selectedCategory = ref<StampCategory | 'all'>('all');
const visitedFilter = ref<'all' | 'visited' | 'unvisited' | 'wishlist'>('all');
const searchQuery = ref<string>('');
const selectedStamp = ref<Stamp | null>(null);
const isDrawerOpen = ref<boolean>(false);
const isWishlistModalOpen = ref<boolean>(false);
const isPacksModalOpen = ref<boolean>(false);
const visitedStampIds = ref<Set<string>>(new Set());
const wishlistStampIds = ref<Set<string>>(new Set());
const downloadedPacksCount = ref<number>(0);
const mapContainerRef = ref<InstanceType<typeof MapContainer> | null>(null);

// Load stamps & prefectures from public data and visited & wishlist stamps from Dexie
onMounted(async () => {
  try {
    const [stampsRes, prefsRes] = await Promise.all([
      fetch('/data/stamps.json'),
      fetch('/data/prefectures.json'),
    ]);
    if (stampsRes.ok) {
      allStamps.value = await stampsRes.json();
    }
    if (prefsRes.ok) {
      prefectures.value = await prefsRes.json();
    }
  } catch (err) {
    console.error('Error fetching stamps or prefectures catalog:', err);
  }

  // Load visited, wishlist & offline packs from Dexie
  const [visited, wishlist, downloaded] = await Promise.all([
    getVisitedStampIds(),
    getWishlistStampIds(),
    getDownloadedPackIds(),
  ]);
  visitedStampIds.value = visited;
  wishlistStampIds.value = wishlist;
  downloadedPacksCount.value = downloaded.size;
});

// Category counts for badges
const categoryCounts = computed(() => {
  const counts: Record<string, number> = {
    all: allStamps.value.length,
    eki: 0,
    michinoeki: 0,
    highway: 0,
    castle: 0,
    temple_shrine: 0,
    tower: 0,
  };

  for (const s of allStamps.value) {
    if (counts[s.category] !== undefined) {
      counts[s.category]++;
    }
  }
  return counts;
});

// Wishlist stamps array for modal
const wishlistStamps = computed(() => {
  return allStamps.value.filter((stamp) => wishlistStampIds.value.has(stamp.id));
});

// Filtered stamps passed to map
const filteredStamps = computed(() => {
  const query = searchQuery.value.trim().toLowerCase();

  return allStamps.value.filter((stamp) => {
    // 1. Category check
    if (selectedCategory.value !== 'all' && stamp.category !== selectedCategory.value) {
      return false;
    }

    // 2. Status filter check
    const isVisited = visitedStampIds.value.has(stamp.id);
    const isWishlist = wishlistStampIds.value.has(stamp.id);

    if (visitedFilter.value === 'visited' && !isVisited) {
      return false;
    }
    if (visitedFilter.value === 'unvisited' && isVisited) {
      return false;
    }
    if (visitedFilter.value === 'wishlist' && !isWishlist) {
      return false;
    }

    // 3. Search query check
    if (query) {
      const matchName = stamp.name.toLowerCase().includes(query);
      const matchJa = stamp.name_ja.includes(query);
      const matchRomaji = stamp.name_romaji.toLowerCase().includes(query);
      const matchPref = stamp.prefecture.toLowerCase().includes(query);
      const matchCity = stamp.city.toLowerCase().includes(query);
      const matchDesc = stamp.description.toLowerCase().includes(query);
      if (!matchName && !matchJa && !matchRomaji && !matchPref && !matchCity && !matchDesc) {
        return false;
      }
    }

    return true;
  });
});

function handleSelectStamp(stamp: Stamp) {
  selectedStamp.value = stamp;
  isDrawerOpen.value = true;
}

function handleSelectStampFromWishlist(stamp: Stamp) {
  isWishlistModalOpen.value = false;
  selectedStamp.value = stamp;
  isDrawerOpen.value = true;
  handleFocusMap(stamp.coordinates);
}

function handleCloseDrawer() {
  isDrawerOpen.value = false;
  // Keep selectedStamp for smooth exit animation, then clean up
  setTimeout(() => {
    if (!isDrawerOpen.value) {
      selectedStamp.value = null;
    }
  }, 300);
}

async function handleToggleCollected(stampId: string) {
  await toggleVisitedStamp(stampId);
  visitedStampIds.value = await getVisitedStampIds();
}

async function handleToggleWishlist(stampId: string) {
  await toggleWishlistStamp(stampId);
  wishlistStampIds.value = await getWishlistStampIds();
}

function handleFocusMap(coordinates: [number, number]) {
  mapContainerRef.value?.focusCoordinates(coordinates, 13);
}

function handleFitWishlistOnMap() {
  isWishlistModalOpen.value = false;
  visitedFilter.value = 'wishlist';
  nextTick(() => {
    mapContainerRef.value?.fitAllStamps();
  });
}

async function handleClosePacksModal() {
  isPacksModalOpen.value = false;
  const downloaded = await getDownloadedPackIds();
  downloadedPacksCount.value = downloaded.size;
}
</script>

<template>
  <div class="relative w-screen h-screen overflow-hidden bg-slate-950 font-sans">
    <!-- Map Canvas (Full screen background) -->
    <MapContainer
      ref="mapContainerRef"
      :stamps="filteredStamps"
      :selected-stamp="selectedStamp"
      :visited-stamp-ids="visitedStampIds"
      :wishlist-stamp-ids="wishlistStampIds"
      @select-stamp="handleSelectStamp"
    />

    <!-- Top Status Bar Scrim for contrast -->
    <div class="absolute top-0 left-0 right-0 h-14 bg-gradient-to-b from-slate-950/90 via-slate-950/40 to-transparent pointer-events-none z-20" />

    <!-- Floating Top Header & Filter Controls -->
    <div class="absolute top-0 left-0 right-0 z-30 pointer-events-none">
      <CategoryFilters
        v-model:selected-category="selectedCategory"
        v-model:visited-filter="visitedFilter"
        v-model:search-query="searchQuery"
        :category-counts="categoryCounts"
        :visited-count="visitedStampIds.size"
        :wishlist-count="wishlistStampIds.size"
        :total-count="allStamps.length"
        :downloaded-packs-count="downloadedPacksCount"
        @open-wishlist-modal="isWishlistModalOpen = true"
        @open-packs-modal="isPacksModalOpen = true"
      />
    </div>

    <!-- Stamp Detail Drawer (Bottom Sheet) -->
    <StampDrawer
      :stamp="selectedStamp"
      :is-open="isDrawerOpen"
      :is-collected="selectedStamp ? visitedStampIds.has(selectedStamp.id) : false"
      :is-wishlist="selectedStamp ? wishlistStampIds.has(selectedStamp.id) : false"
      @close="handleCloseDrawer"
      @toggle-collected="handleToggleCollected"
      @toggle-wishlist="handleToggleWishlist"
      @focus-map="handleFocusMap"
    />

    <!-- Wishlist Modal -->
    <WishlistModal
      :is-open="isWishlistModalOpen"
      :wishlist-stamps="wishlistStamps"
      :visited-stamp-ids="visitedStampIds"
      @close="isWishlistModalOpen = false"
      @select-stamp="handleSelectStampFromWishlist"
      @toggle-wishlist="handleToggleWishlist"
      @toggle-collected="handleToggleCollected"
      @fit-wishlist-on-map="handleFitWishlistOnMap"
    />

    <!-- Prefecture Offline Packs Download Modal -->
    <PrefectureDownloadModal
      :is-open="isPacksModalOpen"
      :prefectures="prefectures"
      :stamps="allStamps"
      @close="handleClosePacksModal"
    />
  </div>
</template>
