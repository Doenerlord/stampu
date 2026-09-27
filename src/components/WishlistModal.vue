<script setup lang="ts">
import { computed } from 'vue';
import type { Stamp } from '../types/stamp';
import { CATEGORIES } from '../constants/categories';
import {
  Star,
  X,
  MapPin,
  Compass,
  CheckCircle2,
  Trash2,
  ExternalLink,
} from 'lucide-vue-next';

const props = defineProps<{
  isOpen: boolean;
  wishlistStamps: Stamp[];
  visitedStampIds: Set<string>;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'selectStamp', stamp: Stamp): void;
  (e: 'toggleWishlist', stampId: string): void;
  (e: 'toggleCollected', stampId: string): void;
  (e: 'fitWishlistOnMap'): void;
}>();

const sortedWishlistStamps = computed(() => {
  return [...props.wishlistStamps].sort((a, b) => {
    // Uncollected first, then by prefecture and name
    const aCollected = props.visitedStampIds.has(a.id);
    const bCollected = props.visitedStampIds.has(b.id);
    if (aCollected !== bCollected) return aCollected ? 1 : -1;
    return a.prefecture.localeCompare(b.prefecture) || a.name.localeCompare(b.name);
  });
});
</script>

<template>
  <div
    v-if="isOpen"
    class="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200"
    role="dialog"
    aria-modal="true"
    aria-labelledby="wishlist-modal-title"
  >
    <div
      class="relative w-full max-w-lg max-h-[85vh] flex flex-col bg-slate-900 border border-slate-700/80 rounded-3xl shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200 text-slate-100"
      @click.stop
    >
      <!-- Header -->
      <div class="flex items-center justify-between px-5 py-4 border-b border-slate-800 bg-slate-900/90">
        <div class="flex items-center gap-2.5">
          <div class="w-9 h-9 rounded-xl bg-amber-500/20 border border-amber-500/40 flex items-center justify-center text-amber-400">
            <Star class="w-5 h-5 fill-amber-400" />
          </div>
          <div>
            <h2 id="wishlist-modal-title" class="text-lg font-bold text-white leading-tight flex items-center gap-2">
              <span>Stamp Wishlist</span>
              <span class="text-xs px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30 font-semibold">
                {{ wishlistStamps.length }}
              </span>
            </h2>
            <p class="text-xs text-slate-400">Stamps you want to collect on your journey</p>
          </div>
        </div>

        <button
          type="button"
          @click="$emit('close')"
          class="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-full transition-colors"
          aria-label="Close wishlist modal"
        >
          <X class="w-5 h-5" />
        </button>
      </div>

      <!-- Action Sub-header (when items exist) -->
      <div
        v-if="wishlistStamps.length > 0"
        class="px-5 py-2.5 bg-slate-850/90 border-b border-slate-800 flex items-center justify-between text-xs"
      >
        <span class="text-slate-400">
          <strong class="text-amber-400">{{ wishlistStamps.length }}</strong> target stamps saved
        </span>
        <button
          type="button"
          @click="$emit('fitWishlistOnMap')"
          class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 font-semibold border border-amber-500/40 transition-colors"
        >
          <Compass class="w-3.5 h-3.5" />
          <span>Show All on Map</span>
        </button>
      </div>

      <!-- Scrollable List -->
      <div class="flex-1 overflow-y-auto p-4 space-y-3">
        <!-- Empty State -->
        <div
          v-if="wishlistStamps.length === 0"
          class="py-12 px-6 flex flex-col items-center justify-center text-center space-y-3"
        >
          <div class="w-16 h-16 rounded-2xl bg-slate-800 border border-slate-700/80 flex items-center justify-center text-slate-500">
            <Star class="w-8 h-8" />
          </div>
          <h3 class="text-base font-semibold text-slate-200">No stamps on your wishlist yet</h3>
          <p class="text-xs text-slate-400 max-w-xs leading-relaxed">
            Browse the map or search for stations, castles, and shrines. Tap the star icon (★) in any stamp's drawer to bookmark it for your itinerary!
          </p>
        </div>

        <!-- Stamp Cards -->
        <div
          v-for="stamp in sortedWishlistStamps"
          :key="stamp.id"
          class="bg-slate-800/70 hover:bg-slate-800 border border-slate-700/70 hover:border-slate-600 rounded-2xl p-3.5 transition-all flex items-start gap-3.5 group"
        >
          <!-- Stamp Artwork Thumbnail -->
          <div
            class="relative flex-shrink-0 w-16 h-16 rounded-xl bg-stone-100 p-1 border border-stone-300 flex items-center justify-center overflow-hidden cursor-pointer"
            @click="$emit('selectStamp', stamp)"
            title="View details"
          >
            <img
              v-if="stamp.imageUrl"
              :src="stamp.imageUrl"
              :alt="stamp.name"
              class="w-full h-full object-contain"
              loading="lazy"
            />
            <div v-else class="text-[10px] font-bold text-slate-600 font-serif">
              {{ stamp.name_ja.slice(0, 2) }}
            </div>

            <!-- Collected Badge overlay -->
            <div
              v-if="visitedStampIds.has(stamp.id)"
              class="absolute inset-0 bg-emerald-950/60 flex items-center justify-center"
            >
              <CheckCircle2 class="w-6 h-6 text-emerald-400 drop-shadow" />
            </div>
          </div>

          <!-- Stamp Info -->
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-1.5 flex-wrap">
              <span
                :class="[
                  'text-[10px] px-1.5 py-0.2 rounded font-semibold border',
                  CATEGORIES[stamp.category]?.badgeClass || 'bg-slate-700 text-slate-300'
                ]"
              >
                {{ CATEGORIES[stamp.category]?.label || stamp.category }}
              </span>
              <span class="text-xs text-slate-400 font-serif">{{ stamp.name_ja }}</span>
              <span
                v-if="visitedStampIds.has(stamp.id)"
                class="text-[10px] text-emerald-400 font-semibold bg-emerald-950/50 px-1.5 py-0.2 rounded border border-emerald-800/40"
              >
                ✓ Collected
              </span>
            </div>

            <h4
              class="text-sm font-bold text-white truncate mt-0.5 cursor-pointer hover:text-amber-300 transition-colors"
              @click="$emit('selectStamp', stamp)"
            >
              {{ stamp.name }}
            </h4>

            <div class="flex items-center gap-1 text-[11px] text-slate-400 mt-1 truncate">
              <MapPin class="w-3 h-3 text-slate-500 flex-shrink-0" />
              <span class="truncate">{{ stamp.prefecture }} • {{ stamp.stampLocation }}</span>
            </div>

            <!-- Card Actions -->
            <div class="flex items-center gap-2 mt-2.5">
              <button
                type="button"
                @click="$emit('selectStamp', stamp)"
                class="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-700/70 hover:bg-slate-700 text-xs text-slate-200 font-medium border border-slate-600/50 transition-colors"
                title="View full details and location"
              >
                <ExternalLink class="w-3 h-3" />
                <span>Details</span>
              </button>

              <button
                type="button"
                @click="$emit('toggleCollected', stamp.id)"
                :class="[
                  'inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium border transition-colors',
                  visitedStampIds.has(stamp.id)
                    ? 'bg-emerald-950/40 text-emerald-400 border-emerald-800/50 hover:bg-emerald-950/70'
                    : 'bg-slate-700/70 text-slate-300 border-slate-600/50 hover:bg-emerald-900/40 hover:text-emerald-300'
                ]"
                :title="visitedStampIds.has(stamp.id) ? 'Mark as uncollected' : 'Mark as collected'"
              >
                <CheckCircle2 class="w-3 h-3" />
                <span>{{ visitedStampIds.has(stamp.id) ? 'Collected' : 'Collect' }}</span>
              </button>

              <button
                type="button"
                @click="$emit('toggleWishlist', stamp.id)"
                class="ml-auto inline-flex items-center gap-1 p-1 text-slate-500 hover:text-rose-400 hover:bg-rose-950/30 rounded-lg transition-colors"
                title="Remove from wishlist"
                aria-label="Remove from wishlist"
              >
                <Trash2 class="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Footer -->
      <div class="p-4 bg-slate-950/90 border-t border-slate-800 flex items-center justify-end">
        <button
          type="button"
          @click="$emit('close')"
          class="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-white border border-slate-700 transition-colors"
        >
          Close
        </button>
      </div>
    </div>
  </div>
</template>
