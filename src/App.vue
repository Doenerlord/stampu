<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import type { Stamp, StampCategory } from './types/stamp';
import { getVisitedStampIds, toggleVisitedStamp } from './db';
import MapContainer from './components/MapContainer.vue';
import CategoryFilters from './components/CategoryFilters.vue';
import StampDrawer from './components/StampDrawer.vue';

const allStamps = ref<Stamp[]>([]);
const selectedCategory = ref<StampCategory | 'all'>('all');
const visitedFilter = ref<'all' | 'visited' | 'unvisited'>('all');
const searchQuery = ref<string>('');
const selectedStamp = ref<Stamp | null>(null);
const isDrawerOpen = ref<boolean>(false);
const visitedStampIds = ref<Set<string>>(new Set());
const mapContainerRef = ref<InstanceType<typeof MapContainer> | null>(null);

// Load stamps from public data and visited stamps from Dexie
onMounted(async () => {
  try {
    const res = await fetch('/data/stamps.json');
    if (res.ok) {
      allStamps.value = await res.json();
    } else {
      console.error('Failed to load stamps.json:', res.statusText);
    }
  } catch (err) {
    console.error('Error fetching stamps.json:', err);
  }

  // Load visited from Dexie
  visitedStampIds.value = await getVisitedStampIds();
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
  };

  for (const s of allStamps.value) {
    if (counts[s.category] !== undefined) {
      counts[s.category]++;
    }
  }
  return counts;
});

// Filtered stamps passed to map
const filteredStamps = computed(() => {
  const query = searchQuery.value.trim().toLowerCase();

  return allStamps.value.filter((stamp) => {
    // 1. Category check
    if (selectedCategory.value !== 'all' && stamp.category !== selectedCategory.value) {
      return false;
    }

    // 2. Visited filter check
    const isVisited = visitedStampIds.value.has(stamp.id);
    if (visitedFilter.value === 'visited' && !isVisited) {
      return false;
    }
    if (visitedFilter.value === 'unvisited' && isVisited) {
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

function handleFocusMap(coordinates: [number, number]) {
  mapContainerRef.value?.focusCoordinates(coordinates, 13);
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
      @select-stamp="handleSelectStamp"
    />

    <!-- Floating Top Header & Filter Controls -->
    <div class="absolute top-0 left-0 right-0 z-30 pointer-events-none">
      <CategoryFilters
        v-model:selected-category="selectedCategory"
        v-model:visited-filter="visitedFilter"
        v-model:search-query="searchQuery"
        :category-counts="categoryCounts"
        :visited-count="visitedStampIds.size"
        :total-count="allStamps.length"
      />
    </div>

    <!-- Stamp Detail Drawer (Bottom Sheet) -->
    <StampDrawer
      :stamp="selectedStamp"
      :is-open="isDrawerOpen"
      :is-collected="selectedStamp ? visitedStampIds.has(selectedStamp.id) : false"
      @close="handleCloseDrawer"
      @toggle-collected="handleToggleCollected"
      @focus-map="handleFocusMap"
    />
  </div>
</template>
