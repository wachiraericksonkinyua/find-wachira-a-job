<script setup>
import RedTeamLab from '../components/RedTeamLab.vue'
</script>

<template>
  <div class="page-shell">
    <header class="page-header">
      <p class="page-kicker text-[#FF4D8D]">ISOLATED SECURITY PLAYGROUND</p>
      <h1 class="page-title">AI RED TEAM CTF LAB</h1>
      <p class="page-copy">
        Four prompt-injection defenses guard four fake flags. This sandbox is
        isolated from real keys, tools, and user data. Capture a flag, then claim
        a nickname-only leaderboard spot.
      </p>
    </header>
    <RedTeamLab />
  </div>
</template>
