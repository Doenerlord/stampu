<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue';
import {
  X,
  Layers,
  MapPin,
  Clock,
  CheckCircle2,
  Star,
  ChevronRight,
} from 'lucide-vue-next';
import type { Stamp } from '../types/stamp';
import { CATEGORIES } from '../constants/categories';

const props = defineProps<{
  isOpen: boolean;
  stamps: Stamp[];
  visitedStampIds: Set<string>;
  wishlistStampIds?: Set<string>;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'select', stamp: Stamp): void;
}>();

const locationTitle = computed(() => {
  if (!props.stamps.length) return '';
  const first = props.stamps[0];
  return first.city ? `${first.city}, ${first.prefecture}` : first.prefecture;
});

function handleKeydown(ev: KeyboardEvent) {
  if (ev.key === 'Escape' && props.isOpen) {
    emit('close');
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeydown);
});

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown);
});
</script>

<template>
  <Teleport to="body">
    <div
      v-if="isOpen"
      class="fixed inset-0 z-50 flex items-end md:items-center justify-center p-0 md:p-4"
      role="dialog"
      aria-modal="true"
      aria-label="Stempel an diesem Standort auswählen"
    >
      <!-- Backdrop -->
      <div
        class="fixed inset-0 bg-slate-950/80 backdrop-blur-sm transition-opacity"
        @click="emit('close')"
      />

      <!-- Modal Card / Bottom Sheet -->
      <div
        class="relative w-full max-w-lg bg-[#0B162C] border-t md:border border-slate-700/80 rounded-t-3xl md:rounded-2xl shadow-2xl z-10 flex flex-col max-h-[85vh] md:max-h-[80vh] overflow-hidden text-slate-100 animate-in fade-in slide-in-from-bottom-6 duration-200"
      >
        <!-- Mobile Handlebar -->
        <div class="md:hidden flex justify-center pt-3 pb-1">
          <div class="w-12 h-1.5 rounded-full bg-slate-600/80" />
        </div>

        <!-- Header -->
        <div class="px-5 pt-3 pb-3 border-b border-slate-800/80 flex items-center justify-between gap-3">
          <div class="flex items-center gap-3 min-w-0">
            <div class="w-10 h-10 rounded-xl bg-rose-500/15 border border-rose-500/30 flex items-center justify-center text-rose-400 shrink-0 shadow-inner">
              <Layers class="w-5 h-5" />
            </div>
            <div class="min-w-0">
              <div class="flex items-center gap-2">
                <h3 class="text-base font-bold text-white tracking-tight leading-tight">
                  Stempel an diesem Ort
                </h3>
                <span class="px-2 py-0.5 rounded-full text-[11px] font-bold bg-rose-500/20 text-rose-300 border border-rose-500/30">
                  {{ stamps.length }}
                </span>
              </div>
              <p class="text-xs text-slate-400 truncate mt-0.5 flex items-center gap-1 font-serif">
                <MapPin class="w-3 h-3 text-slate-500 shrink-0" />
                <span>{{ locationTitle }}</span>
              </p>
            </div>
          </div>

          <!-- Close Button -->
          <button
            type="button"
            class="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition-colors shrink-0"
            aria-label="Auswahlliste schließen"
            @click="emit('close')"
          >
            <X class="w-5 h-5" />
          </button>
        </div>

        <!-- Hint Subheader -->
        <div class="px-5 py-2 bg-slate-900/60 border-b border-slate-800/60 text-xs text-slate-300">
          Tippe auf einen Stempel, um Details, Öffnungszeiten und Motiv anzusehen:
        </div>

        <!-- Scrollable List of Overlapping Stamps -->
        <div class="flex-1 overflow-y-auto p-4 space-y-2.5 divide-y divide-slate-800/40">
          <div
            v-for="stamp in stamps"
            :key="stamp.id"
            role="button"
            tabindex="0"
            class="pt-2.5 first:pt-0 group relative flex items-center gap-3.5 p-3 rounded-2xl bg-slate-900/80 hover:bg-slate-800/90 active:scale-[0.99] border border-slate-800 hover:border-slate-700 transition-all duration-150 cursor-pointer select-none"
            @click="emit('select', stamp)"
            @keydown.enter="emit('select', stamp)"
            @keydown.space.prevent="emit('select', stamp)"
          >
            <!-- Left: Stamp Image or Hanko Preview -->
            <div class="relative w-14 h-14 rounded-xl bg-slate-950/80 border border-slate-700/80 p-1 flex items-center justify-center shrink-0 overflow-hidden shadow-inner">
              <img
                v-if="stamp.imageUrl"
                :src="stamp.imageUrl"
                :alt="stamp.name"
                class="w-full h-full object-contain drop-shadow transition-transform duration-200 group-hover:scale-105"
                loading="lazy"
              />
              <div
                v-else
                class="w-full h-full rounded-lg flex items-center justify-center text-xs font-bold font-serif"
                :style="{ backgroundColor: (CATEGORIES[stamp.category] || CATEGORIES.eki).hexColor + '20', color: (CATEGORIES[stamp.category] || CATEGORIES.eki).hexColor }"
              >
                印
              </div>

              <!-- Status Overlay Badges -->
              <div
                v-if="visitedStampIds.has(stamp.id)"
                class="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-emerald-500 border border-white flex items-center justify-center shadow-xs"
                title="Bereits gesammelt"
              >
                <CheckCircle2 class="w-3 h-3 text-white" />
              </div>
              <div
                v-else-if="wishlistStampIds?.has(stamp.id)"
                class="absolute -top-1 -left-1 w-4 h-4 rounded-full bg-amber-400 border border-slate-900 flex items-center justify-center shadow-xs"
                title="Auf der Wunschliste"
              >
                <Star class="w-2.5 h-2.5 fill-amber-900 text-amber-900" />
              </div>
            </div>

            <!-- Middle: Stamp Details -->
            <div class="flex-1 min-w-0 pr-1">
              <div class="flex items-center gap-2 mb-1">
                <!-- Category Pill -->
                <span
                  class="px-2 py-0.5 rounded-full text-[10px] font-semibold text-white tracking-wide shrink-0"
                  :style="{ backgroundColor: (CATEGORIES[stamp.category] || CATEGORIES.eki).hexColor }"
                >
                  {{ (CATEGORIES[stamp.category] || CATEGORIES.eki).label }}
                </span>
                <span v-if="stamp.operator || stamp.railwayOperator" class="text-[10px] text-slate-400 truncate">
                  {{ stamp.operator || stamp.railwayOperator }}
                </span>
              </div>

              <!-- Titles -->
              <h4 class="text-sm font-bold text-white group-hover:text-rose-200 transition-colors truncate leading-tight">
                {{ stamp.name }}
              </h4>
              <p class="text-xs text-slate-400 font-serif truncate mt-0.5">
                {{ stamp.name_ja }}
              </p>

              <!-- Stamp Location / Hours subtext -->
              <div class="flex items-center gap-3 mt-1.5 text-[11px] text-slate-400 truncate">
                <span v-if="stamp.stampLocation" class="truncate flex items-center gap-1">
                  <MapPin class="w-3 h-3 text-slate-500 shrink-0" />
                  <span>{{ stamp.stampLocation }}</span>
                </span>
                <span v-if="stamp.hours" class="shrink-0 flex items-center gap-1 text-slate-500">
                  <Clock class="w-3 h-3 text-slate-500 shrink-0" />
                  <span>{{ stamp.hours }}</span>
                </span>
              </div>
            </div>

            <!-- Right: Arrow Action Indicator -->
            <div class="text-slate-500 group-hover:text-rose-400 group-hover:translate-x-0.5 transition-all shrink-0">
              <ChevronRight class="w-5 h-5" />
            </div>
          </div>
        </div>

        <!-- Footer / Dismiss -->
        <div class="p-3 bg-slate-900/90 border-t border-slate-800/80 flex justify-end">
          <button
            type="button"
            class="w-full md:w-auto px-4 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors"
            @click="emit('close')"
          >
            Abbrechen
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
