<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue';
import type { Stamp } from '../types/stamp';
import { CATEGORIES } from '../constants/categories';
import {
  X,
  MapPin,
  Clock,
  Navigation,
  CheckCircle2,
  Sparkles,
  Train,
  Store,
  Car,
  Castle,
  Radio,
  Compass,
  Star,
  Languages,
  ExternalLink,
} from 'lucide-vue-next';
import AskStaffModal from './AskStaffModal.vue';
import { openInGoogleMaps } from '../utils/geo';

const props = defineProps<{
  stamp: Stamp | null;
  isOpen: boolean;
  isCollected: boolean;
  isWishlist?: boolean;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'toggleCollected', stampId: string): void;
  (e: 'toggleWishlist', stampId: string): void;
  (e: 'focusMap', coordinates: [number, number]): void;
}>();

const isImageModalOpen = ref(false);
const hasImageError = ref(false);
const isAskStaffOpen = ref(false);

watch(
  () => props.stamp,
  () => {
    isImageModalOpen.value = false;
    hasImageError.value = false;
    isAskStaffOpen.value = false;
  }
);

const iconMap = {
  Train,
  Store,
  Car,
  Castle,
  Sparkles,
  Radio,
};

const categoryInfo = computed(() => {
  if (!props.stamp) return null;
  return CATEGORIES[props.stamp.category];
});

function handleBackdropClick(event: MouseEvent) {
  if (event.target === event.currentTarget) {
    emit('close');
  }
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape' && props.isOpen) {
    emit('close');
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeydown);
});

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown);
});

watch(
  () => props.isOpen,
  (open) => {
    if (open) {
      // Prevent body scrolling when sheet is open on small mobile devices
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
  }
);
</script>

<template>
  <div
    v-if="isOpen && stamp"
    class="fixed inset-0 z-50 flex flex-col justify-end sm:items-center sm:justify-end pointer-events-auto md:hidden"
    role="dialog"
    aria-modal="true"
    aria-labelledby="stamp-title"
  >
    <!-- Scrim / Backdrop with smooth fade -->
    <div
      class="fixed inset-0 bg-black/60 backdrop-blur-xs transition-opacity duration-300"
      @click="handleBackdropClick"
      aria-hidden="true"
    />

    <!-- Material 3 Expressive Bottom Sheet Content -->
    <div
      class="relative z-10 w-full sm:max-w-xl max-h-[88dvh] flex flex-col rounded-t-[32px] sm:rounded-t-[32px] shadow-2xl overflow-hidden animate-in slide-in-from-bottom duration-300 transition-all text-slate-100"
      style="background: var(--m3-surface-elevated, #162720); border-top: 1px solid var(--m3-border, #334155); box-shadow: 0 -10px 40px rgba(0,0,0,0.6), 0 0 30px var(--m3-glow-subtle, transparent);"
      @click.stop
    >
      <!-- Mobile Drag / Grab Handle -->
      <div class="flex justify-center pt-3 pb-1 cursor-grab" @click="$emit('close')">
        <div class="w-12 h-1.5 rounded-full" style="background: var(--m3-border-subtle, #475569);" />
      </div>

      <!-- Header with Close Button -->
      <div
        class="flex items-start justify-between px-5 pt-3 pb-2 sm:pt-5 border-b"
        style="border-color: var(--m3-border-subtle, #334155);"
      >
        <div class="flex flex-col gap-1">
          <!-- Category Badge -->
          <div v-if="categoryInfo" class="flex items-center gap-2">
            <span
              :class="[
                'inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border',
                categoryInfo.badgeClass
              ]"
            >
              <component :is="iconMap[categoryInfo.iconName]" class="w-3.5 h-3.5" />
              <span>{{ categoryInfo.label }}</span>
              <span class="text-[10px] opacity-75">({{ categoryInfo.labelJa }})</span>
            </span>

            <span
              v-if="isCollected"
              class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-950/80 text-emerald-300 border border-emerald-700/50"
            >
              <CheckCircle2 class="w-3.5 h-3.5 text-emerald-400" />
              Collected
            </span>

            <span
              v-if="isWishlist"
              class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-950/80 text-amber-300 border border-amber-600/50"
            >
              <Star class="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
              Wishlist
            </span>
          </div>

          <!-- Titles -->
          <h2 id="stamp-title" class="text-xl sm:text-2xl font-bold tracking-tight text-white mt-1">
            {{ stamp.name }}
          </h2>
          <div class="flex items-center gap-2 text-xs sm:text-sm text-slate-400 font-medium">
            <span class="text-base text-slate-200 font-serif">{{ stamp.name_ja }}</span>
            <span>•</span>
            <span class="italic text-slate-300">{{ stamp.name_romaji }}</span>
          </div>
        </div>

        <!-- Header Actions: Wishlist and Close -->
        <div class="flex items-center gap-1 -mr-2 -mt-1">
          <button
            type="button"
            @click="$emit('toggleWishlist', stamp.id)"
            :class="[
              'p-2 rounded-full transition-all',
              isWishlist
                ? 'text-amber-400 bg-amber-500/20 hover:bg-amber-500/30 border border-amber-500/40 shadow-xs'
                : 'text-slate-400 hover:text-amber-300 hover:bg-white/5'
            ]"
            :title="isWishlist ? 'Remove from Wishlist' : 'Add to Wishlist (Auf die Wunschliste)'"
            aria-label="Toggle wishlist"
          >
            <Star :class="['w-5 h-5', isWishlist ? 'fill-amber-400 text-amber-400' : '']" />
          </button>

          <button
            type="button"
            @click="$emit('close')"
            class="p-2 text-slate-400 hover:text-white hover:bg-white/10 rounded-full transition-colors"
            title="Close drawer"
            aria-label="Close drawer"
          >
            <X class="w-5 h-5" />
          </button>
        </div>
      </div>

      <!-- Scrollable Body -->
      <div class="flex-1 overflow-y-auto px-5 py-4 space-y-4">
        <!-- Stamp Showcase Card (Washi Paper Stamp-Chō Mount) -->
        <div
          class="relative rounded-2xl p-4 border flex items-center gap-4 overflow-hidden shadow-lg transition-all"
          style="background: var(--m3-surface-highlight, #1e332a); border-color: var(--m3-border-subtle, #334155);"
        >
          <!-- Stamp Paper Mount -->
          <div
            class="relative flex-shrink-0 w-24 h-24 sm:w-28 sm:h-28 bg-stone-50 rounded-2xl p-1.5 shadow-md border border-stone-200 flex items-center justify-center overflow-hidden cursor-pointer group hover:ring-2 hover:ring-rose-400 transition-all"
            @click="stamp.imageUrl ? (isImageModalOpen = true) : null"
            title="Click to inspect stamp in high resolution"
          >
            <img
              v-if="stamp.imageUrl && !hasImageError"
              :src="stamp.imageUrl"
              :alt="stamp.name"
              class="w-full h-full object-contain filter drop-shadow-xs transition-transform duration-200 group-hover:scale-110 select-none"
              loading="eager"
              @error="hasImageError = true"
            />
            <!-- Fallback Seal if no image -->
            <div
              v-else
              :class="[
                'w-full h-full rounded-xl border-2 border-dashed flex flex-col items-center justify-center p-1 text-center',
                isCollected ? 'border-emerald-600 text-emerald-700' : 'border-red-600 text-red-600'
              ]"
            >
              <span class="text-[9px] font-serif leading-none uppercase">{{ stamp.prefecture }}</span>
              <span class="text-sm font-black font-serif my-0.5 leading-none">{{ stamp.name_ja.slice(0, 2) }}</span>
              <span class="text-[8px] font-bold leading-none">記念印</span>
            </div>

            <!-- Collected "済" Stamp Seal Overlay -->
            <div
              v-if="isCollected"
              class="absolute bottom-1 right-1 bg-emerald-600/95 text-white text-[9px] font-bold px-1.5 py-0.5 rounded shadow border border-white/80 rotate-[-12deg] tracking-wider font-serif flex items-center gap-0.5 pointer-events-none"
            >
              <span>済</span>
              <span class="text-[7px]">COLLECTED</span>
            </div>
          </div>

          <!-- Description & Details -->
          <div class="flex-1 min-w-0">
            <p class="text-xs text-slate-300 leading-relaxed line-clamp-3">
              {{ stamp.description }}
            </p>
            <div class="mt-2.5 flex flex-wrap items-center gap-2">
              <button
                type="button"
                @click="$emit('focusMap', stamp.coordinates)"
                class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-700/80 hover:bg-slate-700 text-xs text-rose-300 hover:text-white font-medium border border-slate-600/60 transition-colors active:scale-95"
              >
                <Compass class="w-3.5 h-3.5 text-rose-400" />
                <span>Center on Map</span>
              </button>

              <button
                type="button"
                @click="openInGoogleMaps(stamp.coordinates[1], stamp.coordinates[0], stamp.name)"
                class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-blue-600/20 hover:bg-blue-600/30 text-xs text-blue-300 hover:text-white font-medium border border-blue-500/40 transition-colors active:scale-95 shadow-xs"
                title="Open directions in Google Maps"
              >
                <ExternalLink class="w-3.5 h-3.5 text-blue-400" />
                <span>Google Maps</span>
              </button>

              <button
                type="button"
                @click="$emit('toggleWishlist', stamp.id)"
                :class="[
                  'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium border transition-colors active:scale-95',
                  isWishlist
                    ? 'bg-amber-500/20 text-amber-300 border-amber-500/40 hover:bg-amber-500/30 font-semibold'
                    : 'bg-slate-700/80 hover:bg-slate-700 text-slate-300 hover:text-white border-slate-600/60'
                ]"
                :title="isWishlist ? 'Remove from Wishlist' : 'Add to Wishlist (Auf die Wunschliste)'"
              >
                <Star :class="['w-3.5 h-3.5', isWishlist ? 'fill-amber-400 text-amber-400' : 'text-slate-400']" />
                <span>{{ isWishlist ? 'Wishlisted' : 'Wishlist' }}</span>
              </button>
            </div>
          </div>
        </div>

        <!-- STAMP LOCATION (設置場所) - Highlighted Callout with Ask Staff Trigger -->
        <div class="bg-amber-950/30 border border-amber-500/40 rounded-2xl p-3.5">
          <div class="flex items-center justify-between mb-1.5">
            <div class="flex items-center gap-2 text-amber-400 text-xs font-bold uppercase tracking-wider">
              <MapPin class="w-4 h-4 flex-shrink-0" />
              <span>Stamp Desk Location (設置場所)</span>
            </div>
            <button
              type="button"
              @click="isAskStaffOpen = true"
              class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-gradient-to-r from-amber-500 to-rose-500 hover:from-amber-400 hover:to-rose-400 text-slate-950 font-bold text-[11px] shadow-sm transition-all active:scale-95"
              title="Show Japanese inquiry flashcard to station or shop staff"
            >
              <Languages class="w-3.5 h-3.5" />
              <span>Ask Staff (日本で尋ねる)</span>
            </button>
          </div>
          <p class="text-sm text-amber-100 font-medium leading-snug">
            {{ stamp.stampLocation }}
          </p>
        </div>

        <!-- Information Grid -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
          <!-- Operating Hours -->
          <div
            class="rounded-xl p-3 flex items-start gap-2.5 border transition-all"
            style="background: var(--m3-surface-container, #0f1d18); border-color: var(--m3-border-subtle, #334155);"
          >
            <Clock class="w-4 h-4 text-slate-400 mt-0.5 flex-shrink-0" />
            <div>
              <div class="text-slate-400 font-medium">Availability (利用時間)</div>
              <div class="text-slate-200 font-semibold mt-0.5">{{ stamp.hours }}</div>
            </div>
          </div>

          <!-- Operator / Line -->
          <div
            v-if="stamp.operator"
            class="rounded-xl p-3 flex items-start gap-2.5 border transition-all"
            style="background: var(--m3-surface-container, #0f1d18); border-color: var(--m3-border-subtle, #334155);"
          >
            <Navigation class="w-4 h-4 text-slate-400 mt-0.5 flex-shrink-0" />
            <div>
              <div class="text-slate-400 font-medium">Operator / Railway</div>
              <div class="text-slate-200 font-semibold mt-0.5 truncate">{{ stamp.operator }}</div>
            </div>
          </div>

          <!-- Address & Region -->
          <div
            class="rounded-xl p-3 sm:col-span-2 flex items-start gap-2.5 border transition-all"
            style="background: var(--m3-surface-container, #0f1d18); border-color: var(--m3-border-subtle, #334155);"
          >
            <MapPin class="w-4 h-4 text-slate-400 mt-0.5 flex-shrink-0" />
            <div>
              <div class="text-slate-400 font-medium">Address & Prefecture</div>
              <div class="text-slate-200 font-semibold mt-0.5">
                {{ stamp.address }} ({{ stamp.city }}, {{ stamp.prefecture }} Prefecture)
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Action Footer with Collect Toggle -->
      <div
        class="px-5 py-3.5 border-t flex items-center justify-between gap-3 transition-all"
        style="background: var(--m3-surface-elevated, #162720); border-color: var(--m3-border-subtle, #334155); padding-bottom: max(env(safe-area-inset-bottom, 0px), 1.25rem);"
      >
        <div class="text-xs text-slate-400 hidden sm:block">
          <span v-if="isCollected" class="text-emerald-400 font-semibold">Saved in local offline registry</span>
          <span v-else>Collect this stamp when you visit!</span>
        </div>

        <button
          type="button"
          @click="$emit('toggleCollected', stamp.id)"
          class="w-full sm:w-auto px-5 py-2.5 rounded-xl font-bold text-sm flex items-center justify-center gap-2 transition-all shadow-lg active:scale-95 text-white"
          :style="isCollected
            ? { background: '#059669', boxShadow: '0 4px 14px rgba(5, 150, 105, 0.4)' }
            : { background: 'var(--m3-primary)', boxShadow: '0 4px 16px var(--m3-glow)' }"
        >
          <CheckCircle2 v-if="isCollected" class="w-4 h-4" />
          <span v-else class="text-base font-serif leading-none">印</span>
          <span>{{ isCollected ? 'Collected! (Click to Undo)' : 'I Stamped This! (集めた)' }}</span>
        </button>
      </div>
    </div>

    <!-- Fullscreen Stamp Image Lightbox Modal -->
    <div
      v-if="isImageModalOpen && stamp?.imageUrl"
      class="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-950/85 backdrop-blur-md animate-in fade-in duration-200"
      @click="isImageModalOpen = false"
    >
      <div
        class="relative max-w-sm sm:max-w-md w-full bg-stone-50 rounded-3xl p-6 shadow-2xl border-4 border-stone-200 flex flex-col items-center gap-4 animate-in zoom-in-95 duration-200 text-stone-900"
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
            {{ categoryInfo?.label }} ({{ categoryInfo?.labelJa }})
          </div>
          <h3 class="text-xl font-bold text-stone-900 mt-0.5">{{ stamp.name }}</h3>
          <p class="text-sm font-serif text-stone-600">{{ stamp.name_ja }}</p>
        </div>

        <div class="w-64 h-64 sm:w-72 sm:h-72 bg-white rounded-2xl p-4 shadow-inner border border-stone-200 flex items-center justify-center">
          <img
            :src="stamp.imageUrl"
            :alt="stamp.name"
            class="max-w-full max-h-full object-contain filter drop-shadow-sm select-none"
          />
        </div>

        <div class="text-center text-xs text-stone-500 max-w-xs">
          {{ stamp.stampLocation }}
        </div>
      </div>
    </div>

    <!-- Ask Staff Japanese Inquiry Flashcard Modal -->
    <AskStaffModal
      :is-open="isAskStaffOpen"
      :stamp="stamp"
      @close="isAskStaffOpen = false"
    />
  </div>
</template>
