# Web — Find Wachira a Job

Vue 3 + Vite frontend for the portfolio API in `../backend`.

## Scripts

```bash
npm install
npm run dev            # Vite dev server
npm run build          # production build
npm run test           # run the Vitest suite once
npm run test:watch     # watch mode
npm run test:coverage  # coverage report in ./coverage
```

## Tests

Component and store tests live in `tests/` and run under Vitest + jsdom with
`@vue/test-utils`. `vitest.config.js` registers the `@` alias to `src/` and
loads `tests/setup.js`, which stubs the browser APIs jsdom lacks and the global
`fetch`.

Covered today:

- `tests/stores/pet.test.js` — Pinia pet store defaults, state application,
  success/error handling for `fetchState()` and `interact()`.
- `tests/components/Match.test.js` — form validation, presets, POST payload,
  loading state, score/verdict/skill/gap/citation rendering, error paths.
- `tests/components/Interrogate.test.js` — validation, presets, SSE token
  streaming, stop control, and error handling.
- `tests/components/ExcuseBuster.test.js` — loading excuses, selection,
  debounced streaming response, and error handling.

Network calls are mocked at the `fetch` boundary; no backend is required.
