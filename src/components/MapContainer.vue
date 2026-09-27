<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue';
import {
  Map as MapLibreMap,
  NavigationControl,
  GeolocateControl,
  Marker,
  LngLatBounds,
  type StyleSpecification,
} from 'maplibre-gl';
import type { Stamp } from '../types/stamp';
import { CATEGORIES } from '../constants/categories';

const props = defineProps<{
  stamps: Stamp[];
  selectedStamp: Stamp | null;
  visitedStampIds: Set<string>;
}>();

const emit = defineEmits<{
  (e: 'selectStamp', stamp: Stamp): void;
}>();

const mapContainerRef = ref<HTMLDivElement | null>(null);
const currentBasemap = ref<'esri' | 'gsi_std' | 'gsi_pale'>('esri');
let map: MapLibreMap | null = null;
const markersMap = new Map<string, Marker>();

// Available high-performance tile sources with NO API key requirements
const MAP_STYLES: Record<string, StyleSpecification> = {
  esri: {
    version: 8,
    sources: {
      'raster-tiles': {
        type: 'raster',
        tiles: [
          'https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',
        ],
        tileSize: 256,
        attribution:
          'Tiles &copy; Esri &mdash; Sources: Esri, DeLorme, NAVTEQ, USGS, Intermap, iPC, METI, TomTom',
        maxzoom: 19,
      },
    },
    layers: [
      {
        id: 'raster-layer',
        type: 'raster',
        source: 'raster-tiles',
        minzoom: 0,
        maxzoom: 19,
      },
    ],
  },
  gsi_std: {
    version: 8,
    sources: {
      'raster-tiles': {
        type: 'raster',
        tiles: ['https://cyberjapandata.gsi.go.jp/xyz/std/{z}/{x}/{y}.png'],
        tileSize: 256,
        attribution:
          '&copy; <a href="https://maps.gsi.go.jp/development/ichiran.html">国土地理院 (GSI Japan)</a>',
        maxzoom: 18,
      },
    },
    layers: [
      {
        id: 'raster-layer',
        type: 'raster',
        source: 'raster-tiles',
        minzoom: 2,
        maxzoom: 18,
      },
    ],
  },
  gsi_pale: {
    version: 8,
    sources: {
      'raster-tiles': {
        type: 'raster',
        tiles: ['https://cyberjapandata.gsi.go.jp/xyz/pale/{z}/{x}/{y}.png'],
        tileSize: 256,
        attribution:
          '&copy; <a href="https://maps.gsi.go.jp/development/ichiran.html">国土地理院 (GSI Japan) 淡色地図</a>',
        maxzoom: 18,
      },
    },
    layers: [
      {
        id: 'raster-layer',
        type: 'raster',
        source: 'raster-tiles',
        minzoom: 2,
        maxzoom: 18,
      },
    ],
  },
};

const iconSvgs: Record<string, string> = {
  Train: '<path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" x2="4" y1="22" y2="15"/><line x1="9" x2="9" y1="15" y2="18"/><line x1="15" x2="15" y1="15" y2="18"/><line x1="20" x2="20" y1="22" y2="15"/>',
  Store: '<path d="m2 7 4.41-4.41A2 2 0 0 1 7.83 2h8.34a2 2 0 0 1 1.42.59L22 7"/><path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"/><path d="M15 22v-4a2 2 0 0 0-2-2h-2a2 2 0 0 0-2 2v4"/><path d="M2 7h20"/><path d="M22 7v3a2 2 0 0 1-2 2v0a2.7 2.7 0 0 1-1.59-.63.7.7 0 0 0-.82 0A2.7 2.7 0 0 1 16 12a2.7 2.7 0 0 1-1.59-.63.7.7 0 0 0-.82 0A2.7 2.7 0 0 1 12 12a2.7 2.7 0 0 1-1.59-.63.7.7 0 0 0-.82 0A2.7 2.7 0 0 1 8 12a2.7 2.7 0 0 1-1.59-.63.7.7 0 0 0-.82 0A2.7 2.7 0 0 1 4 12v0a2 2 0 0 1-2-2V7"/>',
  Car: '<path d="M19 17h2c.6 0 1-.4 1-1v-3c0-.9-.7-1.7-1.5-1.9C18.7 10.6 16 10 16 10s-1.3-1.4-2.2-2.3c-.5-.4-1.1-.7-1.8-.7H5c-.6 0-1.1.4-1.4.9l-1.4 2.9A3.7 3.7 0 0 0 2 12v4c0 .6.4 1 1 1h2"/><circle cx="7" cy="17" r="2"/><circle cx="17" cy="17" r="2"/>',
  Castle: '<path d="M22 20v-9H2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2Z"/><path d="M18 11V4H6v7"/><path d="M15 22v-4a3 3 0 0 0-6 0v4"/><path d="M22 11V9"/><path d="M2 11V9"/><path d="M6 4V2"/><path d="M18 4V2"/><path d="M10 4V2"/><path d="M14 4V2"/>',
  Sparkles: '<path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/>',
};

function renderMarkerContent(wrapper: HTMLElement, stamp: Stamp) {
  const cat = CATEGORIES[stamp.category] || CATEGORIES.eki;
  const isVisited = props.visitedStampIds.has(stamp.id);
  const isSelected = props.selectedStamp?.id === stamp.id;

  wrapper.dataset.stampId = stamp.id;
  wrapper.setAttribute('role', 'button');
  wrapper.setAttribute('tabindex', '0');
  wrapper.setAttribute('aria-label', `${stamp.name} (${stamp.name_ja})`);

  wrapper.innerHTML = `
    <div class="relative group flex flex-col items-center select-none" style="pointer-events: auto;">
      <!-- Tooltip (visible on hover) -->
      <div class="pointer-events-none absolute bottom-full mb-2 hidden group-hover:flex flex-col items-center z-30 transition-all opacity-0 group-hover:opacity-100">
        <div class="bg-slate-900/95 text-white px-2.5 py-1 rounded-lg text-[11px] font-semibold tracking-wide whitespace-nowrap shadow-xl border border-slate-700/80 flex items-center gap-1.5">
          <span>${stamp.name}</span>
          <span class="text-slate-400 font-serif text-[10px]">${stamp.name_ja}</span>
        </div>
        <div class="w-2 h-2 bg-slate-900 rotate-45 -mt-1 border-r border-b border-slate-700"></div>
      </div>

      <!-- Main Pin Badge -->
      <div
        class="marker-pin relative flex items-center justify-center w-8 h-8 rounded-full border-2 shadow-lg transition-transform duration-200 group-hover:scale-125 ${
          isSelected
            ? 'scale-125 ring-4 ring-white ring-offset-2 ring-offset-slate-900 z-20'
            : 'z-10'
        }"
        style="background-color: ${cat.hexColor}; border-color: #ffffff;"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2.5"
          stroke-linecap="round"
          stroke-linejoin="round"
          class="w-4 h-4 text-white"
        >
          ${iconSvgs[cat.iconName] || iconSvgs.Train}
        </svg>

        <!-- Collected checkmark badge in corner -->
        ${
          isVisited
            ? `
          <span class="absolute -top-1 -right-1 w-3.5 h-3.5 rounded-full bg-emerald-500 border border-white flex items-center justify-center shadow-xs">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" class="w-2.5 h-2.5">
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
          </span>
        `
            : ''
        }
      </div>

      <!-- Pin Needle Point -->
      <div
        class="w-1.5 h-1.5 rotate-45 -mt-0.5 shadow-xs"
        style="background-color: ${cat.hexColor};"
      ></div>
    </div>
  `;
}

function updateMarkers() {
  if (!map) return;

  const currentIds = new Set(props.stamps.map((s) => s.id));

  // 1. Remove markers no longer in current stamps
  for (const [id, marker] of markersMap.entries()) {
    if (!currentIds.has(id)) {
      marker.remove();
      markersMap.delete(id);
    }
  }

  // 2. Update existing or create new markers
  for (const stamp of props.stamps) {
    const existing = markersMap.get(stamp.id);
    if (existing) {
      // Safely update inner content without detaching element from MapLibre
      renderMarkerContent(existing.getElement(), stamp);
      existing.setLngLat(stamp.coordinates);
    } else {
      const el = document.createElement('div');
      el.className = 'stampu-marker-root';
      renderMarkerContent(el, stamp);

      el.addEventListener('click', (ev) => {
        ev.stopPropagation();
        emit('selectStamp', stamp);
      });

      const marker = new Marker({
        element: el,
        anchor: 'bottom',
      })
        .setLngLat(stamp.coordinates)
        .addTo(map);

      markersMap.set(stamp.id, marker);
    }
  }
}

function switchBasemap(styleKey: 'esri' | 'gsi_std' | 'gsi_pale') {
  if (!map || currentBasemap.value === styleKey) return;
  currentBasemap.value = styleKey;
  map.setStyle(MAP_STYLES[styleKey]);
  // Once new style loads, restore markers
  map.once('style.load', () => {
    updateMarkers();
  });
}

function focusCoordinates(coordinates: [number, number], zoom = 12) {
  if (!map) return;
  map.easeTo({
    center: coordinates,
    zoom,
    duration: 1000,
    essential: true,
  });
}

function resetJapanView() {
  if (!map) return;
  map.easeTo({
    center: [138.2529, 36.2048],
    zoom: 5.5,
    pitch: 0,
    bearing: 0,
    duration: 1200,
    essential: true,
  });
}

function fitAllStamps() {
  if (!map || props.stamps.length === 0) return;
  const bounds = new LngLatBounds();
  for (const s of props.stamps) {
    bounds.extend(s.coordinates);
  }
  map.fitBounds(bounds, {
    padding: { top: 80, bottom: 80, left: 50, right: 50 },
    maxZoom: 14,
    duration: 1000,
  });
}

onMounted(() => {
  if (!mapContainerRef.value) return;

  map = new MapLibreMap({
    container: mapContainerRef.value,
    style: MAP_STYLES.esri,
    center: [138.2529, 36.2048], // Japan center
    zoom: 5.5,
    minZoom: 3.5,
    maxZoom: 18,
    attributionControl: false,
  });

  map.addControl(
    new NavigationControl({
      showCompass: true,
      showZoom: true,
      visualizePitch: true,
    }),
    'bottom-right'
  );

  map.addControl(
    new GeolocateControl({
      positionOptions: { enableHighAccuracy: true },
      trackUserLocation: true,
    }),
    'bottom-right'
  );

  map.on('load', () => {
    updateMarkers();
  });
});

onUnmounted(() => {
  for (const marker of markersMap.values()) {
    marker.remove();
  }
  markersMap.clear();
  if (map) {
    map.remove();
    map = null;
  }
});

// Watch for changes in stamps, selected stamp, or visited stamps
watch(
  () => [props.stamps, props.selectedStamp, props.visitedStampIds],
  () => {
    nextTick(() => {
      updateMarkers();
    });
  },
  { deep: true }
);

// If selected stamp changes, gently center on it
watch(
  () => props.selectedStamp,
  (newStamp) => {
    if (newStamp && map) {
      focusCoordinates(newStamp.coordinates, Math.max(map.getZoom(), 11));
    }
  }
);

defineExpose({
  focusCoordinates,
  resetJapanView,
  fitAllStamps,
  switchBasemap,
});
</script>

<template>
  <div class="relative w-full h-full overflow-hidden select-none bg-slate-950">
    <!-- MapLibre canvas container -->
    <div ref="mapContainerRef" class="w-full h-full absolute inset-0" />

    <!-- Map Quick Action Controls (Floating bottom-left) -->
    <div class="absolute bottom-6 left-4 z-20 flex flex-col gap-2 pointer-events-auto">
      <!-- Basemap Style Selector -->
      <div
        class="flex items-center gap-1 p-1 rounded-xl bg-slate-900/90 border border-slate-700/80 shadow-lg backdrop-blur-md"
      >
        <button
          type="button"
          @click="switchBasemap('esri')"
          :class="[
            'px-2 py-1 text-[11px] font-semibold rounded-lg transition-all',
            currentBasemap === 'esri'
              ? 'bg-blue-600 text-white shadow-sm'
              : 'text-slate-400 hover:text-white',
          ]"
          title="ESRI World Street Map (Bilingual English/Japanese)"
        >
          Street
        </button>
        <button
          type="button"
          @click="switchBasemap('gsi_std')"
          :class="[
            'px-2 py-1 text-[11px] font-semibold rounded-lg transition-all',
            currentBasemap === 'gsi_std'
              ? 'bg-blue-600 text-white shadow-sm'
              : 'text-slate-400 hover:text-white',
          ]"
          title="GSI Japan Standard Map (国土地理院)"
        >
          Japan GSI
        </button>
        <button
          type="button"
          @click="switchBasemap('gsi_pale')"
          :class="[
            'px-2 py-1 text-[11px] font-semibold rounded-lg transition-all',
            currentBasemap === 'gsi_pale'
              ? 'bg-blue-600 text-white shadow-sm'
              : 'text-slate-400 hover:text-white',
          ]"
          title="GSI Japan Pale Map (淡色地図)"
        >
          Pale
        </button>
      </div>

      <div class="flex items-center gap-2">
        <button
          type="button"
          @click="resetJapanView"
          class="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-900/90 hover:bg-slate-800 text-slate-200 hover:text-white border border-slate-700/80 shadow-lg backdrop-blur-md text-xs font-semibold transition-all active:scale-95"
          title="Reset view to whole Japan overview"
        >
          <span class="font-serif text-sm leading-none text-red-500 font-bold">日本</span>
          <span>Japan Overview</span>
        </button>

        <button
          type="button"
          @click="fitAllStamps"
          class="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-900/90 hover:bg-slate-800 text-slate-200 hover:text-white border border-slate-700/80 shadow-lg backdrop-blur-md text-xs font-semibold transition-all active:scale-95"
          title="Fit all current filtered stamps into view"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            class="w-3.5 h-3.5 text-amber-400"
          >
            <path d="M3 7V5a2 2 0 0 1 2-2h2" />
            <path d="M17 3h2a2 2 0 0 1 2 2v2" />
            <path d="M21 17v2a2 2 0 0 1-2 2h-2" />
            <path d="M7 21H5a2 2 0 0 1-2-2v-2" />
          </svg>
          <span>Fit Visible ({{ stamps.length }})</span>
        </button>
      </div>
    </div>
  </div>
</template>

<style>
/* MapLibre Controls Styling for dark theme integration */
.maplibregl-ctrl-group {
  background-color: rgba(15, 23, 42, 0.9) !important;
  border: 1px solid rgba(51, 65, 85, 0.8) !important;
  border-radius: 12px !important;
  overflow: hidden !important;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3) !important;
  backdrop-filter: blur(8px) !important;
}

.maplibregl-ctrl-group button {
  border-bottom: 1px solid rgba(51, 65, 85, 0.6) !important;
  width: 34px !important;
  height: 34px !important;
}

.maplibregl-ctrl-group button:last-child {
  border-bottom: none !important;
}

.maplibregl-ctrl-group button .maplibregl-ctrl-icon {
  filter: invert(0.9) !important;
}

.maplibregl-ctrl-group button:hover {
  background-color: rgba(30, 41, 59, 0.9) !important;
}
</style>
