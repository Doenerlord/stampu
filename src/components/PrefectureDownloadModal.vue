<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import {
  Download,
  CheckCircle2,
  Trash2,
  X,
  Search,
  HardDrive,
  MapPin,
  RefreshCw,
  FolderDown,
  ShieldCheck,
} from 'lucide-vue-next';
import type { Stamp, PrefecturePack } from '../types/stamp';
import { getDownloadedPackIds } from '../db';
import {
  downloadPrefecturePack,
  deletePrefecturePack,
  type PackDownloadProgress,
} from '../utils/offlinePacks';

const props = defineProps<{
  isOpen: boolean;
  prefectures: PrefecturePack[];
  stamps: Stamp[];
  currentLocation?: { lat: number; lng: number } | null;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
}>();

const searchQuery = ref('');
const selectedRegion = ref('All');
const downloadedPackIds = ref<Set<string>>(new Set());
const activeDownloadingId = ref<string | null>(null);
const currentProgress = ref<PackDownloadProgress | null>(null);
const feedbackMessage = ref('');

const REGIONS = [
  'All',
  'Hokkaido',
  'Tohoku',
  'Kanto',
  'Chubu',
  'Kansai',
  'Chugoku',
  'Shikoku',
  'Kyushu & Okinawa',
];

async function loadDownloadedPacks() {
  downloadedPackIds.value = await getDownloadedPackIds();
}

onMounted(() => {
  loadDownloadedPacks();
});

const filteredPrefectures = computed(() => {
  let list = props.prefectures;
  if (selectedRegion.value !== 'All') {
    list = list.filter((p) => p.region === selectedRegion.value);
  }
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.trim().toLowerCase();
    list = list.filter(
      (p) =>
        p.name.toLowerCase().includes(q) ||
        p.name_ja.includes(q) ||
        p.region.toLowerCase().includes(q)
    );
  }
  return list;
});

const totalDownloadedCount = computed(() => downloadedPackIds.value.size);

const totalDownloadedMB = computed(() => {
  let total = 0;
  for (const p of props.prefectures) {
    if (downloadedPackIds.value.has(p.id)) {
      total += p.estimatedSizeMB;
    }
  }
  return Math.round(total * 10) / 10;
});

async function handleDownload(pack: PrefecturePack) {
  if (activeDownloadingId.value) return;
  activeDownloadingId.value = pack.id;
  currentProgress.value = {
    current: 0,
    total: 100,
    phase: 'images',
    percent: 0,
    message: `Starting download for ${pack.name}...`,
  };

  try {
    await downloadPrefecturePack(pack, props.stamps, (prog) => {
      currentProgress.value = prog;
    });
    await loadDownloadedPacks();
    feedbackMessage.value = `${pack.name} (${pack.name_ja}) is now available offline!`;
    setTimeout(() => {
      feedbackMessage.value = '';
    }, 3500);
  } catch (err: any) {
    console.error('Download pack failed', err);
    feedbackMessage.value = `Failed to download ${pack.name}: ${err.message || 'Network error'}`;
  } finally {
    activeDownloadingId.value = null;
    currentProgress.value = null;
  }
}

async function handleDelete(pack: PrefecturePack) {
  if (activeDownloadingId.value) return;
  try {
    await deletePrefecturePack(pack, props.stamps);
    await loadDownloadedPacks();
    feedbackMessage.value = `Offline pack for ${pack.name} removed.`;
    setTimeout(() => {
      feedbackMessage.value = '';
    }, 3000);
  } catch (err) {
    console.error('Failed to delete pack', err);
  }
}

function findCurrentPrefecture(): PrefecturePack | null {
  if (!props.currentLocation) return null;
  const { lat, lng } = props.currentLocation;
  for (const p of props.prefectures) {
    if (p.bounds) {
      if (
        lat >= p.bounds.minLat &&
        lat <= p.bounds.maxLat &&
        lng >= p.bounds.minLon &&
        lng <= p.bounds.maxLon
      ) {
        return p;
      }
    }
  }
  return null;
}

const currentNearbyPrefecture = computed(() => findCurrentPrefecture());
</script>

<template>
  <div
    v-if="isOpen"
    class="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-slate-950/80 backdrop-blur-md transition-opacity"
  >
    <div
      class="w-full max-w-2xl rounded-3xl shadow-2xl flex flex-col max-h-[90vh] overflow-hidden animate-in fade-in zoom-in-95 duration-200 text-slate-100"
      style="background: var(--m3-surface-elevated, #162720); border: 1px solid var(--m3-border, #334155); box-shadow: 0 20px 50px rgba(0,0,0,0.7), 0 0 30px var(--m3-glow-subtle, transparent);"
    >
      <!-- Header -->
      <div
        class="flex items-center justify-between px-5 py-4 border-b"
        style="background: var(--m3-surface-container, #0f1d18); border-color: var(--m3-border-subtle, #334155);"
      >
        <div class="flex items-center gap-2.5">
          <div
            class="w-10 h-10 rounded-xl bg-amber-500/10 text-amber-600 dark:text-amber-400 flex items-center justify-center"
          >
            <FolderDown class="w-5 h-5" />
          </div>
          <div>
            <h2 class="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
              Prefecture Offline Packs
              <span class="text-xs px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 font-semibold">
                都道府県
              </span>
            </h2>
            <p class="text-xs text-slate-500 dark:text-slate-400">
              Download stamp images & map regions for 100% offline travel in Japan
            </p>
          </div>
        </div>
        <button
          @click="emit('close')"
          class="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
        >
          <X class="w-5 h-5" />
        </button>
      </div>

      <!-- Storage Overview Banner -->
      <div
        class="bg-amber-50 dark:bg-amber-950/30 px-5 py-3 border-b border-amber-100 dark:border-amber-900/30 flex items-center justify-between text-xs"
      >
        <div class="flex items-center gap-2 text-amber-900 dark:text-amber-200">
          <HardDrive class="w-4 h-4 text-amber-600 dark:text-amber-400" />
          <span>
            <strong>{{ totalDownloadedCount }} of 47</strong> Prefectures Downloaded
            (≈ {{ totalDownloadedMB }} MB stored offline)
          </span>
        </div>
        <div
          v-if="currentNearbyPrefecture && !downloadedPackIds.has(currentNearbyPrefecture.id)"
          class="flex items-center gap-1.5"
        >
          <button
            @click="handleDownload(currentNearbyPrefecture)"
            :disabled="Boolean(activeDownloadingId)"
            class="flex items-center gap-1 px-2.5 py-1 bg-amber-600 hover:bg-amber-700 text-white rounded-md font-medium text-[11px] shadow-sm transition-all"
          >
            <MapPin class="w-3 h-3" />
            Download {{ currentNearbyPrefecture.name }}
          </button>
        </div>
      </div>

      <!-- Feedback Toast -->
      <div
        v-if="feedbackMessage"
        class="bg-emerald-500 text-white text-xs px-4 py-2 text-center font-medium shadow-sm transition-all animate-in fade-in"
      >
        {{ feedbackMessage }}
      </div>

      <!-- Controls: Search & Region Filter -->
      <div class="p-4 border-b border-slate-100 dark:border-slate-800 space-y-3 bg-slate-50/50 dark:bg-slate-900/50">
        <!-- Search Input -->
        <div class="relative">
          <Search class="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Search prefecture (e.g. Hokkaido, Tokyo, 京都, 大阪)..."
            class="w-full pl-9 pr-4 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-xs sm:text-sm text-slate-800 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-amber-500"
          />
        </div>

        <!-- Region Pills -->
        <div class="flex items-center gap-1.5 overflow-x-auto pb-1 no-scrollbar text-xs">
          <button
            v-for="region in REGIONS"
            :key="region"
            @click="selectedRegion = region"
            :class="[
              'px-3 py-1 rounded-full whitespace-nowrap transition-all font-medium',
              selectedRegion === region
                ? 'bg-amber-500 text-white shadow-sm'
                : 'bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700 hover:bg-slate-100'
            ]"
          >
            {{ region }}
          </button>
        </div>
      </div>

      <!-- Prefectures List -->
      <div class="flex-1 overflow-y-auto p-4 space-y-2.5 divide-y divide-slate-100 dark:divide-slate-800">
        <div
          v-for="pack in filteredPrefectures"
          :key="pack.id"
          class="pt-2.5 first:pt-0 flex items-center justify-between gap-3 group"
        >
          <!-- Left info -->
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2">
              <span class="font-bold text-sm text-slate-900 dark:text-slate-100">
                {{ pack.name }}
              </span>
              <span class="text-xs text-slate-400 font-japanese">
                {{ pack.name_ja }}
              </span>
              <span
                class="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400"
              >
                {{ pack.region }}
              </span>
            </div>

            <!-- Stats & breakdown -->
            <div class="flex items-center gap-3 text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              <span>{{ pack.stampCount }} Stamps</span>
              <span class="text-slate-300 dark:text-slate-600">•</span>
              <span>≈ {{ pack.estimatedSizeMB }} MB</span>
              <span
                v-if="downloadedPackIds.has(pack.id)"
                class="flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-medium ml-1"
              >
                <CheckCircle2 class="w-3.5 h-3.5" />
                Downloaded
              </span>
            </div>

            <!-- Progress bar if actively downloading this pack -->
            <div
              v-if="activeDownloadingId === pack.id && currentProgress"
              class="mt-2 space-y-1"
            >
              <div class="flex items-center justify-between text-[11px] text-amber-600 dark:text-amber-400">
                <span>{{ currentProgress.message }}</span>
                <span class="font-bold">{{ currentProgress.percent }}%</span>
              </div>
              <div class="w-full bg-slate-200 dark:bg-slate-700 h-1.5 rounded-full overflow-hidden">
                <div
                  class="bg-amber-500 h-full transition-all duration-200 rounded-full"
                  :style="{ width: `${currentProgress.percent}%` }"
                ></div>
              </div>
            </div>
          </div>

          <!-- Action Buttons -->
          <div class="flex items-center gap-1.5 shrink-0">
            <!-- Download Button -->
            <button
              v-if="!downloadedPackIds.has(pack.id)"
              @click="handleDownload(pack)"
              :disabled="Boolean(activeDownloadingId)"
              class="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-amber-500 hover:text-white dark:bg-slate-800 dark:hover:bg-amber-500 text-slate-700 dark:text-slate-200 text-xs font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
              title="Download offline pack for this prefecture"
            >
              <RefreshCw
                v-if="activeDownloadingId === pack.id"
                class="w-3.5 h-3.5 animate-spin"
              />
              <Download v-else class="w-3.5 h-3.5" />
              <span>{{ activeDownloadingId === pack.id ? 'Saving...' : 'Download' }}</span>
            </button>

            <!-- Delete / Manage Button if downloaded -->
            <button
              v-else
              @click="handleDelete(pack)"
              :disabled="Boolean(activeDownloadingId)"
              class="p-2 text-slate-400 hover:text-red-500 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/30 rounded-lg transition-colors"
              title="Delete offline pack"
            >
              <Trash2 class="w-4 h-4" />
            </button>
          </div>
        </div>

        <div
          v-if="filteredPrefectures.length === 0"
          class="py-12 text-center text-slate-400 dark:text-slate-500 text-xs"
        >
          No prefectures found matching "{{ searchQuery }}".
        </div>
      </div>

      <!-- Footer -->
      <div
        class="p-4 bg-slate-50 dark:bg-slate-900 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between text-xs text-slate-500"
      >
        <span class="flex items-center gap-1 text-[11px]">
          <ShieldCheck class="w-3.5 h-3.5 text-emerald-500" />
          Downloaded packs are stored in device CacheStorage & Dexie.
        </span>
        <button
          @click="emit('close')"
          class="px-4 py-1.5 bg-slate-200 hover:bg-slate-300 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 rounded-lg font-medium transition-colors"
        >
          Done
        </button>
      </div>
    </div>
  </div>
</template>
