# Peoties deployment lessons (2026-05-29 MVP go-live)

Sediment from cutting Peoties live on the SG VPS for the first time
(one afternoon, ~3 hours of debugging). If you're standing up a similar
`business-<tenant>/` wrapper deployment, read this before you start —
every entry below is a real incident, and every fix took longer than it
should have because the trap wasn't obvious upfront.

## 1. Don't let multiple processes share one Telegram bot token

**Symptom**: hermes-gateway log showed recurring `Conflict: terminated
by other getUpdates request` warnings every ~25s.

**Root cause**: Three corvus docker containers (`corvus-guan`,
`corvus-willwei`, `corvus-maxwell_liu`) and hermes-gateway were all
configured with the same `TELEGRAM_BOT_TOKEN`. Telegram only delivers
updates to one long-poll consumer at a time, so they kept stealing the
polling lease from each other — every individual bot was effectively
broken even though all four processes looked healthy.

**Fix**: `docker stop` the corvus containers sharing the token before
bringing up the wrapper. Each ongoing deployment gets its own bot token
from `@BotFather`.

**Lesson**: Before deploy, `ps auxf | grep -E '(telegram|bot)'` and
`docker ps` to find any other process polling the token. The `bot_id`
prefix of the token (`<bot_id>:<secret>` — the part before the colon)
is identifying enough; you don't need to read the secret to compare.

## 2. Hermes tool execution cwd ≠ systemd WorkingDirectory

**Symptom**: First skill turn returned `Path not found:
data/business-peoties/peoties-prod/members/`.

**Root cause**: hermes systemd unit has
`WorkingDirectory=/opt/hermes-agent`, but tools run inside hermes's
internal sandbox which defaults `cwd` to the user's home (`/root` for
the root user). Relative KB paths resolved against `/root` and missed.

**Fix**: Set `TERMINAL_CWD=/opt/hermes-agent` in hermes's `.env`. The
gateway honours `TERMINAL_CWD` over `$HOME` for messaging-platform
tool execution — see `gateway/run.py:1009-1012`.

**Lesson**: For every new business deployment, set `TERMINAL_CWD` to
where the KB lives, before relying on relative paths in SKILL.md.

## 3. Hermes refuses session continuity without `API_SERVER_KEY`

**Symptom**: Wrapper POST to `/v1/chat/completions` returned 403
`Session continuation via X-Hermes-Session-Id rejected: no API key
configured`.

**Root cause**: hermes's api_server treats per-caller
`X-Hermes-Session-Id` headers as security-sensitive (without auth, an
anonymous caller could hijack any session id). It refuses session
continuity unless `API_SERVER_KEY` is set — **even on the loopback
interface**.

**Fix**: `openssl rand -hex 32` → put the same value in hermes `.env`
as `API_SERVER_KEY` and in wrapper `.env` as `HERMES_API_KEY`. Wrapper
sends `Authorization: Bearer ${HERMES_API_KEY}` on every call.

**Lesson**: The "localhost is safe enough, skip the key" instinct
breaks per-user sessions. Don't skip the key just because you're on
the loopback.

## 4. Hermes is a generic AI by default — system prompt must bootstrap brand

**Symptom**: First user DM "hi" returned `Hello Russell! How can I
assist you today?` — pure generic-AI tone, no Peoties branding, no
skill dispatch.

**Root cause**: hermes loads skills on-demand (the LLM has to call
`skills_list` + `skill_view` itself). Without an active hint, "hi"
doesn't trigger any skill load; hermes falls through to its default
assistant behaviour.

**Fix**: Wrapper prepends a `system`-role message on every
`/v1/chat/completions` call. hermes merges it into
`ephemeral_system_prompt` (see
`gateway/platforms/api_server.py:1135`). The prompt establishes brand
voice, mandates the caller-block parse, routes intents to the
peoties-* skills, and explicitly forbids the "How can I help?"
fallback.

**Lesson**: hermes is platform infrastructure, not a finished bot.
Every business deployment needs its own bootstrap prompt. Version it
next to the wrapper as business-layer code.

## 5. Brand voice collapses in non-English by default

**Symptom**: Same "hi" sent in Mandarin (`你好`) returned `你好,
Russell! 欢迎你! 有什么我可以帮助你的吗?` — the literal Chinese
rendering of "Hello! Welcome! How can I help you?", with no Peoties
branding and the exact phrase the English prompt explicitly forbade
("How can I assist you today").

**Root cause**: System prompt was English-only. gpt-4o-mini mirrors
the user's language but doesn't carry the English anti-patterns or
brand vocabulary into the translation — "how can I help" → "有什么我
可以帮助你的吗" is a clean translation that *to the model* doesn't
look like the forbidden phrase.

**Fix**: System prompt now lists forbidden phrases in Mandarin /
Malay / Tamil with sample brand-aligned openers in each language, and
mandates that "Peoties" stays in English inside every other language.

**Lesson**: Brand voice rules need per-language exemplars for every
language you officially support. "Mirror the user's language" by
itself doesn't preserve tone — the model needs concrete forbidden /
preferred phrases per language.

## 6. LLM (especially mini) shortcuts long SKILL procedures

**Symptom**: Test user said "I want to join". Bot replied "Thank you
for your patience, Russell! I've started the onboarding process for
you... team will reach out in 1-2 weeks." But it had only called
`write_file` once with **3 fields** (gateway_user_id, gateway_username,
status) and **fabricated** the body summary. The actual intake
(10-15 turn slow conversation collecting 13 required fields) was
skipped entirely.

**Root cause**: gpt-4o-mini reads the SKILL.md procedure but optimises
for completion latency — it interprets "intake skill" as "create one
file then say done", not as "slowly converse for 10+ turns collecting
specific fields".

**Fix (planned, not yet implemented as of 2026-05-29)**: Add a hard
precondition to intake SKILL.md: "DO NOT call write_file before turn 8.
Before write_file, you must have collected, by turn-by-turn
conversation, all 13 required fields." Weak models may still drift;
long-term we may add a wrapper-side hook that validates field
completeness before delivering an "you're enrolled" reply.

**Lesson**: For multi-turn skills with mini-class models, "the
SKILL.md says so" is not enforcement — it's a suggestion. Either
constrain via hard rules at the top of the prompt (numeric turn
gates, explicit refusal phrases) or add programmatic post-hooks.

## 7. Sample / seed data must NOT use real user identifiers

**Symptom**: After fixing the cwd issue, the bot would have matched
the test user (telegram_id `1946161251`) to
`member--anna-tan-7a3f.md` because the Anna sample file had
`gateway_user_id: "tg:1946161251"` — which was the developer's own
telegram id, baked in as a "placeholder" during sample-data creation.

**Root cause**: During KB seeding, the sample `gateway_user_id` was
set to the developer's own id, never replaced.

**Fix**: Strip identity-binding fields from all sample/seed data
before deploy. Sample data should have **no** real telegram ids,
emails, phones, or anything that could collide with a real user.

**Lesson**: Sample data and real user identity must never share a
namespace. Seed files should use clearly-fake ids — e.g.
`tg:9999999001`, `email: anna@sample.peoties.test`,
`phone: +65 9XXX XXXX` (literally, with placeholders).

## 8. Don't leave templated placeholders in LLM-facing prompt examples

**Symptom**: The redirect template included `For [their topic], you'd
want a different tool`. The model sometimes output the literal
`[their topic]` string, and worse, sometimes echoed the user's
specific topic back judgmentally ("For investment advice, you'd want
a different tool").

**Root cause**: `[bracketed placeholders]` in prompt examples assume
the model substitutes them. Weak models either pass them through
literally or fill them with the user's specific request — both bad.

**Fix**: Lock redirect wording to fixed phrases ("for other topics")
and explicitly forbid topic-echoing.

**Lesson**: Never put `[bracketed placeholders]` in LLM-facing
exemplars unless you've tested the model substitutes correctly. For
weak models, use literal final wording.

---

## What stayed easy (worked on the first try)

For balance, so the next deployer knows where not to over-engineer:

- `/start` and `/help` wrapper override — hermes UI completely
  hidden, took ~5 lines of python-telegram-bot code
- hermes api_server endpoint — OpenAI-compatible
  (`/v1/chat/completions`), works with any standard client
- Per-user session via `X-Hermes-Session-Id` header (once the API
  key was set per #3)
- KB read via `search_files` + `read_file` (once cwd was set per #2)
- Caller-block parsing by the LLM — the nonce-protection idea worked
  as designed, no injection attempts got through

## Per-deployment checklist (mirror this for the next business)

Before you start, prepare:
1. A dedicated Telegram bot token from `@BotFather` (don't share)
2. KB directory at a known absolute path
3. `TERMINAL_CWD` env value pointing to that path
4. `API_SERVER_KEY` generated via `openssl rand -hex 32`
5. A wrapper system prompt with: brand voice (per-language
   exemplars), skill dispatch table, scope boundary, forbidden
   phrases
6. SKILL.md files with hard procedural gates for any multi-turn
   flow (don't rely on "just follow the procedure")
7. Seed/sample data with **fake** ids, emails, phones
8. A smoke-test checklist that exercises: `/start`, `/help`,
   one in-scope question, one out-of-scope question (verify
   redirect), one greeting in each supported language

Most of these are 5-minute items in isolation. The 3 hours of
debugging on 5-29 came from hitting them in production rather than
during prep.
