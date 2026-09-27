<script setup lang="ts">
import { ref, onMounted } from 'vue';
import {
  Download,
  WifiOff,
  Trash2,
  X,
  CheckCircle2,
  HardDrive,
  RefreshCw,
  Compass,
} from 'lucide-vue-next';
import {
  getTileCacheStats,
  clearTileCache,
  precacheArea,
  type PrecacheProgress,
} from '../utils/offlineMap';

const props = defineProps<{
  isOpen: boolean;
  currentBounds?: {
    minLat: number;
    maxLat: number;
    minLon: number;
    maxLon: number;
    zoom: number;
  } | null;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
}>();

const cacheStats = ref<{ count: number; estimatedSizeMB: number }>({
  count: 0,
  estimatedSizeMB: 0,
});
const isDownloading = ref(false);
const activePackName = ref('');
const downloadProgress = ref<PrecacheProgress | null>(null);
const successMessage = ref('');
const errorMessage = ref('');

async function refreshStats() {
  cacheStats.value = await getTileCacheStats();
}

onMounted(() => {
  refreshStats();
});

async function handleClearCache() {
  if (isDownloading.value) return;
  const success = await clearTileCache();
  if (success) {
    await refreshStats();
    successMessage.value = 'Offline tile cache cleared successfully!';
    setTimeout(() => {
      successMessage.value = '';
    }, 3000);
  }
}

async function runDownload(
  name: string,
  bounds: { minLat: number; maxLat: number; minLon: number; maxLon: number },
  minZoom: number,
  maxZoom: number
) {
  if (isDownloading.value) return;
  isDownloading.value = true;
  activePackName.value = name;
  errorMessage.value = '';
  successMessage.value = '';
  downloadProgress.value = { current: 0, total: 1, isComplete: false, failed: 0 };

  try {
    const result = await precacheArea(bounds, minZoom, maxZoom, 'esri', (prog) => {
      downloadProgress.value = prog;
    });
    await refreshStats();
    successMessage.value = `Successfully downloaded ${result.success} tiles for ${name}!`;
    setTimeout(() => {
      successMessage.value = '';
    }, 4000);
  } catch (err: any) {
    errorMessage.value = err.message || 'Download failed. Ensure you are connected to the internet.';
  } finally {
    isDownloading.value = false;
    downloadProgress.value = null;
    activePackName.value = '';
  }
}

function downloadTokyoPack() {
  runDownload(
    'Tokyo Yamanote Deep Zoom',
    { minLat: 35.61, maxLat: 35.74, minLon: 139.69, maxLon: 139.79 },
    12,
    15
  );
}

function downloadKansaiPack() {
  runDownload(
    'Kansai Castles (Osaka/Kyoto)',
    { minLat: 34.45, maxLat: 35.05, minLon: 135.25, maxLon: 135.85 },
    11,
    13
  );
}

function downloadCurrentView() {
  if (!props.currentBounds) return;
  const b = props.currentBounds;
  const currentZ = Math.round(b.zoom);
  const minZ = Math.max(3, currentZ);
  const maxZ = Math.min(16, currentZ + 1);

  runDownload(
    'Current Map Area',
    { minLat: b.minLat, maxLat: b.maxLat, minLon: b.minLon, maxLon: b.maxLon },
    minZ,
    maxZ
  );
}
</script>

<template>
  <div
    v-if="isOpen"
    class="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-slate-950/70 backdrop-blur-sm animate-in fade-in duration-200"
    style="padding-top: calc(env(safe-area-inset-top, 0px) + 0.75rem); padding-bottom: calc(env(safe-area-inset-bottom, 0px) + 0.75rem);"
  >
    <div
      class="bg-slate-900 border border-slate-800 rounded-3xl w-full max-w-lg max-h-[90vh] flex flex-col shadow-2xl overflow-hidden text-white"
    >
      <!-- Header -->
      <div class="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="p-2.5 bg-rose-500/10 text-rose-400 rounded-2xl border border-rose-500/20">
            <WifiOff class="w-5 h-5" />
          </div>
          <div>
            <h2 class="text-lg font-bold">Offline Map Manager</h2>
            <p class="text-xs text-slate-400">100% offline travel & stamp collection</p>
          </div>
        </div>
        <button
          @click="emit('close')"
          class="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-full transition-colors"
          aria-label="Close offline manager"
        >
          <X class="w-5 h-5" />
        </button>
      </div>

      <!-- Scrollable Content -->
      <div class="p-6 overflow-y-auto space-y-6 text-sm">
        <!-- Ready Status Banner -->
        <div class="bg-emerald-950/40 border border-emerald-500/30 rounded-2xl p-4 flex items-start gap-3.5">
          <CheckCircle2 class="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
          <div class="space-y-1">
            <div class="text-sm font-semibold text-emerald-300">
              Offline Map System Active
            </div>
            <p class="text-xs text-emerald-200/70 leading-relaxed">
              257 core tiles (Japan overview, central Tokyo & Kansai) and 139 stamp assets are pre-installed in the app. No internet connection required!
            </p>
          </div>
        </div>

        <!-- Dynamic Storage Info -->
        <div class="bg-slate-800/50 border border-slate-700/50 rounded-2xl p-4 flex items-center justify-between">
          <div class="flex items-center gap-3">
            <div class="p-2 bg-slate-700/60 rounded-xl text-slate-300">
              <HardDrive class="w-4 h-4" />
            </div>
            <div>
              <div class="text-xs text-slate-400">Dynamic Cache</div>
              <div class="text-sm font-medium text-slate-200">
                {{ cacheStats.count }} tiles cached (approx. {{ cacheStats.estimatedSizeMB }} MB)
              </div>
            </div>
          </div>
          <button
            v-if="cacheStats.count > 0"
            @click="handleClearCache"
            :disabled="isDownloading"
            class="flex items-center gap-1.5 px-3 py-1.5 text-xs text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 rounded-xl transition-colors disabled:opacity-50"
          >
            <Trash2 class="w-3.5 h-3.5" />
            <span>Clear</span>
          </button>
        </div>

        <!-- Download Progress Indicator -->
        <div v-if="isDownloading && downloadProgress" class="bg-blue-950/40 border border-blue-500/30 rounded-2xl p-4 space-y-2.5">
          <div class="flex items-center justify-between text-xs">
            <span class="text-blue-300 font-medium flex items-center gap-1.5">
              <RefreshCw class="w-3.5 h-3.5 animate-spin" />
              Downloading: {{ activePackName }}
            </span>
            <span class="text-blue-400 font-mono">
              {{ downloadProgress.current }} / {{ downloadProgress.total }}
            </span>
          </div>
          <div class="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
            <div
              class="bg-blue-500 h-full transition-all duration-150 rounded-full"
              :style="{ width: `${Math.round((downloadProgress.current / downloadProgress.total) * 100)}%` }"
            ></div>
          </div>
        </div>

        <!-- Success/Error Feedback -->
        <div
          v-if="successMessage"
          class="bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-xs px-3.5 py-2.5 rounded-xl flex items-center gap-2"
        >
          <CheckCircle2 class="w-4 h-4 shrink-0" />
          <span>{{ successMessage }}</span>
        </div>
        <div
          v-if="errorMessage"
          class="bg-rose-500/15 border border-rose-500/30 text-rose-300 text-xs px-3.5 py-2.5 rounded-xl flex items-center gap-2"
        >
          <X class="w-4 h-4 shrink-0" />
          <span>{{ errorMessage }}</span>
        </div>

        <!-- Pre-cache Regional Packs -->
        <div class="space-y-3">
          <h3 class="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Download Detailed Travel Packs
          </h3>

          <!-- Tokyo Pack -->
          <div class="bg-slate-800/40 border border-slate-700/40 rounded-2xl p-4 flex items-center justify-between gap-4">
            <div class="space-y-0.5">
              <div class="text-sm font-semibold flex items-center gap-2">
                <span>Tokyo Yamanote Loop</span>
                <span class="text-[10px] bg-slate-700 text-slate-300 px-2 py-0.5 rounded-full font-normal">Zoom 12–15</span>
              </div>
              <p class="text-xs text-slate-400">Detailed station-level streets & buildings (~2.5 MB)</p>
            </div>
            <button
              @click="downloadTokyoPack"
              :disabled="isDownloading"
              class="shrink-0 flex items-center gap-1.5 px-3.5 py-2 bg-rose-600 hover:bg-rose-500 active:scale-95 text-white text-xs font-medium rounded-xl transition-all disabled:opacity-50"
            >
              <Download class="w-3.5 h-3.5" />
              <span>Download</span>
            </button>
          </div>

          <!-- Kansai Pack -->
          <div class="bg-slate-800/40 border border-slate-700/40 rounded-2xl p-4 flex items-center justify-between gap-4">
            <div class="space-y-0.5">
              <div class="text-sm font-semibold flex items-center gap-2">
                <span>Kansai Castles Area</span>
                <span class="text-[10px] bg-slate-700 text-slate-300 px-2 py-0.5 rounded-full font-normal">Zoom 11–13</span>
              </div>
              <p class="text-xs text-slate-400">Osaka, Kyoto, Nara, Himeji regions (~3.0 MB)</p>
            </div>
            <button
              @click="downloadKansaiPack"
              :disabled="isDownloading"
              class="shrink-0 flex items-center gap-1.5 px-3.5 py-2 bg-rose-600 hover:bg-rose-500 active:scale-95 text-white text-xs font-medium rounded-xl transition-all disabled:opacity-50"
            >
              <Download class="w-3.5 h-3.5" />
              <span>Download</span>
            </button>
          </div>

          <!-- Cache Current View -->
          <div
            v-if="props.currentBounds"
            class="bg-slate-800/40 border border-slate-700/40 rounded-2xl p-4 flex items-center justify-between gap-4"
          >
            <div class="space-y-0.5">
              <div class="text-sm font-semibold flex items-center gap-2">
                <span>Current Map Viewport</span>
                <span class="text-[10px] bg-slate-700 text-slate-300 px-2 py-0.5 rounded-full font-normal">
                  Zoom {{ Math.round(props.currentBounds.zoom) }}–{{ Math.min(16, Math.round(props.currentBounds.zoom) + 1) }}
                </span>
              </div>
              <p class="text-xs text-slate-400">Save your current screen position for offline use</p>
            </div>
            <button
              @click="downloadCurrentView"
              :disabled="isDownloading"
              class="shrink-0 flex items-center gap-1.5 px-3.5 py-2 bg-slate-700 hover:bg-slate-600 active:scale-95 text-white text-xs font-medium rounded-xl transition-all disabled:opacity-50"
            >
              <Compass class="w-3.5 h-3.5" />
              <span>Cache View</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
