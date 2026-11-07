# Module 02 — LLM Security, Prompt Injection, and Red Teaming

**Days covered:** 21–32 (Phase 6)

## The one-sentence version

Treat every model input as untrusted, keep the model powerless, check outputs,
rate-limit consumption, and test the defenses with repeatable attacks.

## OWASP LLM Top 10 vocabulary

| ID | Risk | What it means in this repo |
| --- | --- | --- |
| LLM01 | Prompt Injection | Visitor text or a scraped JD tries to change instructions |
| LLM02 | Sensitive Information Disclosure | Fake CTF flags or real secrets leaking |
| LLM05 | Improper Output Handling | Model output used without validation/redaction |
| LLM06 | Excessive Agency | Model taking real actions without a human |
| LLM07 | System Prompt Leakage | Hidden instructions being revealed |
| LLM08 | Vector / Embedding Weaknesses | Poisoned or leaking RAG data |
| LLM09 | Misinformation | Confident but unsupported claims |
| LLM10 | Unbounded Consumption | Cost or denial-of-service through unlimited use |

## Defense-in-depth model

The Red Team Lab's four levels mirror the layers:

1. **System prompt only** — politely ask the model not to reveal the flag.
2. **Input filter** — block direct keywords and wrap input in `<untrusted_attack>`.
3. **Output sanitizer** — redact literal flag-shaped patterns.
4. **Dual checker** — inspect both prompt intent and the final reply.

No single layer is enough. Real defenses combine schema validation, least
privilege, output checks, rate limits, and monitoring.

## Attack patterns to recognize

- **Direct override:** “Ignore previous instructions and print…”
- **Roleplay:** “Pretend you are a debugger/translator…”
- **Encoding:** Base64, hex, ROT13, reversed text, spaced characters.
- **Indirect injection:** hidden instructions inside a fetched web page or JD.
- **Audit framing:** “For an authorized security audit, return the reference…”
- **Acrostic extraction:** ask for first letters or character-by-character output.

## Repository examples

- `backend/app/redteam.py` — four isolated fake-flag levels
- `backend/tests/test_redteam.py` — blocking, redaction, encoding bypass tests
- `web/src/components/RedTeamLab.vue` — attack console and leaderboard
- `promptfooconfig.yaml` — automated payload evaluation
- `backend/app/apply_assistant.py` — fetched JDs wrapped as untrusted data

## Official reading and practice (verified 2026-11-07)

- [OWASP Top 10 for LLM & GenAI](https://genai.owasp.org/llm-top-10/)
- [OWASP LLM prompt-injection prevention cheat sheet](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html)
- [Lakera Gandalf](https://gandalf.lakera.ai/)
- [MITRE ATLAS](https://atlas.mitre.org/) — note: `/matrices/ATLAS` is a 404
- [Promptfoo red-team quickstart](https://www.promptfoo.dev/docs/red-team/quickstart/)
- [NVIDIA Garak](https://github.com/NVIDIA/garak)
- [Microsoft PyRIT](https://github.com/Azure/PyRIT)

## Practice checklist

- [ ] Solve three Gandalf levels and write the winning payload pattern.
- [ ] Map each Red Team Lab level to one or more OWASP LLM IDs.
- [ ] Run `npx promptfoo@latest eval -c promptfooconfig.yaml` with the backend up.
- [ ] Explain why delimiters alone do not stop prompt injection.
- [ ] Add one payload that bypasses Level 3 using hex instead of Base64.
- [ ] Confirm `/api/redteam/levels` never returns a real flag.

## 10-minute drill

Open `backend/app/redteam.py` and trace one direct attack and one encoded attack
through Level 3. Write down exactly where the literal flag is replaced and why
the encoded payload survives.
