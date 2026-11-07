# Module 04 — Accessibility, Web Vitals, Moderation, and XSS

**Days covered:** 33–38 (Phase 7)

## The one-sentence version

Make the interface usable without motion or a mouse, keep it fast, and treat all
user-generated content as hostile until it is sanitized, moderated, and escaped.

## Accessibility

### `prefers-reduced-motion`

Some users experience nausea or dizziness from animation. CSS should disable
non-essential motion when the operating system asks for it.

```css
@media (prefers-reduced-motion: reduce) {
  .animated-thing {
    animation: none;
  }
}
```

Repository examples:

- `web/src/style.css` → smooth scrolling disabled for reduced motion
- `web/src/components/CinematicLanding.vue` → auto-advance and hotspot motion respect the setting

### Keyboard navigation and focus

- Every interactive control must be reachable with `Tab`.
- Do not remove focus outlines without replacing them.
- Use `focus-visible:ring-*` utilities for visible focus.
- Modal dialogs should have a close button and `role="dialog"`.

### `aria-live`

Streaming text and async status messages should be announced politely:

```html
<div role="status" aria-live="polite">Draft ready for review.</div>
```

Repository examples:

- `web/src/components/ApplyAssistant.vue`
- `web/src/components/TalentBoard.vue`
- `web/src/components/RedTeamLab.vue`

## Web Vitals

Keep the first view light:

- avoid huge unoptimized images
- use system/display fonts deliberately
- lazy-load below-the-fold work where possible
- keep streamed responses small
- measure with Lighthouse and the Performance panel

Official reading:

- [web.dev: Learn Performance](https://web.dev/learn/performance)

## Moderation and data minimization

The Talent Board demonstrates a safe pattern:

1. Public submission starts as `status="pending"`.
2. An admin must approve it.
3. Public output includes only `id`, `name`, `role`, `pitch`, `link`.
4. Emails and takedown tokens are never returned.
5. Links must be `https://`.
6. Tags/control characters are stripped.
7. The submitter gets a one-time takedown token whose hash is stored.

Repository examples:

- `backend/app/board.py`
- `backend/tests/test_phase7_8.py`
- `web/src/components/TalentBoard.vue`

## XSS prevention

XSS happens when attacker-controlled text becomes executable markup. Defenses:

- escape on output; Vue's `{{ }}` does this automatically
- never use `v-html` with untrusted data
- strip HTML tags server-side where plain text is expected
- validate links and reject `javascript:` / `data:` schemes
- serve a Content-Security-Policy in production

Official reading:

- [OWASP XSS Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html)
- [MDN `prefers-reduced-motion`](https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-reduced-motion)

## Practice checklist

- [ ] Navigate the whole site with only the keyboard.
- [ ] Turn on reduced motion at the OS level and confirm the 2.5D scene stops
      auto-advancing.
- [ ] Submit `<script>alert(1)</script>` as a board pitch and verify it cannot
      execute.
- [ ] Confirm pending board entries are missing from `GET /api/board`.
- [ ] Confirm the public board response has no email or takedown token.
- [ ] Explain why Vue escaping and server-side tag stripping are complementary,
      not duplicates.
- [ ] Run Lighthouse and record the performance score.

## 10-minute drill

Open `TalentBoard.vue` and trace one submission from the modal to the public
board. List every place privacy or escaping is enforced.
