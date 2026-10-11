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

      <!-- Modal Card / Bottom Sheet (Material 3 Expressive Dynamic Surface) -->
      <div
        class="relative w-full max-w-lg rounded-t-3xl md:rounded-2xl shadow-2xl z-10 flex flex-col max-h-[85vh] md:max-h-[80vh] overflow-hidden text-slate-100 animate-in fade-in slide-in-from-bottom-6 duration-200"
        style="background: var(--m3-surface-elevated, #162720); border: 1px solid var(--m3-border, #334155); box-shadow: 0 20px 50px rgba(0,0,0,0.7), 0 0 30px var(--m3-glow-subtle, transparent);"
      >
        <!-- Mobile Handlebar -->
        <div class="md:hidden flex justify-center pt-3 pb-1">
          <div
            class="w-12 h-1.5 rounded-full"
            style="background: var(--m3-border-subtle, #475569);"
          />
        </div>

        <!-- Header -->
        <div
          class="px-5 pt-3 pb-3 border-b flex items-center justify-between gap-3"
          style="background: var(--m3-surface-container, #0f1d18); border-color: var(--m3-border-subtle, #334155);"
        >
          <div class="flex items-center gap-3 min-w-0">
            <!-- Themed Icon Container -->
            <div
              class="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 shadow-inner"
              style="background: var(--m3-badge-bg, rgba(16, 185, 129, 0.2)); border: 1px solid var(--m3-border, #334155); color: var(--m3-primary, #10b981);"
            >
              <Layers class="w-5 h-5" />
            </div>

            <div class="min-w-0">
              <div class="flex items-center gap-2">
                <h3 class="text-base font-bold text-white tracking-tight leading-tight">
                  Stempel an diesem Ort
                </h3>
                <!-- Themed Counter Pill -->
                <span
                  class="px-2 py-0.5 rounded-full text-[11px] font-bold"
                  style="background: var(--m3-badge-bg, rgba(16, 185, 129, 0.2)); border: 1px solid var(--m3-border-subtle, #334155); color: var(--m3-primary, #10b981);"
                >
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
            class="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800/80 transition-colors shrink-0"
            aria-label="Auswahlliste schließen"
            @click="emit('close')"
          >
            <X class="w-5 h-5" />
          </button>
        </div>

        <!-- Hint Subheader -->
        <div
          class="px-5 py-2 border-b text-xs text-slate-300"
          style="background: var(--m3-surface-tint, #0c1814); border-color: var(--m3-border-subtle, #334155);"
        >
          Tippe auf einen Stempel, um Details, Öffnungszeiten und Motiv anzusehen:
        </div>

        <!-- Scrollable List of Overlapping Stamps -->
        <div class="flex-1 overflow-y-auto p-4 space-y-2.5">
          <div
            v-for="stamp in stamps"
            :key="stamp.id"
            role="button"
            tabindex="0"
            class="stamp-item-card group relative flex items-center gap-3.5 p-3 rounded-2xl active:scale-[0.99] transition-all duration-150 cursor-pointer select-none"
            style="background: var(--m3-surface-container, #0f1d18); border: 1px solid var(--m3-border-subtle, #334155);"
            @click="emit('select', stamp)"
            @keydown.enter="emit('select', stamp)"
            @keydown.space.prevent="emit('select', stamp)"
          >
            <!-- Left: Stamp Image or Hanko Preview -->
            <div
              class="relative w-14 h-14 rounded-xl p-1 flex items-center justify-center shrink-0 overflow-hidden shadow-inner"
              style="background: var(--m3-surface-highlight, #1e332a); border: 1px solid var(--m3-border-subtle, #334155);"
            >
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
                  class="px-2 py-0.5 rounded-full text-[10px] font-semibold text-white tracking-wide shrink-0 shadow-xs"
                  :style="{ backgroundColor: (CATEGORIES[stamp.category] || CATEGORIES.eki).hexColor }"
                >
                  {{ (CATEGORIES[stamp.category] || CATEGORIES.eki).label }}
                </span>
                <span v-if="stamp.operator || stamp.railwayOperator" class="text-[10px] text-slate-400 truncate">
                  {{ stamp.operator || stamp.railwayOperator }}
                </span>
              </div>

              <!-- Titles -->
              <h4 class="text-sm font-bold text-white transition-colors truncate leading-tight group-hover:text-[var(--m3-primary)]">
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
            <div class="text-slate-500 group-hover:text-[var(--m3-primary)] group-hover:translate-x-0.5 transition-all shrink-0">
              <ChevronRight class="w-5 h-5" />
            </div>
          </div>
        </div>

        <!-- Footer / Dismiss -->
        <div
          class="p-3 border-t flex justify-end"
          style="background: var(--m3-surface-container, #0f1d18); border-color: var(--m3-border-subtle, #334155); padding-bottom: max(env(safe-area-inset-bottom, 0px), 0.75rem);"
        >
          <button
            type="button"
            class="w-full md:w-auto px-4 py-2 rounded-xl text-xs font-semibold text-slate-300 hover:text-white transition-colors"
            style="background: var(--m3-surface-highlight, #1e332a); border: 1px solid var(--m3-border-subtle, #334155);"
            @click="emit('close')"
          >
            Abbrechen
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.stamp-item-card:hover {
  background: var(--m3-surface-highlight, #1e332a) !important;
  border-color: var(--m3-border, #334155) !important;
  box-shadow: 0 4px 14px var(--m3-glow-subtle, rgba(0, 0, 0, 0.2));
}
</style>
