<script setup lang="ts">
import { ref } from 'vue';
import { X, Languages, Copy, Check, MessageSquare, MapPin } from 'lucide-vue-next';
import type { Stamp } from '../types/stamp';
import { CATEGORIES } from '../constants/categories';

const props = defineProps<{
  isOpen: boolean;
  stamp: Stamp | null;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
}>();

const hasCopied = ref(false);

const mainPhraseJa = 'すみません、記念スタンプを押したいのですが、どこにありますか？';
const mainPhraseRomaji = 'Sumimasen, kinen sutanpu o oshitai no desu ga, doko ni arimasu ka?';
const mainPhraseDe = 'Entschuldigung, ich würde gerne den Gedenkstempel stempeln. Wo befindet sich dieser?';

const behindCounterPhraseJa = 'スタンプを出していただけますでしょうか。';
const behindCounterPhraseRomaji = 'Sutanpu o dashite itadakemasu deshō ka?';
const behindCounterPhraseDe = 'Könnten Sie mir den Stempel bitte herausgeben?';

function copyFullText() {
  if (!props.stamp) return;
  const isBehindCounter = props.stamp.stampLocation.includes('駅員に依頼') || props.stamp.stampLocation.includes('Ask station staff');
  let text = `${mainPhraseJa}\n\n● 探しているスタンプ:\n${props.stamp.name_ja} (${props.stamp.name})\n● 設置場所目安:\n${props.stamp.stampLocation}`;
  if (isBehindCounter) {
    text += `\n\n${behindCounterPhraseJa}`;
  }
  navigator.clipboard.writeText(text);
  hasCopied.value = true;
  setTimeout(() => {
    hasCopied.value = false;
  }, 2500);
}
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
        v-if="isOpen && stamp"
        class="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-slate-950/80 backdrop-blur-md overflow-y-auto"
        role="dialog"
        aria-modal="true"
        aria-labelledby="ask-staff-title"
        @click.self="$emit('close')"
      >
        <div
          class="relative w-full max-w-lg rounded-3xl shadow-2xl overflow-hidden my-auto animate-in fade-in zoom-in-95 duration-200"
          style="background: var(--m3-surface-elevated, #162720); border: 2px solid var(--m3-border, rgba(245, 158, 11, 0.6)); box-shadow: 0 20px 50px rgba(0,0,0,0.7), 0 0 30px var(--m3-glow-subtle, transparent);"
        >
          <!-- Top Bar -->
          <div class="px-5 py-3.5 bg-gradient-to-r from-amber-600 via-amber-500 to-rose-600 text-slate-950 flex items-center justify-between">
            <div class="flex items-center gap-2">
              <Languages class="w-5 h-5 flex-shrink-0" />
              <div>
                <h3 id="ask-staff-title" class="font-extrabold text-sm sm:text-base leading-tight tracking-wide">
                  Show to Staff (スタッフに見せる画面)
                </h3>
                <p class="text-[11px] font-medium opacity-90">
                  Hold this screen up to station or shop staff in Japan
                </p>
              </div>
            </div>
            <button
              type="button"
              @click="$emit('close')"
              class="p-1.5 rounded-full bg-black/15 hover:bg-black/25 text-slate-950 transition-colors"
              title="Close modal"
              aria-label="Close modal"
            >
              <X class="w-5 h-5" />
            </button>
          </div>

          <!-- Main Flashcard Content -->
          <div class="p-5 space-y-4">
            <!-- Giant Japanese Question Box (High Contrast for showing across counter) -->
            <div class="bg-white rounded-2xl p-5 border-2 border-slate-300 shadow-inner text-slate-950">
              <div class="flex items-center gap-1.5 text-xs font-bold text-red-600 uppercase tracking-widest mb-2 font-mono">
                <MessageSquare class="w-4 h-4" />
                <span>Polite Inquiry (お尋ね)</span>
              </div>
              <p class="text-xl sm:text-2xl font-black font-serif leading-snug tracking-tight text-slate-900">
                「{{ mainPhraseJa }}」
              </p>
              
              <!-- Romaji & German translation for traveler -->
              <div class="mt-3 pt-3 border-t border-slate-200 space-y-1 text-xs text-slate-600">
                <p class="font-mono text-slate-700 font-semibold italic">
                  "{{ mainPhraseRomaji }}"
                </p>
                <p class="text-slate-500">
                  🇩🇪 {{ mainPhraseDe }}
                </p>
              </div>
            </div>

            <!-- Specific Target Stamp Details -->
            <div class="bg-slate-800/90 rounded-2xl p-4 border border-slate-700/80 space-y-2.5">
              <div class="flex items-center justify-between text-xs">
                <span class="text-slate-400 font-medium">Looking for this stamp (探している印):</span>
                <span
                  v-if="CATEGORIES[stamp.category]"
                  :class="['text-[11px] px-2 py-0.5 rounded-md font-bold border', CATEGORIES[stamp.category].badgeClass]"
                >
                  {{ CATEGORIES[stamp.category].labelJa }} ({{ CATEGORIES[stamp.category].label }})
                </span>
              </div>

              <!-- Stamp Name in Big Japanese -->
              <div class="bg-slate-900/90 rounded-xl p-3 border border-slate-700 flex items-center gap-3">
                <div v-if="stamp.imageUrl" class="w-12 h-12 flex-shrink-0 bg-white rounded-lg p-1 border border-slate-600 flex items-center justify-center overflow-hidden">
                  <img :src="stamp.imageUrl" :alt="stamp.name" class="w-full h-full object-contain" />
                </div>
                <div>
                  <div class="text-base sm:text-lg font-bold text-white font-serif leading-tight">
                    {{ stamp.name_ja }}
                  </div>
                  <div class="text-xs text-slate-300 font-medium mt-0.5">
                    {{ stamp.name }}
                  </div>
                </div>
              </div>

              <!-- Known Expected Location (設置場所目安) -->
              <div class="bg-amber-950/20 border border-amber-600/30 rounded-xl p-3 text-xs text-amber-200">
                <div class="flex items-center gap-1.5 font-bold text-amber-400 mb-1">
                  <MapPin class="w-3.5 h-3.5" />
                  <span>Expected Desk (設置場所の目安):</span>
                </div>
                <p class="leading-relaxed">
                  {{ stamp.stampLocation }}
                </p>
              </div>
            </div>

            <!-- Special Box for Behind-the-Counter / Staff Request -->
            <div
              v-if="stamp.stampLocation.includes('駅員に依頼') || stamp.stampLocation.includes('Ask station staff') || stamp.stampLocation.includes('窓口')"
              class="bg-rose-950/30 border border-rose-500/40 rounded-2xl p-4 text-xs"
            >
              <div class="text-rose-300 font-bold mb-1 flex items-center gap-1.5">
                <span>⚠️ Behind Counter Note (スタンプの取り出し):</span>
              </div>
              <p class="text-base font-bold text-rose-100 font-serif leading-snug">
                「{{ behindCounterPhraseJa }}」
              </p>
              <p class="font-mono text-[11px] text-rose-300 italic mt-1">
                "{{ behindCounterPhraseRomaji }}"
              </p>
              <p class="text-[11px] text-slate-400 mt-0.5">
                🇩🇪 {{ behindCounterPhraseDe }}
              </p>
            </div>
          </div>

          <!-- Bottom Action Buttons -->
          <div class="px-5 py-3.5 bg-slate-950/90 border-t border-slate-800 flex items-center justify-between gap-3">
            <button
              type="button"
              @click="copyFullText"
              class="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 border border-slate-700 transition-colors active:scale-95"
            >
              <component :is="hasCopied ? Check : Copy" :class="['w-4 h-4', hasCopied ? 'text-emerald-400' : 'text-slate-400']" />
              <span>{{ hasCopied ? 'Copied to Clipboard!' : 'Copy Japanese Text' }}</span>
            </button>

            <button
              type="button"
              @click="$emit('close')"
              class="px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs shadow-md transition-colors active:scale-95"
            >
              Done / 閉じる
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
