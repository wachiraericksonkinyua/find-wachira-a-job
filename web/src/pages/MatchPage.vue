<script setup>
import Match from '../components/Match.vue'
import Interrogate from '../components/Interrogate.vue'
</script>

<template>
  <div class="page-shell">
    <header class="page-header">
      <p class="page-kicker text-[#19E3FF]">RAG + LLM VERDICTS</p>
      <h1 class="page-title">MATCH ENGINE & INTERROGATOR</h1>
      <p class="page-copy">
        Paste a job description to retrieve real project evidence, score the fit,
        and stream a grounded verdict. No invented employers, metrics, or skills.
      </p>
    </header>
    <Match />
    <Interrogate />
  </div>
</template>
