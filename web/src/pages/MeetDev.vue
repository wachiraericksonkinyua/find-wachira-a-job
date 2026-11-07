<script setup>
const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

const stack = [
  { group: 'Backend', items: ['Python', 'FastAPI', 'PostgreSQL', 'Supabase', 'REST APIs', 'Pydantic'] },
  { group: 'Frontend', items: ['Vue 3', 'JavaScript', 'Pinia', 'Tailwind CSS', 'Vite'] },
  { group: 'AI / Data', items: ['RAG retrieval', 'LLM pipelines', 'Prompt engineering', 'Structured outputs'] },
  { group: 'Tooling', items: ['Git', 'Docker', 'Linux', 'pytest', 'GitHub Actions'] },
]

const timeline = [
  {
    when: '2022 — 2027',
    title: 'B.Sc. Information Technology',
    place: 'Karatina University',
    body: 'Final-year coursework across software engineering, databases, networking, and applied AI.',
  },
  {
    when: '2025',
    title: 'IT Intern',
    place: 'Judiciary of Kenya',
    body: 'Supported institutional ICT infrastructure, preventive maintenance, and responsive user support for court and administrative teams.',
  },
  {
    when: '2024 — Present',
    title: 'Backend & AI Engineer',
    place: 'Independent projects',
    body: 'Shipped FastAPI services, Vue interfaces, RAG pipelines, payments integrations, and security-focused portfolio features.',
  },
]

const links = [
  { label: 'GitHub', href: 'https://github.com/wachiraericksonkinyua' },
  { label: 'LinkedIn', href: 'https://www.linkedin.com/in/erickson-kinyua-28b7b2327' },
  { label: 'Email', href: 'mailto:ericksonkinyua681@gmail.com' },
]
</script>

<template>
  <div class="page-shell">
    <header class="page-header">
      <p class="page-kicker text-[#19E3FF]">MEET THE DEV</p>
      <h1 class="page-title">ERICKSON KINYUA WACHIRA</h1>
      <p class="page-copy">
        Final-year B.Sc. IT student, backend builder, AI-pipeline tinkerer, and
        the person behind this entire portfolio.
      </p>
    </header>

    <section class="grid gap-6 lg:grid-cols-[0.8fr_1.2fr] mb-12">
      <div class="panel p-6 md:p-8 text-center">
        <div class="mx-auto h-28 w-28 rounded-full border border-[#19E3FF]/60 bg-[#0D2230] flex items-center justify-center shadow-[0_0_40px_rgba(25,227,255,0.18)]">
          <span class="font-orbitron text-3xl font-black text-[#19E3FF]">EK</span>
        </div>
        <h2 class="font-orbitron text-xl font-bold mt-4">ERICKSON KINYUA WACHIRA</h2>
        <p class="font-mono-tech text-xs text-[#3DF5A6] mt-1">AI + FULL-STACK ENGINEER</p>
        <p class="text-sm text-[#A9BCD9] mt-3">
          Nairobi, Kenya · Available for internships and junior roles
        </p>
        <div class="mt-5 grid gap-2">
          <a
            v-for="link in links"
            :key="link.label"
            :href="link.href"
            target="_blank"
            rel="noopener noreferrer"
            class="btn-secondary text-center"
          >
            {{ link.label.toUpperCase() }}
          </a>
          <a :href="`${API_URL}/api/resume`" download class="btn-primary text-center">
            DOWNLOAD RESUME PDF
          </a>
        </div>
      </div>

      <div class="grid gap-6">
        <div class="panel p-6">
          <p class="page-kicker text-[#3DF5A6]">THE SHORT VERSION</p>
          <p class="text-[#D7E4F8] leading-relaxed mt-3">
            I build software that has to survive real users: typed FastAPI
            services, PostgreSQL data models, Vue interfaces with honest loading
            and error states, and LLM features that are grounded, validated, and
            rate-limited. I care about the unglamorous parts — security, tests,
            deployment, and the moment a user trusts the product.
          </p>
        </div>

        <div class="panel p-6">
          <p class="page-kicker text-[#FFC857]">CURRENTLY</p>
          <ul class="mt-3 grid gap-2 text-sm text-[#A9BCD9]">
            <li>• Finishing B.Sc. Information Technology at Karatina University (2027).</li>
            <li>• Open to backend, full-stack, and AI engineering internships.</li>
            <li>• Building RAG systems, security demos, and practical developer tools.</li>
          </ul>
        </div>
      </div>
    </section>

    <section class="mb-12">
      <h2 class="page-title text-2xl mb-4">EXPERIENCE</h2>
      <div class="grid gap-4">
        <article v-for="item in timeline" :key="item.title" class="panel p-5">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <h3 class="font-orbitron font-bold">{{ item.title }}</h3>
            <span class="font-mono-tech text-[10px] text-[#FFC857]">{{ item.when }}</span>
          </div>
          <p class="font-mono-tech text-xs text-[#19E3FF] mt-1">{{ item.place }}</p>
          <p class="text-sm text-[#A9BCD9] mt-2 leading-relaxed">{{ item.body }}</p>
        </article>
      </div>
    </section>

    <section>
      <h2 class="page-title text-2xl mb-4">STACK</h2>
      <div class="grid gap-4 md:grid-cols-2">
        <article v-for="group in stack" :key="group.group" class="panel p-5">
          <h3 class="font-mono-tech text-xs text-[#3DF5A6] mb-2">{{ group.group.toUpperCase() }}</h3>
          <div class="flex flex-wrap gap-2">
            <span
              v-for="item in group.items"
              :key="item"
              class="px-2 py-1 border border-[#22345E] bg-[#0A0F1F] font-mono-tech text-[10px] text-[#D7E4F8]"
            >
              {{ item }}
            </span>
          </div>
        </article>
      </div>
    </section>
  </div>
</template>
