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
  Compass,
  Maximize2,
} from 'lucide-vue-next';

const props = defineProps<{
  stamp: Stamp | null;
  isOpen: boolean;
  isCollected: boolean;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'toggleCollected', stampId: string): void;
  (e: 'focusMap', coordinates: [number, number]): void;
}>();

const isImageModalOpen = ref(false);

watch(
  () => props.stamp,
  () => {
    isImageModalOpen.value = false;
  }
);

const iconMap = {
  Train,
  Store,
  Car,
  Castle,
  Sparkles,
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
    class="fixed inset-0 z-50 flex flex-col justify-end sm:items-center sm:justify-end pointer-events-auto"
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

    <!-- Bottom Sheet Content -->
    <div
      class="relative z-10 w-full sm:max-w-xl max-h-[85vh] sm:max-h-[80vh] flex flex-col bg-slate-900 border-t sm:border border-slate-700/80 rounded-t-3xl sm:rounded-3xl sm:mb-4 shadow-2xl overflow-hidden animate-in slide-in-from-bottom duration-300 transition-all text-slate-100"
      @click.stop
    >
      <!-- Mobile Drag / Grab Handle -->
      <div class="flex justify-center pt-2.5 pb-1 sm:hidden cursor-grab" @click="$emit('close')">
        <div class="w-12 h-1.5 bg-slate-700 rounded-full" />
      </div>

      <!-- Header with Close Button -->
      <div class="flex items-start justify-between px-5 pt-3 pb-2 sm:pt-5 border-b border-slate-800">
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

        <!-- Close Button -->
        <button
          type="button"
          @click="$emit('close')"
          class="p-2 -mr-2 -mt-1 text-slate-400 hover:text-white hover:bg-slate-800 rounded-full transition-colors"
          title="Close drawer"
          aria-label="Close drawer"
        >
          <X class="w-5 h-5" />
        </button>
      </div>

      <!-- Scrollable Body -->
      <div class="flex-1 overflow-y-auto px-5 py-4 space-y-4">
        <!-- Stamp Showcase Card (Washi Paper Stamp-Chō Mount) -->
        <div class="relative bg-slate-800/80 rounded-2xl p-4 border border-slate-700/80 flex items-center gap-4 overflow-hidden shadow-lg">
          <!-- Stamp Paper Mount -->
          <div
            class="relative flex-shrink-0 w-24 h-24 sm:w-28 sm:h-28 bg-stone-50 rounded-2xl p-1.5 shadow-md border border-stone-200 flex items-center justify-center overflow-hidden cursor-pointer group hover:ring-2 hover:ring-rose-400 transition-all"
            @click="stamp.imageUrl ? (isImageModalOpen = true) : null"
            title="Click to inspect stamp in high resolution"
          >
            <img
              v-if="stamp.imageUrl"
              :src="stamp.imageUrl"
              :alt="stamp.name"
              class="w-full h-full object-contain filter drop-shadow-xs transition-transform duration-200 group-hover:scale-110 select-none"
              loading="eager"
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
                v-if="stamp.imageUrl"
                type="button"
                @click="isImageModalOpen = true"
                class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-700/80 hover:bg-slate-700 text-xs text-slate-300 hover:text-white font-medium border border-slate-600/60 transition-colors active:scale-95"
              >
                <Maximize2 class="w-3.5 h-3.5 text-slate-400" />
                <span>Enlarge</span>
              </button>
            </div>
          </div>
        </div>

        <!-- STAMP LOCATION (設置場所) - Highlighted Callout -->
        <div class="bg-amber-950/30 border border-amber-500/40 rounded-2xl p-3.5">
          <div class="flex items-center gap-2 text-amber-400 text-xs font-bold uppercase tracking-wider mb-1.5">
            <MapPin class="w-4 h-4 flex-shrink-0" />
            <span>Stamp Desk Location (設置場所)</span>
          </div>
          <p class="text-sm text-amber-100 font-medium leading-snug">
            {{ stamp.stampLocation }}
          </p>
        </div>

        <!-- Information Grid -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
          <!-- Operating Hours -->
          <div class="bg-slate-800/60 border border-slate-700/60 rounded-xl p-3 flex items-start gap-2.5">
            <Clock class="w-4 h-4 text-slate-400 mt-0.5 flex-shrink-0" />
            <div>
              <div class="text-slate-400 font-medium">Availability (利用時間)</div>
              <div class="text-slate-200 font-semibold mt-0.5">{{ stamp.hours }}</div>
            </div>
          </div>

          <!-- Operator / Line -->
          <div v-if="stamp.operator" class="bg-slate-800/60 border border-slate-700/60 rounded-xl p-3 flex items-start gap-2.5">
            <Navigation class="w-4 h-4 text-slate-400 mt-0.5 flex-shrink-0" />
            <div>
              <div class="text-slate-400 font-medium">Operator / Railway</div>
              <div class="text-slate-200 font-semibold mt-0.5 truncate">{{ stamp.operator }}</div>
            </div>
          </div>

          <!-- Address & Region -->
          <div class="bg-slate-800/60 border border-slate-700/60 rounded-xl p-3 sm:col-span-2 flex items-start gap-2.5">
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
      <div class="px-5 py-3.5 bg-slate-950/80 border-t border-slate-800 flex items-center justify-between gap-3">
        <div class="text-xs text-slate-400 hidden sm:block">
          <span v-if="isCollected" class="text-emerald-400 font-semibold">Saved in local offline registry</span>
          <span v-else>Collect this stamp when you visit!</span>
        </div>

        <button
          type="button"
          @click="$emit('toggleCollected', stamp.id)"
          :class="[
            'w-full sm:w-auto px-5 py-2.5 rounded-xl font-bold text-sm flex items-center justify-center gap-2 transition-all shadow-lg active:scale-95',
            isCollected
              ? 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-950/50'
              : 'bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-500 hover:to-rose-500 text-white shadow-red-950/50'
          ]"
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
  </div>
</template>
