# Study Vault — Days 16–44

**Why “study-vault”?** It is short, memorable, and easy to find again with a
single search: `study-vault`. Everything study-related lives here instead of
being scattered across the repository.

This vault turns the Phase 6–8 build into a reusable learning curriculum:

```
study-vault/
├── README.md                    ← you are here
├── modules/
│   ├── 01_testing_and_ci.md
│   ├── 02_llm_security_owasp.md
│   ├── 03_ssrf_and_network_security.md
│   ├── 04_frontend_a11y_and_moderation.md
│   └── 05_redis_caching_and_keepalive.md
└── verification/
    ├── verify_setup.py          ← runs backend/frontend tests + security checks
    └── check_links.sh           ← re-checks every official documentation link
```

## How to use it

1. Read one module at a time.
2. Open the linked official docs.
3. Find the matching code in this repository.
4. Explain the concept out loud in two sentences.
5. Run the verification harness:

```bash
python study-vault/verification/verify_setup.py
```

The harness exits non-zero if anything fails, so it can also run in CI.

To re-check the documentation links:

```bash
bash study-vault/verification/check_links.sh
```

## Link verification — 2026-11-07

All links below were checked with `curl -L` on **2026-11-07**.

| Module | Link | Status |
| --- | --- | --- |
| Testing | [Python `secrets.compare_digest`](https://docs.python.org/3/library/secrets.html#secrets.compare_digest) | ✅ 200 |
| Testing | [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html) | ✅ 200 |
| Testing | [FastAPI testing tutorial](https://fastapi.tiangolo.com/tutorial/testing/) | ✅ 200 |
| Testing | [Pytest monkeypatch guide](https://docs.pytest.org/en/stable/how-to/monkeypatch.html) | ✅ 200 |
| CI/CD | [GitHub Actions quickstart](https://docs.github.com/en/actions/writing-workflows/quickstart) | ✅ 200 |
| CI/CD | [Gitleaks](https://github.com/gitleaks/gitleaks) | ✅ 200 |
| Deployment | [FastAPI CORS](https://fastapi.tiangolo.com/tutorial/cors/) | ✅ 200 |
| Deployment | [MDN CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS) | ✅ 200 |
| LLM security | [OWASP LLM Top 10](https://genai.owasp.org/llm-top-10/) | ✅ 200 |
| LLM security | [OWASP prompt-injection cheat sheet](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html) | ✅ 200 |
| LLM security | [Lakera Gandalf](https://gandalf.lakera.ai/) | ✅ 200 |
| LLM security | [MITRE ATLAS](https://atlas.mitre.org/) | ✅ 200 |
| LLM security | [Promptfoo red teaming](https://www.promptfoo.dev/docs/red-team/quickstart/) | ✅ 200 |
| LLM security | [NVIDIA Garak](https://github.com/NVIDIA/garak) | ✅ 200 |
| LLM security | [Microsoft PyRIT](https://github.com/Azure/PyRIT) | ✅ 200 |
| Frontend | [MDN `prefers-reduced-motion`](https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-reduced-motion) | ✅ 200 |
| Frontend | [web.dev performance](https://web.dev/learn/performance) | ✅ 200 |
| Frontend | [OWASP XSS prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html) | ✅ 200 |
| SSRF | [OWASP SSRF prevention](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html) | ✅ 200 |
| SSRF | [Python `ipaddress`](https://docs.python.org/3/library/ipaddress.html) | ✅ 200 |
| Prompt injection | [Simon Willison series](https://simonwillison.net/series/prompt-injection/) | ✅ 200 |
| Operations | [Redis docs](https://redis.io/docs/latest/) | ✅ 200 |
| Operations | [Redis caching patterns](https://redis.io/docs/latest/develop/use/patterns/) | ✅ 200 |
| Operations | [Redis client-side caching](https://redis.io/docs/latest/develop/use/client-side-caching/) | ✅ 200 |
| Operations | [redis-py docs](https://redis.io/docs/latest/develop/clients/redis-py/) | ✅ 200 |
| Operations | [Redis University](https://university.redis.io/) | ✅ 200 |
| Operations | [Upstash Redis](https://upstash.com/docs/redis/overall/getstarted) | ✅ 200 |
| Operations | [Render free tier](https://render.com/docs/free) | ✅ 200 |
| Operations | [Render Key Value](https://render.com/docs/key-value) | ✅ 200 |
| Operations | [Supabase production checklist](https://supabase.com/docs/guides/platform/going-into-prod) | ✅ 200 |
| Operations | [GitHub Actions schedule syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule) | ✅ 200 |
| Operations | [UptimeRobot](https://uptimerobot.com/) | ✅ 200 |
| Operations | [cron-job.org](https://cron-job.org/en/) | ✅ 200 |
| Operations | [Better Stack Uptime](https://betterstack.com/uptime) | ✅ 200 |
| Operations | [FastAPI lifespan events](https://fastapi.tiangolo.com/advanced/events/) | ✅ 200 |

### Correction

The pasted guide used:

`https://atlas.mitre.org/matrices/ATLAS` → **404**

The working official entry point is:

`https://atlas.mitre.org/` → **200**

Use the root URL in notes and future slides.

## Related repository documents

- [`../LEARNING_RESOURCES.md`](../LEARNING_RESOURCES.md) — full narrative study guide
- [`../LOG.md`](../LOG.md) — implementation history through Day 44
- [`../THREAT_MODEL.md`](../THREAT_MODEL.md) — OWASP LLM Top 10 mapping
