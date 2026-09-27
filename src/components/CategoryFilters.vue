<script setup lang="ts">
import { computed } from 'vue';
import type { StampCategory } from '../types/stamp';
import { ALL_CATEGORIES } from '../constants/categories';
import {
  Train,
  Store,
  Car,
  Castle,
  Sparkles,
  Layers,
  Search,
  X,
  CheckCircle2,
  CircleDot,
  Star,
} from 'lucide-vue-next';

const props = defineProps<{
  selectedCategory: StampCategory | 'all';
  visitedFilter: 'all' | 'visited' | 'unvisited' | 'wishlist';
  searchQuery: string;
  categoryCounts: Record<string, number>;
  visitedCount: number;
  wishlistCount: number;
  totalCount: number;
}>();

const emit = defineEmits<{
  (e: 'update:selectedCategory', value: StampCategory | 'all'): void;
  (e: 'update:visitedFilter', value: 'all' | 'visited' | 'unvisited' | 'wishlist'): void;
  (e: 'update:searchQuery', value: string): void;
  (e: 'openWishlistModal'): void;
}>();

const iconMap = {
  Train,
  Store,
  Car,
  Castle,
  Sparkles,
};

const visitedPercentage = computed(() => {
  if (props.totalCount === 0) return 0;
  return Math.round((props.visitedCount / props.totalCount) * 100);
});

function selectCategory(cat: StampCategory | 'all') {
  emit('update:selectedCategory', cat);
}

function selectVisited(filter: 'all' | 'visited' | 'unvisited' | 'wishlist') {
  emit('update:visitedFilter', filter);
}

function onSearchInput(event: Event) {
  const target = event.target as HTMLInputElement;
  emit('update:searchQuery', target.value);
}

function clearSearch() {
  emit('update:searchQuery', '');
}
</script>

<template>
  <header
    class="pointer-events-auto w-full max-w-4xl mx-auto flex flex-col gap-2.5 px-3 md:px-4 transition-all"
    style="padding-top: calc(env(safe-area-inset-top, 0px) + 0.75rem);"
    role="region"
    aria-label="Filter and Search Controls"
  >
    <!-- Top Bar: Brand, Search, and Visited Progress -->
    <div
      class="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 bg-slate-900/85 backdrop-blur-md border border-slate-700/60 shadow-xl rounded-2xl p-2.5 sm:px-4"
    >
      <!-- Title, Stamp Counter & Wishlist Badge -->
      <div class="flex items-center justify-between sm:justify-start gap-2.5">
        <div class="flex items-center gap-2">
          <div
            class="w-9 h-9 rounded-xl bg-gradient-to-tr from-red-600 via-rose-500 to-amber-500 flex items-center justify-center text-white shadow-md shadow-red-900/30"
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

        <div class="flex items-center gap-2">
          <!-- Progress Pill -->
          <div
            class="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-800/90 border border-slate-700 text-xs"
            :title="`${visitedCount} of ${totalCount} collected`"
          >
            <CheckCircle2 class="w-3.5 h-3.5 text-emerald-400" />
            <span class="text-slate-300 font-medium">
              <strong class="text-emerald-400">{{ visitedCount }}</strong> / {{ totalCount }}
            </span>
            <span class="text-[10px] text-slate-400 bg-slate-700/60 px-1 rounded-sm">{{ visitedPercentage }}%</span>
          </div>

          <!-- Wishlist Modal Trigger Pill -->
          <button
            type="button"
            @click="$emit('openWishlistModal')"
            class="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-500/15 hover:bg-amber-500/25 border border-amber-500/40 text-xs text-amber-300 font-semibold transition-all active:scale-95 shadow-xs"
            title="Open Stamp Wishlist"
            aria-label="Open Stamp Wishlist"
          >
            <Star class="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
            <span class="hidden sm:inline">Wishlist</span>
            <span class="text-[10px] bg-amber-500/30 text-amber-200 px-1.5 py-0.2 rounded-full font-bold">
              {{ wishlistCount }}
            </span>
          </button>
        </div>
      </div>

      <!-- Search Input -->
      <div class="relative flex-1 min-w-[200px]">
        <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
        <input
          type="text"
          :value="searchQuery"
          @input="onSearchInput"
          placeholder="Station, Castle, City, Romaji (e.g. Kyoto, 姫路)..."
          class="w-full bg-slate-800/70 hover:bg-slate-800 focus:bg-slate-800 text-slate-100 placeholder-slate-400 text-xs sm:text-sm pl-9 pr-8 py-2 rounded-xl border border-slate-700/80 focus:border-red-500 focus:outline-none transition-colors"
        />
        <button
          v-if="searchQuery"
          @click="clearSearch"
          type="button"
          class="absolute right-2.5 top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-slate-200 transition-colors"
          title="Clear search"
          aria-label="Clear search"
        >
          <X class="w-3.5 h-3.5" />
        </button>
      </div>

      <!-- Visited Status & Wishlist Quick Toggle -->
      <div class="flex items-center gap-1 bg-slate-800/80 p-1 rounded-xl border border-slate-700/70 self-end sm:self-center overflow-x-auto no-scrollbar">
        <button
          type="button"
          @click="selectVisited('all')"
          :class="[
            'px-2.5 py-1 text-xs rounded-lg font-medium transition-all',
            visitedFilter === 'all'
              ? 'bg-slate-700 text-white shadow-sm'
              : 'text-slate-400 hover:text-slate-200'
          ]"
        >
          All
        </button>
        <button
          type="button"
          @click="selectVisited('visited')"
          :class="[
            'px-2 py-1 text-xs rounded-lg font-medium flex items-center gap-1 transition-all',
            visitedFilter === 'visited'
              ? 'bg-emerald-600 text-white shadow-sm'
              : 'text-slate-400 hover:text-emerald-300'
          ]"
          title="Show collected stamps only"
        >
          <CheckCircle2 class="w-3.5 h-3.5" />
          <span>Collected</span>
        </button>
        <button
          type="button"
          @click="selectVisited('unvisited')"
          :class="[
            'px-2 py-1 text-xs rounded-lg font-medium flex items-center gap-1 transition-all',
            visitedFilter === 'unvisited'
              ? 'bg-slate-700 text-white shadow-sm'
              : 'text-slate-400 hover:text-slate-200'
          ]"
          title="Show uncollected stamps only"
        >
          <CircleDot class="w-3.5 h-3.5" />
          <span>To Find</span>
        </button>
        <button
          type="button"
          @click="selectVisited('wishlist')"
          :class="[
            'px-2 py-1 text-xs rounded-lg font-medium flex items-center gap-1 transition-all',
            visitedFilter === 'wishlist'
              ? 'bg-amber-500 text-slate-950 font-bold shadow-sm'
              : 'text-slate-400 hover:text-amber-300'
          ]"
          title="Filter map to show wishlist target stamps"
        >
          <Star :class="['w-3.5 h-3.5', visitedFilter === 'wishlist' ? 'fill-slate-950 text-slate-950' : 'fill-amber-400 text-amber-400']" />
          <span>Wishlist</span>
          <span
            v-if="wishlistCount > 0"
            :class="[
              'text-[9px] px-1 rounded-full font-bold ml-0.5',
              visitedFilter === 'wishlist' ? 'bg-slate-950 text-amber-300' : 'bg-amber-500/30 text-amber-300'
            ]"
          >
            {{ wishlistCount }}
          </span>
        </button>
      </div>
    </div>

    <!-- Category Chips Bar (Horizontally scrollable on mobile) -->
    <div
      class="flex items-center gap-2 overflow-x-auto no-scrollbar py-0.5 scroll-smooth"
      style="-webkit-overflow-scrolling: touch;"
    >
      <!-- All Categories Chip -->
      <button
        type="button"
        @click="selectCategory('all')"
        :class="[
          'flex-shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all shadow-md',
          selectedCategory === 'all'
            ? 'bg-red-600 border-red-500 text-white shadow-red-900/40 ring-2 ring-red-400/30'
            : 'bg-slate-900/80 border-slate-700/80 text-slate-300 hover:bg-slate-800 hover:text-white'
        ]"
      >
        <Layers class="w-3.5 h-3.5" />
        <span>All Stamps</span>
        <span
          :class="[
            'ml-0.5 text-[10px] px-1.5 py-0.2 rounded-full font-bold',
            selectedCategory === 'all' ? 'bg-red-800/80 text-white' : 'bg-slate-800 text-slate-400'
          ]"
        >
          {{ categoryCounts['all'] || 0 }}
        </span>
      </button>

      <!-- Category Specific Chips -->
      <button
        v-for="cat in ALL_CATEGORIES"
        :key="cat.id"
        type="button"
        @click="selectCategory(cat.id)"
        :class="[
          'flex-shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all shadow-md',
          selectedCategory === cat.id
            ? cat.activeClass + ' ring-2 ring-white/20'
            : 'bg-slate-900/80 border-slate-700/80 text-slate-300 hover:bg-slate-800 hover:text-white'
        ]"
      >
        <component :is="iconMap[cat.iconName]" class="w-3.5 h-3.5" />
        <span>{{ cat.label }}</span>
        <span class="text-[10px] opacity-75 font-normal hidden sm:inline">({{ cat.labelJa }})</span>
        <span
          :class="[
            'ml-0.5 text-[10px] px-1.5 py-0.2 rounded-full font-bold',
            selectedCategory === cat.id ? 'bg-black/25 text-white' : 'bg-slate-800 text-slate-400'
          ]"
        >
          {{ categoryCounts[cat.id] || 0 }}
        </span>
      </button>
    </div>
  </header>
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
