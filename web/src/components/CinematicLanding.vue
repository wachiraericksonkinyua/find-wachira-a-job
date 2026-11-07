<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

const slides = [
  {
    id: 'identity',
    code: 'BOOT 01/04',
    title: 'IDENTITY // VERIFIED',
    lines: [
      '> OPERATOR: WACHIRA ERICKSON KINYUA',
      '> ROLE: AI + FULL-STACK ENGINEER',
      '> BASE: NAIROBI, KENYA // UTC+3',
      '> STATUS: AVAILABLE FOR INTERNSHIPS & JUNIOR ROLES',
    ],
    footer: 'Loading human credentials... OK',
  },
  {
    id: 'workspace',
    code: 'BOOT 02/04',
    title: 'WORKSPACE // ONLINE',
    lines: [
      '> BACKEND: FASTAPI + POSTGRESQL + PGVECTOR',
      '> FRONTEND: VUE 3 + PINIA + VITE',
      '> AI LAYER: RAG RETRIEVAL + STREAMED SSE',
      '> SECURITY: OWASP LLM01 DELIMITERS + RATE LIMITS',
    ],
    footer: 'Desk scene mounted. Hotspots armed.',
  },
  {
    id: 'security',
    code: 'BOOT 03/04',
    title: 'SECURITY // HARDENED',
    lines: [
      '> TIMING-SAFE ADMIN AUTH',
      '> UNTRUSTED INPUT DELIMITERS',
      '> RED-TEAM CTF: 4 DEFENSE LAYERS',
      '> ZERO REAL KEYS INSIDE THE SANDBOX',
    ],
    footer: 'Threat model loaded. Send it.',
  },
  {
    id: 'mission',
    code: 'BOOT 04/04',
    title: 'MISSION // HIRE WACHIRA',
    lines: [
      '> READ THE CASE STUDIES',
      '> RUN THE RAG MATCH ENGINE',
      '> TRY TO JAILBREAK THE MONKEY',
      '> BOOK THE INTERVIEW',
    ],
    footer: 'Boot complete. Pick a hotspot or scroll.',
  },
]

const slideIndex = ref(0)
const reducedMotion = ref(false)
const paused = ref(false)
let timer = null

const currentSlide = computed(() => slides[slideIndex.value])
const isFirstSlide = computed(() => slideIndex.value === 0)
const isLastSlide = computed(() => slideIndex.value === slides.length - 1)

function prefersReducedMotion() {
  return (
    typeof window !== 'undefined' &&
    typeof window.matchMedia === 'function' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches
  )
}

function nextSlide() {
  slideIndex.value = (slideIndex.value + 1) % slides.length
}

function previousSlide() {
  slideIndex.value = (slideIndex.value - 1 + slides.length) % slides.length
}

function jumpToSlide(index) {
  slideIndex.value = index
}

function goTo(target) {
  if (typeof document === 'undefined') return
  const element = document.getElementById(target)
  if (!element) return
  element.scrollIntoView({
    behavior: reducedMotion.value ? 'auto' : 'smooth',
    block: 'start',
  })
}

function startTimer() {
  if (reducedMotion.value || typeof window === 'undefined') return
  window.clearInterval(timer)
  timer = window.setInterval(() => {
    if (!paused.value) nextSlide()
  }, 7000)
}

function pauseTour() {
  paused.value = true
}

function resumeTour() {
  paused.value = false
}

onMounted(() => {
  reducedMotion.value = prefersReducedMotion()
  startTimer()
})

onUnmounted(() => {
  if (typeof window !== 'undefined') window.clearInterval(timer)
})
</script>

<template>
  <section id="boot" class="mb-8 scroll-mt-24" aria-label="Cinematic landing scene">
    <div class="panel overflow-hidden">
      <div class="grid lg:grid-cols-[0.95fr_1.05fr]">
        <!-- Four-slide secure boot terminal -->
        <div
          class="relative p-5 md:p-7 border-b lg:border-b-0 lg:border-r border-[#22345E] bg-[#070D1B]"
          tabindex="0"
          @keydown.left.prevent="previousSlide"
          @keydown.right.prevent="nextSlide"
          @mouseenter="pauseTour"
          @mouseleave="resumeTour"
          @focusin="pauseTour"
          @focusout="resumeTour"
        >
          <div class="flex items-center justify-between gap-3 mb-4">
            <p class="font-mono-tech text-[10px] text-[#3DF5A6]">
              SYSTEM // SECURE_BOOT_v4.1
            </p>
            <span class="font-mono-tech text-[10px] text-[#8FA6C8]">
              {{ currentSlide.code }}
            </span>
          </div>

          <div class="flex gap-1.5 mb-5" aria-hidden="true">
            <span
              v-for="(slide, index) in slides"
              :key="slide.id"
              class="h-1 flex-1 transition-colors"
              :class="index <= slideIndex ? 'bg-[#3DF5A6]' : 'bg-[#22345E]'"
            />
          </div>

          <h1 class="font-orbitron text-2xl md:text-3xl font-black leading-tight text-[#E6F1FF]">
            {{ currentSlide.title }}
          </h1>

          <div class="mt-4 min-h-[132px] border border-[#22345E] bg-[#02060F] p-3">
            <p
              v-for="line in currentSlide.lines"
              :key="line"
              class="font-mono-tech text-[11px] md:text-xs leading-relaxed text-[#8FA6C8]"
            >
              <span class="text-[#3DF5A6]">{{ line.slice(0, 1) }}</span>
              {{ line.slice(1) }}
            </p>
            <p class="mt-2 font-mono-tech text-[10px] text-[#FFC857]">
              {{ currentSlide.footer }}<span class="boot-cursor">_</span>
            </p>
          </div>

          <div class="mt-4 flex flex-wrap items-center justify-between gap-3">
            <div class="flex gap-2">
              <button
                type="button"
                @click="previousSlide"
                :disabled="isFirstSlide"
                class="px-3 py-1.5 border border-[#22345E] bg-[#0D1630] font-mono-tech text-[10px] text-[#E6F1FF] hover:border-[#19E3FF] cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
              >
                ← PREV
              </button>
              <button
                type="button"
                @click="nextSlide"
                :disabled="isLastSlide"
                class="px-3 py-1.5 border border-[#19E3FF] bg-[#0D2230] font-mono-tech text-[10px] text-[#19E3FF] hover:bg-[#19E3FF] hover:text-[#06101F] cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
              >
                NEXT →
              </button>
            </div>
            <div class="flex items-center gap-1.5" aria-label="Slides">
              <button
                v-for="(slide, index) in slides"
                :key="slide.id"
                type="button"
                @click="jumpToSlide(index)"
                :aria-label="`Go to slide ${index + 1}: ${slide.title}`"
                :aria-current="index === slideIndex ? 'true' : undefined"
                class="h-2.5 w-2.5 border cursor-pointer"
                :class="
                  index === slideIndex
                    ? 'bg-[#3DF5A6] border-[#3DF5A6]'
                    : 'bg-transparent border-[#8FA6C8]/50 hover:border-[#3DF5A6]'
                "
              />
            </div>
          </div>
        </div>

        <!-- 2.5D desk & wall scene with interactive hotspots -->
        <div class="scene-shell relative min-h-[380px] overflow-hidden bg-[#050914]">
          <div class="scene-glow" aria-hidden="true" />
          <div class="scene-grid" aria-hidden="true" />

          <div class="room">
            <div class="wall">
              <div class="wall-panel wall-panel-a">
                <span class="font-pixel text-[8px] text-[#19E3FF]">CASE FILES</span>
                <span class="font-mono-tech text-[9px] text-[#8FA6C8]">SHIPPED WORK</span>
              </div>
              <div class="wall-panel wall-panel-b">
                <span class="font-pixel text-[8px] text-[#FF4D8D]">/LAB</span>
                <span class="font-mono-tech text-[9px] text-[#8FA6C8]">RED TEAM</span>
              </div>
              <div class="wall-panel wall-panel-c">
                <span class="font-pixel text-[8px] text-[#3DF5A6]">SECURE</span>
                <span class="font-mono-tech text-[9px] text-[#8FA6C8]">LLM01</span>
              </div>

              <button
                type="button"
                class="hotspot hotspot-projects"
                aria-label="Jump to case studies"
                @click="goTo('projects')"
              >
                <span class="hotspot-dot" aria-hidden="true" />
                <span>CASE_FILES</span>
              </button>

              <button
                type="button"
                class="hotspot hotspot-lab"
                aria-label="Jump to the red team lab"
                @click="goTo('lab')"
              >
                <span class="hotspot-dot" aria-hidden="true" />
                <span>/LAB</span>
              </button>
            </div>

            <div class="floor" aria-hidden="true" />

            <div class="desk-surface" aria-hidden="true">
              <div class="desk-edge" />
            </div>

            <div class="monitor">
              <div class="monitor-screen">
                <p class="monitor-kicker">SECURE_BOOT_v4.1</p>
                <p class="monitor-line">> RAG ENGINE READY</p>
                <p class="monitor-line">> CTF LAB ARMED</p>
                <p class="monitor-line monitor-ok">> STATUS: ONLINE<span class="boot-cursor">_</span></p>
              </div>
              <div class="monitor-stand" />
            </div>

            <div class="keyboard" aria-hidden="true">
              <span v-for="key in 12" :key="key" class="key" />
            </div>

            <div class="mug" aria-hidden="true">
              <div class="mug-handle" />
              <div class="mug-steam" />
            </div>

            <button
              type="button"
              class="hotspot hotspot-book"
              aria-label="Jump to the interview booking form"
              @click="goTo('book')"
            >
              <span class="hotspot-dot" aria-hidden="true" />
              <span>BOOK_CALL</span>
            </button>

            <a
              :href="`${API_URL}/api/resume`"
              download="wachira-erickson-kinyua-resume.pdf"
              class="hotspot hotspot-resume"
              aria-label="Download Wachira's resume"
            >
              <span class="hotspot-dot" aria-hidden="true" />
              <span>RESUME.pdf</span>
            </a>
          </div>

          <div class="scanlines" aria-hidden="true" />
          <div class="scene-caption font-mono-tech text-[9px] text-[#8FA6C8]">
            <span class="text-[#3DF5A6]">●</span> HOTSPOTS: PROJECTS / LAB / BOOK / RESUME
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.scene-shell {
  perspective: 1100px;
  background:
    radial-gradient(circle at 70% 20%, rgba(25, 227, 255, 0.14), transparent 42%),
    radial-gradient(circle at 20% 70%, rgba(61, 245, 166, 0.08), transparent 40%),
    #050914;
}

.scene-glow {
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at 72% 28%, rgba(25, 227, 255, 0.16), transparent 55%);
  pointer-events: none;
}

.scene-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(34, 52, 94, 0.25) 1px, transparent 1px),
    linear-gradient(90deg, rgba(34, 52, 94, 0.25) 1px, transparent 1px);
  background-size: 28px 28px;
  mask-image: linear-gradient(to bottom, black, transparent 85%);
  pointer-events: none;
}

.room {
  position: absolute;
  inset: 6% 4% 10%;
  transform-style: preserve-3d;
  transform: rotateX(6deg) rotateY(-6deg);
}

.wall {
  position: absolute;
  inset: 0 0 42% 0;
  border: 1px solid rgba(34, 52, 94, 0.9);
  background:
    linear-gradient(180deg, rgba(16, 26, 51, 0.95), rgba(8, 14, 28, 0.95));
  box-shadow: inset 0 0 40px rgba(0, 0, 0, 0.55);
}

.wall::after {
  content: '';
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(34, 52, 94, 0.35) 1px, transparent 1px),
    linear-gradient(90deg, rgba(34, 52, 94, 0.35) 1px, transparent 1px);
  background-size: 22px 22px;
  opacity: 0.4;
}

.wall-panel {
  position: absolute;
  z-index: 2;
  display: grid;
  gap: 2px;
  padding: 6px 8px;
  border: 1px solid rgba(34, 52, 94, 0.9);
  background: rgba(5, 9, 20, 0.85);
  box-shadow: 0 0 14px rgba(25, 227, 255, 0.12);
}

.wall-panel-a {
  top: 9%;
  right: 8%;
  transform: rotate(1.5deg);
}

.wall-panel-b {
  top: 32%;
  right: 22%;
  transform: rotate(-1deg);
}

.wall-panel-c {
  top: 17%;
  left: 8%;
  transform: rotate(-2deg);
}

.floor {
  position: absolute;
  left: -10%;
  right: -10%;
  bottom: 0;
  height: 44%;
  transform-origin: top center;
  transform: rotateX(62deg);
  background:
    linear-gradient(rgba(25, 227, 255, 0.12) 1px, transparent 1px),
    linear-gradient(90deg, rgba(25, 227, 255, 0.12) 1px, transparent 1px),
    linear-gradient(180deg, rgba(8, 16, 32, 0.95), rgba(2, 6, 15, 1));
  background-size: 34px 34px, 34px 34px, 100% 100%;
  border-top: 1px solid rgba(25, 227, 255, 0.25);
}

.desk-surface {
  position: absolute;
  left: 4%;
  right: 4%;
  bottom: 17%;
  height: 19%;
  transform: translateZ(34px) rotateX(8deg);
  background: linear-gradient(180deg, #1a2947, #0d1630 70%);
  border: 1px solid #22345e;
  box-shadow: 0 18px 40px rgba(0, 0, 0, 0.55);
}

.desk-edge {
  position: absolute;
  left: 2%;
  right: 2%;
  bottom: -10px;
  height: 10px;
  background: #0a1122;
  border: 1px solid #22345e;
  border-top: none;
}

.monitor {
  position: absolute;
  z-index: 3;
  top: 21%;
  left: 17%;
  width: 48%;
  filter: drop-shadow(0 12px 26px rgba(0, 0, 0, 0.6));
}

.monitor-screen {
  position: relative;
  min-height: 112px;
  padding: 10px;
  border: 2px solid #2b4775;
  background:
    linear-gradient(180deg, rgba(25, 227, 255, 0.08), transparent 60%),
    #02060f;
  box-shadow:
    inset 0 0 24px rgba(25, 227, 255, 0.16),
    0 0 20px rgba(25, 227, 255, 0.16);
}

.monitor-kicker {
  font-family: 'Press Start 2P', monospace;
  font-size: 7px;
  color: #19e3ff;
  margin-bottom: 8px;
}

.monitor-line {
  font-family: 'Share Tech Mono', monospace;
  font-size: 10px;
  color: #8fa6c8;
  line-height: 1.55;
}

.monitor-ok {
  color: #3df5a6;
}

.monitor-stand {
  width: 34%;
  height: 16px;
  margin: 0 auto;
  background: linear-gradient(180deg, #1a2947, #0a1122);
  border: 1px solid #22345e;
  border-top: none;
}

.keyboard {
  position: absolute;
  z-index: 4;
  left: 22%;
  bottom: 29%;
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 2px;
  width: 34%;
  padding: 5px;
  transform: translateZ(40px) rotateX(14deg);
  background: #0b152c;
  border: 1px solid #2b4775;
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.5);
}

.key {
  height: 6px;
  background: #22345e;
}

.mug {
  position: absolute;
  z-index: 4;
  right: 17%;
  bottom: 29%;
  width: 26px;
  height: 30px;
  background: linear-gradient(180deg, #19e3ff, #0f7d92);
  border: 1px solid #7cecff;
  border-radius: 3px 3px 6px 6px;
  transform: translateZ(42px) rotateY(-12deg);
  box-shadow: 0 0 14px rgba(25, 227, 255, 0.3);
}

.mug-handle {
  position: absolute;
  right: -9px;
  top: 7px;
  width: 12px;
  height: 14px;
  border: 2px solid #19e3ff;
  border-left: none;
  border-radius: 0 8px 8px 0;
}

.mug-steam {
  position: absolute;
  left: 8px;
  top: -14px;
  width: 3px;
  height: 12px;
  background: linear-gradient(to top, rgba(61, 245, 166, 0.7), transparent);
  animation: steam 2.4s ease-in-out infinite;
}

.hotspot {
  position: absolute;
  z-index: 6;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 7px;
  border: 1px solid rgba(25, 227, 255, 0.8);
  background: rgba(5, 9, 20, 0.9);
  font-family: 'Share Tech Mono', monospace;
  font-size: 9px;
  letter-spacing: 0.04em;
  color: #d9f8ff;
  cursor: pointer;
  box-shadow: 0 0 12px rgba(25, 227, 255, 0.2);
  transition: transform 0.15s ease, border-color 0.15s ease, color 0.15s ease;
}

.hotspot:hover,
.hotspot:focus-visible {
  color: #06101f;
  background: #19e3ff;
  border-color: #19e3ff;
  transform: translateY(-2px);
  outline: none;
}

.hotspot-dot {
  width: 6px;
  height: 6px;
  border-radius: 999px;
  background: #3df5a6;
  box-shadow: 0 0 0 0 rgba(61, 245, 166, 0.55);
  animation: ping 2.2s ease-out infinite;
}

.hotspot-projects {
  top: 15%;
  right: 6%;
}

.hotspot-lab {
  top: 43%;
  right: 12%;
  border-color: rgba(255, 77, 141, 0.85);
}

.hotspot-lab:hover,
.hotspot-lab:focus-visible {
  background: #ff4d8d;
  border-color: #ff4d8d;
}

.hotspot-book {
  left: 10%;
  bottom: 24%;
  border-color: rgba(61, 245, 166, 0.8);
}

.hotspot-book:hover,
.hotspot-book:focus-visible {
  background: #3df5a6;
  border-color: #3df5a6;
}

.hotspot-resume {
  right: 7%;
  bottom: 6%;
}

.scanlines {
  position: absolute;
  inset: 0;
  background: repeating-linear-gradient(
    to bottom,
    rgba(255, 255, 255, 0.025) 0,
    rgba(255, 255, 255, 0.025) 1px,
    transparent 1px,
    transparent 4px
  );
  pointer-events: none;
  mix-blend-mode: screen;
}

.scene-caption {
  position: absolute;
  left: 14px;
  bottom: 10px;
  z-index: 7;
}

.boot-cursor {
  animation: blink 1.1s steps(1) infinite;
}

@keyframes blink {
  50% {
    opacity: 0;
  }
}

@keyframes ping {
  0% {
    box-shadow: 0 0 0 0 rgba(61, 245, 166, 0.55);
  }
  70% {
    box-shadow: 0 0 0 7px rgba(61, 245, 166, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(61, 245, 166, 0);
  }
}

@keyframes steam {
  0% {
    transform: translateY(0) scaleY(0.7);
    opacity: 0.2;
  }
  50% {
    opacity: 0.85;
  }
  100% {
    transform: translateY(-10px) scaleY(1.2);
    opacity: 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .boot-cursor,
  .hotspot-dot,
  .mug-steam {
    animation: none;
  }

  .hotspot {
    transition: none;
  }
}
</style>
