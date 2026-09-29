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
  Info,
  ShieldCheck,
  ChevronRight,
  ZoomIn,
} from 'lucide-vue-next';
import AskStaffModal from './AskStaffModal.vue';
import StampSourceModal from './StampSourceModal.vue';
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
const isSourceModalOpen = ref(false);
const hasImageError = ref(false);
const isAskStaffOpen = ref(false);

watch(
  () => props.stamp,
  () => {
    isImageModalOpen.value = false;
    isSourceModalOpen.value = false;
    hasImageError.value = false;
    isAskStaffOpen.value = false;
  }
);

// Swipe down to dismiss state & physics
const sheetRef = ref<HTMLElement | null>(null);
const contentRef = ref<HTMLElement | null>(null);
const dragY = ref(0);
const isDragging = ref(false);
const isClosing = ref(false);

let startY = 0;
let lastY = 0;
let lastTime = 0;
let velocityY = 0;
let isPointerActive = false;
let dragTargetEl: HTMLElement | null = null;
let contentTouchStartY = 0;
let isContentTracking = false;

function startDrag(clientY: number) {
  isDragging.value = true;
  isClosing.value = false;
  startY = clientY;
  lastY = clientY;
  lastTime = performance.now();
  velocityY = 0;
}

function updateDrag(clientY: number) {
  if (!isDragging.value) return;
  const now = performance.now();
  const dt = now - lastTime;
  const dy = clientY - lastY;
  if (dt > 8) {
    velocityY = dy / dt;
    lastY = clientY;
    lastTime = now;
  }

  const rawDelta = clientY - startY;
  if (rawDelta < 0) {
    // Resistance when pulling up
    dragY.value = Math.max(-40, rawDelta * 0.2);
  } else {
    // Direct 1:1 downward drag
    dragY.value = rawDelta;
  }
}

function endDrag() {
  if (!isDragging.value) return;
  isDragging.value = false;

  const currentDrag = dragY.value;
  const sheetHeight = sheetRef.value?.offsetHeight || 500;
  const dismissDistance = Math.min(100, sheetHeight * 0.2);

  // Dismiss if pulled past threshold or flicked down with velocity
  const isDismiss = currentDrag > dismissDistance || (currentDrag > 25 && velocityY > 0.3);

  if (isDismiss) {
    isClosing.value = true;
    dragY.value = sheetHeight + 60;
    setTimeout(() => {
      emit('close');
      dragY.value = 0;
      isClosing.value = false;
    }, 220);
  } else {
    // Snap back
    dragY.value = 0;
  }
}

function onHeaderTouchStart(e: TouchEvent) {
  const target = e.target as HTMLElement | null;
  if (target?.closest('button, a, input, select, textarea')) {
    return;
  }
  if (e.touches.length !== 1) return;
  startDrag(e.touches[0].clientY);
}

function onHeaderTouchMove(e: TouchEvent) {
  if (!isDragging.value || e.touches.length !== 1) return;
  updateDrag(e.touches[0].clientY);
  if (e.cancelable) {
    e.preventDefault();
  }
}

function onHeaderTouchEnd() {
  if (isDragging.value) {
    endDrag();
  }
}

function onPointerDown(e: PointerEvent) {
  // If touch is active/handling it, ignore touch pointer event
  if (e.pointerType === 'touch') return;
  const target = e.target as HTMLElement | null;
  if (target?.closest('button, a, input, select, textarea')) {
    return;
  }

  isPointerActive = true;
  dragTargetEl = e.currentTarget as HTMLElement;
  try {
    dragTargetEl.setPointerCapture(e.pointerId);
  } catch {
    // Ignore in jsdom or environments lacking pointer capture
  }
  startDrag(e.clientY);
}

function onPointerMove(e: PointerEvent) {
  if (!isPointerActive || !isDragging.value) return;
  updateDrag(e.clientY);
}

function onPointerUp(e: PointerEvent) {
  if (!isPointerActive) return;
  isPointerActive = false;
  if (dragTargetEl) {
    try {
      dragTargetEl.releasePointerCapture(e.pointerId);
    } catch {}
    dragTargetEl = null;
  }
  endDrag();
}

function onPointerCancel(_e: PointerEvent) {
  if (!isPointerActive) return;
  isPointerActive = false;
  dragTargetEl = null;
  endDrag();
}

function onHandlebarClick() {
  if (Math.abs(dragY.value) < 6) {
    emit('close');
  }
}

function onContentTouchStart(e: TouchEvent) {
  if (e.touches.length !== 1) return;
  contentTouchStartY = e.touches[0].clientY;
  isContentTracking = true;
}

function onContentTouchMove(e: TouchEvent) {
  if (!isContentTracking || !contentRef.value || e.touches.length !== 1) return;
  const currentY = e.touches[0].clientY;
  const deltaY = currentY - contentTouchStartY;

  if (contentRef.value.scrollTop <= 0 && deltaY > 0) {
    if (!isDragging.value) {
      startDrag(contentTouchStartY);
    }
    updateDrag(currentY);
    if (e.cancelable) {
      e.preventDefault();
    }
  }
}

function onContentTouchEnd() {
  if (isContentTracking) {
    isContentTracking = false;
    if (isDragging.value) {
      endDrag();
    }
  }
}

const backdropOpacity = computed(() => {
  if (dragY.value <= 0) return 1;
  const sheetHeight = sheetRef.value?.offsetHeight || 500;
  const progress = Math.min(1, dragY.value / (sheetHeight * 0.7));
  return Math.max(0, 1 - progress);
});

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
    dragY.value = 0;
    isDragging.value = false;
    isClosing.value = false;
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
      class="fixed inset-0 bg-black/60 backdrop-blur-xs transition-opacity"
      :style="{
        opacity: backdropOpacity,
        transition: isDragging ? 'none' : 'opacity 0.25s ease',
      }"
      @click="handleBackdropClick"
      aria-hidden="true"
    />

    <!-- Material 3 Expressive Bottom Sheet Content -->
    <div
      ref="sheetRef"
      class="relative z-10 w-full sm:max-w-xl max-h-[88dvh] flex flex-col rounded-t-[32px] sm:rounded-t-[32px] shadow-2xl overflow-hidden animate-in slide-in-from-bottom duration-300 text-slate-100 will-change-transform"
      :style="{
        background: 'var(--m3-surface-elevated, #162720)',
        borderTop: '1px solid var(--m3-border, #334155)',
        boxShadow: '0 -10px 40px rgba(0,0,0,0.6), 0 0 30px var(--m3-glow-subtle, transparent)',
        transform: isDragging || isClosing || dragY !== 0 ? `translate3d(0, ${dragY}px, 0)` : undefined,
        transition: isDragging ? 'none' : isClosing ? 'transform 0.22s cubic-bezier(0.4, 0, 1, 1)' : dragY !== 0 ? 'transform 0.28s cubic-bezier(0.16, 1, 0.3, 1)' : undefined,
      }"
      @click.stop
    >
      <!-- Mobile Drag & Header Gesture Zone -->
      <div
        class="touch-none select-none"
        @touchstart="onHeaderTouchStart"
        @touchmove="onHeaderTouchMove"
        @touchend="onHeaderTouchEnd"
        @touchcancel="onHeaderTouchEnd"
        @pointerdown="onPointerDown"
        @pointermove="onPointerMove"
        @pointerup="onPointerUp"
        @pointercancel="onPointerCancel"
      >
        <!-- Mobile Drag / Grab Handle -->
        <div
          class="flex flex-col items-center pt-3 pb-1 cursor-grab active:cursor-grabbing"
          @click="onHandlebarClick"
          title="Nach unten wischen zum Schließen"
        >
          <div
            class="h-1.5 rounded-full transition-all duration-150"
            :class="isDragging ? 'w-16 scale-y-125' : 'w-12'"
            :style="{
              background: isDragging ? 'var(--m3-primary)' : 'var(--m3-border-subtle, #475569)',
              boxShadow: isDragging ? '0 0 12px var(--m3-glow)' : 'none'
            }"
          />
        </div>

        <!-- Header with Close Button -->
        <div
          class="flex items-start justify-between px-5 pt-1 pb-2 sm:pt-3 border-b"
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

        <!-- Header Actions: Info, Wishlist and Close -->
        <div class="flex items-center gap-1 -mr-2 -mt-1">
          <button
            type="button"
            @click="isSourceModalOpen = true"
            class="p-2 rounded-full text-slate-400 hover:text-emerald-300 hover:bg-white/10 transition-colors"
            title="Stamp Data Sources & Verification (Quellen & Nachweise)"
            aria-label="Stamp sources and verification info"
          >
            <Info class="w-5 h-5 text-emerald-400" />
          </button>

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
      </div>

      <!-- Scrollable Body -->
      <div
        ref="contentRef"
        class="flex-1 overflow-y-auto px-5 py-4 space-y-4"
        style="-webkit-overflow-scrolling: touch;"
        @touchstart.passive="onContentTouchStart"
        @touchmove="onContentTouchMove"
        @touchend="onContentTouchEnd"
        @touchcancel="onContentTouchEnd"
      >
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

            <!-- Zoom Overlay on Hover -->
            <div
              v-if="stamp.imageUrl && !hasImageError"
              class="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity rounded-2xl pointer-events-none"
            >
              <ZoomIn class="w-6 h-6 text-white filter drop-shadow-md" />
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
                v-if="stamp.imageUrl"
                type="button"
                @click="isImageModalOpen = true"
                class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-700/80 hover:bg-slate-700 text-xs text-slate-200 hover:text-white font-medium border border-slate-600/60 transition-colors active:scale-95"
                title="Enlarge stamp image"
              >
                <ZoomIn class="w-3.5 h-3.5 text-slate-300" />
                <span>Zoom</span>
              </button>

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

          <!-- Data Source & Registry Trigger Card -->
          <div
            class="rounded-xl p-3 sm:col-span-2 flex items-center justify-between gap-2 border transition-all cursor-pointer hover:border-emerald-500/50 hover:brightness-110 active:scale-[0.99]"
            style="background: var(--m3-surface-container, #0f1d18); border-color: var(--m3-border-subtle, #334155);"
            @click="isSourceModalOpen = true"
            title="Datenquellen & Offizielle Nachweise öffnen"
          >
            <div class="flex items-center gap-2.5 min-w-0">
              <ShieldCheck class="w-4 h-4 text-emerald-400 flex-shrink-0" />
              <div class="truncate text-xs">
                <span class="text-slate-400">Quelle & Register: </span>
                <span class="text-slate-200 font-semibold">{{ stamp.source || stamp.operator || 'Offizielles Register' }}</span>
              </div>
            </div>
            <span class="text-xs text-emerald-400 font-bold flex items-center gap-0.5 flex-shrink-0">
              Info <ChevronRight class="w-3.5 h-3.5" />
            </span>
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

    <!-- Stamp Source & Registry Modal -->
    <StampSourceModal
      v-if="stamp"
      :is-open="isSourceModalOpen"
      :stamp="stamp"
      @close="isSourceModalOpen = false"
    />
  </div>
</template>
