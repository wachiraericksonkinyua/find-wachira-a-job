<script setup>
import ApplyAssistant from '../components/ApplyAssistant.vue'
</script>

<template>
  <div class="page-shell">
    <header class="page-header">
      <p class="page-kicker text-[#FFC857]">HUMAN-IN-THE-LOOP</p>
      <h1 class="page-title">APPLY ASSISTANT & TRACKER</h1>
      <p class="page-copy">
        Analyze a public job URL or paste a JD, generate a citation-backed cover
        letter, and track the application. Drafts are copied and sent manually —
        nothing is auto-submitted.
      </p>
    </header>
    <ApplyAssistant />
  </div>
</template>
