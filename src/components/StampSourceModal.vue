<script setup lang="ts">
import { computed } from 'vue';
import type { Stamp } from '../types/stamp';
import { getStampSourceDetails } from '../utils/source';
import {
  X,
  ShieldCheck,
  ExternalLink,
  MapPin,
  Building2,
  FileCheck2,
  Info,
} from 'lucide-vue-next';

const props = defineProps<{
  isOpen: boolean;
  stamp: Stamp | null;
}>();

defineEmits<{
  (e: 'close'): void;
}>();

const sourceDetails = computed(() => {
  if (!props.stamp) return null;
  return getStampSourceDetails(props.stamp);
});
</script>

<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition-opacity duration-200 ease-out"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition-opacity duration-150 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="isOpen && stamp && sourceDetails"
        class="fixed inset-0 z-[120] flex items-center justify-center p-3 sm:p-4 bg-slate-950/80 backdrop-blur-md pointer-events-auto overflow-y-auto"
        role="dialog"
        aria-modal="true"
        aria-labelledby="source-modal-title"
        @click.self="$emit('close')"
      >
        <div
          class="relative w-full max-w-lg rounded-3xl shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200 text-slate-100 border"
          style="background: var(--m3-surface-elevated, #162720); border-color: var(--m3-border, #334155); box-shadow: 0 20px 50px rgba(0,0,0,0.7), 0 0 30px var(--m3-glow-subtle, transparent);"
          @click.stop
        >
          <!-- Header -->
          <div
            class="flex items-center justify-between px-5 py-4 border-b"
            style="background: var(--m3-surface-container, #0f1d18); border-color: var(--m3-border-subtle, #334155);"
          >
            <div class="flex items-center gap-2.5">
              <div
                class="w-9 h-9 rounded-xl flex items-center justify-center border"
                style="background: var(--m3-badge-bg, rgba(16, 185, 129, 0.2)); border-color: var(--m3-border-subtle); color: var(--m3-primary);"
              >
                <Info class="w-5 h-5" />
              </div>
              <div>
                <h3 id="source-modal-title" class="text-sm sm:text-base font-bold text-white flex items-center gap-2">
                  Stamp Data Source
                  <span class="text-xs font-normal text-slate-400 font-serif">データ出典・検証</span>
                </h3>
                <p class="text-xs text-slate-400">Authentizität & Herkunftsnachweis</p>
              </div>
            </div>

            <button
              type="button"
              @click="$emit('close')"
              class="p-2 text-slate-400 hover:text-white rounded-full hover:bg-white/10 transition-colors"
              aria-label="Close source info"
            >
              <X class="w-5 h-5" />
            </button>
          </div>

          <!-- Content Body -->
          <div class="p-5 space-y-4 max-h-[75vh] overflow-y-auto">
            <!-- Stamp Overview Pill -->
            <div
              class="rounded-2xl p-3.5 border flex items-center justify-between gap-3"
              style="background: var(--m3-surface-container, #0f1d18); border-color: var(--m3-border-subtle, #334155);"
            >
              <div>
                <div class="text-[11px] font-bold text-emerald-400 uppercase tracking-wider flex items-center gap-1.5 mb-0.5">
                  <ShieldCheck class="w-3.5 h-3.5" />
                  <span>{{ sourceDetails.verificationStatus }}</span>
                </div>
                <h4 class="font-bold text-white text-sm sm:text-base">{{ stamp.name }}</h4>
                <div class="text-xs text-slate-300 font-serif mt-0.5">{{ stamp.name_ja }} ({{ stamp.city }}, {{ stamp.prefecture }})</div>
              </div>
              <div class="text-right text-[11px] text-slate-400 flex-shrink-0">
                <span class="font-mono bg-black/40 px-2 py-0.5 rounded border border-slate-700/60">{{ stamp.id }}</span>
              </div>
            </div>

            <!-- Primary Authority & Registry Card -->
            <div
              class="rounded-2xl p-4 border space-y-3"
              style="background: var(--m3-surface-container, #0f1d18); border-color: var(--m3-border-subtle, #334155);"
            >
              <div class="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-300">
                <Building2 class="w-4 h-4 text-emerald-400" />
                <span>Primary Authority & Registry (Herausgeber)</span>
              </div>

              <div class="space-y-2 text-xs">
                <div>
                  <span class="text-slate-400">Verantwortliche Stelle / Betreiber:</span>
                  <div class="font-semibold text-slate-100 text-sm mt-0.5">{{ sourceDetails.authority }}</div>
                </div>

                <div>
                  <span class="text-slate-400">Offizielle Registrierung:</span>
                  <div class="text-slate-200 mt-0.5 font-medium">{{ sourceDetails.registry }}</div>
                </div>

                <div>
                  <span class="text-slate-400">Referenz-Katalog:</span>
                  <div class="text-slate-200 mt-0.5 font-medium">{{ sourceDetails.sourceName }}</div>
                </div>
              </div>

              <!-- Direct Source URL Action Button -->
              <div v-if="sourceDetails.sourceUrl" class="pt-1">
                <a
                  :href="sourceDetails.sourceUrl"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="inline-flex items-center justify-center gap-2 w-full py-2 px-3 rounded-xl font-bold text-xs text-white transition-all shadow-md active:scale-95"
                  style="background: var(--m3-primary); box-shadow: 0 4px 14px var(--m3-glow-subtle);"
                >
                  <ExternalLink class="w-3.5 h-3.5" />
                  <span>Offizielle Quelle / Katalogeintrag öffnen</span>
                </a>
              </div>
            </div>

            <!-- Verification & Desk Location Details -->
            <div
              class="rounded-2xl p-4 border space-y-2.5"
              style="background: var(--m3-surface-container, #0f1d18); border-color: var(--m3-border-subtle, #334155);"
            >
              <div class="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-amber-300">
                <FileCheck2 class="w-4 h-4 text-amber-400" />
                <span>Standort-Abgleich & Feldprüfung</span>
              </div>

              <p class="text-xs text-slate-200 leading-relaxed">
                {{ sourceDetails.verificationNotesDe }}
              </p>

              <p class="text-[11px] text-slate-400 leading-relaxed italic border-t border-slate-800/80 pt-2">
                "{{ sourceDetails.verificationNotesEn }}"
              </p>
            </div>

            <!-- Geocoding & Mapping Verification -->
            <div
              class="rounded-2xl p-4 border space-y-2"
              style="background: var(--m3-surface-container, #0f1d18); border-color: var(--m3-border-subtle, #334155);"
            >
              <div class="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-sky-300">
                <MapPin class="w-4 h-4 text-sky-400" />
                <span>Geodaten & Koordinatenpräzision</span>
              </div>

              <div class="flex items-center justify-between text-xs text-slate-300">
                <span>Quelle: {{ sourceDetails.geocoding }}</span>
                <span class="font-mono text-[11px] text-sky-300 bg-sky-950/60 px-2 py-0.5 rounded border border-sky-800/50">
                  {{ stamp.coordinates[1].toFixed(5) }}, {{ stamp.coordinates[0].toFixed(5) }}
                </span>
              </div>
              <div class="text-[11px] text-slate-400 flex items-center justify-between pt-1">
                <span>Stand der Datenprüfung:</span>
                <span class="font-semibold text-slate-300">{{ sourceDetails.lastVerified }}</span>
              </div>
            </div>
          </div>

          <!-- Footer -->
          <div
            class="px-5 py-3 border-t flex items-center justify-between gap-3 text-xs"
            style="background: var(--m3-surface-container, #0f1d18); border-color: var(--m3-border-subtle, #334155);"
          >
            <span class="text-slate-400 text-[11px]">STAMPU Japan Verified Registry</span>
            <button
              type="button"
              @click="$emit('close')"
              class="px-4 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold transition-all active:scale-95"
            >
              Schließen
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
