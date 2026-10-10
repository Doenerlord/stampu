<script setup lang="ts">
import { ref, computed } from 'vue';
import type { Stamp, StampRally } from '../types/stamp';
import {
  Flag,
  X,
  Compass,
  CheckCircle2,
  Gift,
  Calendar,
  Sparkles,
  Trophy,
} from 'lucide-vue-next';

const props = defineProps<{
  isOpen: boolean;
  rallies: StampRally[];
  stamps: Stamp[];
  visitedStampIds: Set<string>;
  activeRallyId?: string | null;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'selectRally', rally: StampRally): void;
  (e: 'selectStamp', stamp: Stamp): void;
  (e: 'exitRallyFocus'): void;
}>();

const activeTab = ref<'active' | 'upcoming' | 'archived'>('active');

// Stamp ID lookup map
const stampMap = computed(() => {
  const map = new Map<string, Stamp>();
  for (const s of props.stamps) {
    map.set(s.id, s);
  }
  return map;
});

// Helper for status and days remaining
function getRallyStatus(rally: StampRally) {
  const today = new Date().toISOString().split('T')[0];
  if (today < rally.validFrom) {
    const diff = Math.ceil((new Date(rally.validFrom).getTime() - new Date(today).getTime()) / (1000 * 3600 * 24));
    return {
      status: 'upcoming' as const,
      label: `Starts in ${diff} ${diff === 1 ? 'day' : 'days'}`,
      badgeClass: 'bg-amber-500/20 text-amber-300 border-amber-500/40',
    };
  } else if (today <= rally.validUntil) {
    const diff = Math.ceil((new Date(rally.validUntil).getTime() - new Date(today).getTime()) / (1000 * 3600 * 24));
    return {
      status: 'active' as const,
      label: diff === 0 ? 'Ends today!' : `Ends in ${diff} ${diff === 1 ? 'day' : 'days'}`,
      badgeClass: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40',
    };
  } else {
    return {
      status: 'archived' as const,
      label: 'Archived',
      badgeClass: 'bg-slate-700/60 text-slate-400 border-slate-600/40',
    };
  }
}

const classifiedRallies = computed(() => {
  const active: StampRally[] = [];
  const upcoming: StampRally[] = [];
  const archived: StampRally[] = [];

  for (const r of props.rallies) {
    const { status } = getRallyStatus(r);
    if (status === 'active') active.push(r);
    else if (status === 'upcoming') upcoming.push(r);
    else archived.push(r);
  }

  return { active, upcoming, archived };
});

const currentRallies = computed(() => {
  return classifiedRallies.value[activeTab.value];
});

function getRallyProgress(rally: StampRally) {
  const total = rally.stampIds.length;
  if (total === 0) return { collected: 0, total: 0, percent: 0, isComplete: false };
  let collected = 0;
  for (const id of rally.stampIds) {
    if (props.visitedStampIds.has(id)) collected++;
  }
  const percent = Math.round((collected / total) * 100);
  return { collected, total, percent, isComplete: collected === total };
}
</script>

<template>
  <div
    v-if="isOpen"
    class="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200"
    style="padding-top: calc(env(safe-area-inset-top, 0px) + 0.75rem); padding-bottom: calc(env(safe-area-inset-bottom, 0px) + 0.75rem);"
    role="dialog"
    aria-modal="true"
    aria-labelledby="rallies-modal-title"
  >
    <div
      class="relative w-full max-w-2xl max-h-[90vh] flex flex-col rounded-3xl shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200 text-slate-100"
      style="background: var(--m3-surface-elevated, #162720); border: 1px solid var(--m3-border, #334155); box-shadow: 0 20px 50px rgba(0,0,0,0.7), 0 0 30px var(--m3-glow-subtle, transparent);"
      @click.stop
    >
      <!-- Header -->
      <div
        class="flex items-center justify-between px-5 py-4 border-b"
        style="background: var(--m3-surface-container, #0f1d18); border-color: var(--m3-border-subtle, #334155);"
      >
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-amber-500 to-rose-500 flex items-center justify-center text-white shadow-md shadow-rose-900/40">
            <Flag class="w-5 h-5 fill-white/20" />
          </div>
          <div>
            <h2 id="rallies-modal-title" class="text-lg font-bold text-white leading-tight flex items-center gap-2">
              <span>Stamp Rallies & Circuits</span>
              <span class="text-xs px-2 py-0.5 rounded-full bg-rose-500/20 text-rose-300 border border-rose-500/30 font-semibold font-serif">
                スタンプラリー
              </span>
            </h2>
            <p class="text-xs text-slate-400">Temporary campaigns, railway circuits & commemorative anime rallies</p>
          </div>
        </div>

        <button
          type="button"
          @click="$emit('close')"
          class="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-full transition-colors"
          aria-label="Close rallies modal"
        >
          <X class="w-5 h-5" />
        </button>
      </div>

      <!-- Tab Switcher -->
      <div
        class="flex items-center px-5 py-2.5 gap-2 border-b text-xs font-semibold"
        style="background: var(--m3-surface-container-low, #0c1814); border-color: var(--m3-border-subtle, #334155);"
      >
        <button
          type="button"
          @click="activeTab = 'active'"
          :class="[
            'px-3 py-1.5 rounded-full transition-all flex items-center gap-1.5',
            activeTab === 'active'
              ? 'bg-rose-600 text-white shadow-md shadow-rose-900/30'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
          ]"
        >
          <Sparkles class="w-3.5 h-3.5" />
          <span>Active Rallies</span>
          <span class="text-[10px] px-1.5 py-0.2 rounded-full font-mono font-bold bg-white/20">
            {{ classifiedRallies.active.length }}
          </span>
        </button>

        <button
          type="button"
          @click="activeTab = 'upcoming'"
          :class="[
            'px-3 py-1.5 rounded-full transition-all flex items-center gap-1.5',
            activeTab === 'upcoming'
              ? 'bg-amber-600 text-white shadow-md shadow-amber-900/30'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
          ]"
        >
          <Calendar class="w-3.5 h-3.5" />
          <span>Upcoming</span>
          <span class="text-[10px] px-1.5 py-0.2 rounded-full font-mono font-bold bg-white/20">
            {{ classifiedRallies.upcoming.length }}
          </span>
        </button>

        <button
          type="button"
          @click="activeTab = 'archived'"
          :class="[
            'px-3 py-1.5 rounded-full transition-all flex items-center gap-1.5',
            activeTab === 'archived'
              ? 'bg-slate-700 text-white shadow-md'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
          ]"
        >
          <span>Archived & Past</span>
          <span class="text-[10px] px-1.5 py-0.2 rounded-full font-mono font-bold bg-white/20">
            {{ classifiedRallies.archived.length }}
          </span>
        </button>
      </div>

      <!-- Active Focus Notice (if a rally is currently in focus) -->
      <div
        v-if="activeRallyId"
        class="px-5 py-2.5 bg-rose-950/60 border-b border-rose-900/50 flex items-center justify-between text-xs"
      >
        <div class="flex items-center gap-2 text-rose-300">
          <Compass class="w-4 h-4 animate-spin-slow" />
          <span>A rally circuit is currently focused on the map.</span>
        </div>
        <button
          type="button"
          @click="$emit('exitRallyFocus')"
          class="px-2.5 py-1 rounded-lg bg-rose-800/50 hover:bg-rose-800 text-rose-200 text-xs font-semibold transition-colors"
        >
          Exit Rally Mode
        </button>
      </div>

      <!-- Rallies Cards List -->
      <div class="flex-1 overflow-y-auto p-4 sm:p-5 space-y-4">
        <div v-if="currentRallies.length === 0" class="text-center py-12 text-slate-400 space-y-2">
          <Flag class="w-10 h-10 mx-auto text-slate-600 opacity-60" />
          <p class="text-sm font-medium">No rallies in this category right now.</p>
        </div>

        <div
          v-for="rally in currentRallies"
          :key="rally.id"
          class="rounded-2xl border overflow-hidden shadow-lg transition-all"
          :style="{
            background: activeRallyId === rally.id ? 'var(--m3-surface-container, #13241d)' : 'var(--m3-surface-container, #0f1d18)',
            borderColor: activeRallyId === rally.id ? '#f43f5e' : 'var(--m3-border-subtle, #334155)',
            boxShadow: activeRallyId === rally.id ? '0 0 20px rgba(244,63,94,0.2)' : 'none'
          }"
        >
          <!-- Rally Card Header Gradient -->
          <div
            :class="[
              'px-4 py-3 bg-gradient-to-r text-white flex items-center justify-between',
              rally.bannerGradient || 'from-rose-600 via-amber-600 to-indigo-700'
            ]"
          >
            <div class="flex items-center gap-2 min-w-0">
              <Flag class="w-4 h-4 flex-shrink-0" />
              <span class="text-xs font-bold uppercase tracking-wider truncate">
                {{ rally.organizer }}
              </span>
            </div>

            <!-- Status Pill -->
            <span
              :class="[
                'text-[10px] font-bold px-2 py-0.5 rounded-full border backdrop-blur-xs',
                getRallyStatus(rally).badgeClass
              ]"
            >
              {{ getRallyStatus(rally).label }}
            </span>
          </div>

          <!-- Body -->
          <div class="p-4 space-y-3">
            <div>
              <div class="flex items-start justify-between gap-2">
                <h3 class="text-base font-bold text-white leading-tight">
                  {{ rally.title }}
                </h3>
              </div>
              <p class="text-xs text-rose-300/80 font-serif mt-0.5">
                {{ rally.titleJa }}
              </p>
            </div>

            <p class="text-xs text-slate-300 leading-relaxed">
              {{ rally.description }}
            </p>

            <!-- Valid Dates & Reward -->
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
              <div class="flex items-center gap-2 p-2 rounded-xl bg-slate-900/60 border border-slate-800 text-slate-300">
                <Calendar class="w-4 h-4 text-slate-400 flex-shrink-0" />
                <div class="truncate">
                  <span class="text-[10px] text-slate-400 block">Valid Period</span>
                  <span class="font-mono text-[11px]">{{ rally.validFrom }} ~ {{ rally.validUntil }}</span>
                </div>
              </div>

              <div
                v-if="rally.reward"
                class="flex items-center gap-2 p-2 rounded-xl bg-amber-950/40 border border-amber-800/40 text-amber-200"
              >
                <Gift class="w-4 h-4 text-amber-400 flex-shrink-0" />
                <div class="truncate">
                  <span class="text-[10px] text-amber-400/80 block">Completion Reward</span>
                  <span class="text-[11px] font-semibold truncate">{{ rally.reward }}</span>
                </div>
              </div>
            </div>

            <!-- Progress Bar -->
            <div class="space-y-1.5 pt-1">
              <div class="flex items-center justify-between text-xs">
                <span class="text-slate-400 flex items-center gap-1.5">
                  <Trophy
                    v-if="getRallyProgress(rally).isComplete"
                    class="w-3.5 h-3.5 text-amber-400 fill-amber-400"
                  />
                  <span>Circuit Progress</span>
                </span>
                <span class="font-bold text-white font-mono">
                  {{ getRallyProgress(rally).collected }} / {{ getRallyProgress(rally).total }}
                  <span class="text-slate-400 font-normal">({{ getRallyProgress(rally).percent }}%)</span>
                </span>
              </div>

              <div class="w-full h-2 rounded-full bg-slate-900 border border-slate-800 overflow-hidden">
                <div
                  class="h-full rounded-full transition-all duration-500"
                  :class="getRallyProgress(rally).isComplete ? 'bg-amber-400' : 'bg-gradient-to-r from-rose-500 to-amber-500'"
                  :style="{ width: `${getRallyProgress(rally).percent}%` }"
                />
              </div>
            </div>

            <!-- Station Stamps Preview (Collapsible / Chips) -->
            <div class="space-y-1.5 pt-1">
              <span class="text-[11px] font-medium text-slate-400 block">
                Rally Stations ({{ rally.stampIds.length }} spots):
              </span>
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
                <button
                  v-for="sid in rally.stampIds"
                  :key="sid"
                  type="button"
                  @click="stampMap.get(sid) && $emit('selectStamp', stampMap.get(sid)!)"
                  class="flex items-center gap-2 p-1.5 rounded-lg bg-slate-900/50 hover:bg-slate-800/80 border border-slate-800 text-left transition-colors group"
                >
                  <!-- Stamp Image Thumbnail or Placeholder -->
                  <div class="w-7 h-7 rounded-md overflow-hidden bg-slate-800 border border-slate-700 flex-shrink-0 flex items-center justify-center">
                    <img
                      v-if="stampMap.get(sid)?.imageUrl"
                      :src="stampMap.get(sid)!.imageUrl"
                      :alt="stampMap.get(sid)!.name"
                      class="w-full h-full object-cover"
                      loading="lazy"
                    />
                    <Flag v-else class="w-3.5 h-3.5 text-slate-400" />
                  </div>

                  <div class="min-w-0 flex-1">
                    <div class="text-[11px] font-semibold text-slate-200 truncate group-hover:text-rose-400">
                      {{ stampMap.get(sid)?.name || sid }}
                    </div>
                    <div class="text-[9px] text-slate-400 truncate font-serif">
                      {{ stampMap.get(sid)?.name_ja }}
                    </div>
                  </div>

                  <div class="flex-shrink-0 pr-1">
                    <CheckCircle2
                      v-if="visitedStampIds.has(sid)"
                      class="w-4 h-4 text-emerald-400 fill-emerald-950/80"
                    />
                    <div v-else class="w-2 h-2 rounded-full bg-slate-700" />
                  </div>
                </button>
              </div>
            </div>

            <!-- Card Actions -->
            <div class="pt-2 flex items-center justify-end gap-2 border-t border-slate-800/80">
              <button
                v-if="activeRallyId === rally.id"
                type="button"
                @click="$emit('exitRallyFocus')"
                class="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-bold transition-all"
              >
                Exit Rally Mode
              </button>

              <button
                type="button"
                @click="$emit('selectRally', rally)"
                :class="[
                  'px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-all shadow-md',
                  activeRallyId === rally.id
                    ? 'bg-rose-600 text-white shadow-rose-900/40 ring-2 ring-rose-400'
                    : 'bg-gradient-to-r from-rose-600 to-amber-600 hover:from-rose-500 hover:to-amber-500 text-white shadow-rose-950/50'
                ]"
              >
                <Compass class="w-3.5 h-3.5" />
                <span>{{ activeRallyId === rally.id ? 'Currently Focused on Map' : 'Focus Rally on Map' }}</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
