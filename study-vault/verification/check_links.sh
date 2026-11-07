#!/usr/bin/env bash
# Re-check every official documentation link used by the study vault.
# Requires curl. Exits non-zero if any link does not return a 2xx/3xx status.

set -u

URLS=(
  "https://docs.python.org/3/library/secrets.html#secrets.compare_digest"
  "https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html"
  "https://fastapi.tiangolo.com/tutorial/testing/"
  "https://docs.pytest.org/en/stable/how-to/monkeypatch.html"
  "https://docs.github.com/en/actions/writing-workflows/quickstart"
  "https://github.com/gitleaks/gitleaks"
  "https://fastapi.tiangolo.com/tutorial/cors/"
  "https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS"
  "https://genai.owasp.org/llm-top-10/"
  "https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html"
  "https://gandalf.lakera.ai/"
  "https://atlas.mitre.org/"
  "https://www.promptfoo.dev/docs/red-team/quickstart/"
  "https://github.com/NVIDIA/garak"
  "https://github.com/Azure/PyRIT"
  "https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-reduced-motion"
  "https://web.dev/learn/performance"
  "https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html"
  "https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html"
  "https://docs.python.org/3/library/ipaddress.html"
  "https://simonwillison.net/series/prompt-injection/"
  "https://redis.io/docs/latest/"
  "https://redis.io/docs/latest/develop/use/patterns/"
  "https://redis.io/docs/latest/develop/use/client-side-caching/"
  "https://redis.io/docs/latest/develop/clients/redis-py/"
  "https://github.com/redis/redis-py"
  "https://university.redis.io/"
  "https://upstash.com/docs/redis/overall/getstarted"
  "https://render.com/docs/free"
  "https://render.com/docs/key-value"
  "https://supabase.com/docs/guides/platform/going-into-prod"
  "https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule"
  "https://uptimerobot.com/"
  "https://cron-job.org/en/"
  "https://betterstack.com/uptime"
  "https://fastapi.tiangolo.com/advanced/events/"
)

failed=0
checked=0

echo "Study Vault link check"
echo "------------------------------------------------------------"

for url in "${URLS[@]}"; do
  code=$(curl -L -sS -o /dev/null --max-time 25 \
    -A "Mozilla/5.0 (compatible; study-vault-link-checker/1.0)" \
    -w "%{http_code}" "$url" 2>/dev/null)
  checked=$((checked + 1))

  if [[ "$code" =~ ^(2|3)[0-9][0-9]$ ]]; then
    echo "[PASS] $code  $url"
  else
    echo "[FAIL] ${code:-000}  $url"
    failed=$((failed + 1))
  fi
done

echo "------------------------------------------------------------"
echo "Checked: $checked  |  Failed: $failed"

if [[ "$failed" -gt 0 ]]; then
  echo "Update the failing links in study-vault/README.md and the modules."
  exit 1
fi

echo "All study-vault links are reachable."
