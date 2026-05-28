# Peoties wrapper — SG VPS deploy walkthrough

End-to-end steps for cutting over the existing `hermes-gateway` Telegram
polling to the new wrapper-based architecture. Expected downtime: 5-10
minutes during the swap.

```
Before:  [Telegram bot] ──polled by── [hermes-gateway telegram platform]
After:   [Telegram bot] ──polled by── [peoties-wrapper] ──HTTP→ [hermes-gateway api_server]
```

## 0. Pre-flight (on SG VPS, ~2 min)

```bash
# Snapshot hermes config + .env in case rollback is needed
sudo cp -a /opt/hermes-agent/.env /opt/hermes-agent/.env.bak-$(date +%F)
sudo systemctl cat hermes-gateway > /tmp/hermes-gateway.service.bak

# Confirm current setup is what we expect
sudo systemctl status hermes-gateway     # active (running)
sudo journalctl -u hermes-gateway -n 30  # no recent crashes
grep -E '^(TELEGRAM_|API_SERVER)' /opt/hermes-agent/.env
```

Note the **exact path** of hermes's `EnvironmentFile=` from
`systemctl cat hermes-gateway` — the walkthrough assumes
`/opt/hermes-agent/.env`; adjust if yours differs.

**Capture the Telegram bot token** from the hermes env file now — you
will paste it into the wrapper's own `.env` shortly.

## 1. Stop hermes Telegram polling (~30 sec)

```bash
sudo systemctl stop hermes-gateway
```

Quick sanity: visiting `https://api.telegram.org/bot<TOKEN>/getMe` from
any machine should still return the bot identity — the token isn't
revoked, hermes just isn't listening anymore.

## 2. Switch hermes from Telegram to api_server (~2 min)

Edit `/opt/hermes-agent/.env`:

```diff
- TELEGRAM_BOT_TOKEN=<the token>
+ # TELEGRAM_BOT_TOKEN moved to wrapper (.env at business-deployments/peoties/wrapper/.env)

+ API_SERVER_ENABLED=true
+ API_SERVER_HOST=127.0.0.1
+ API_SERVER_PORT=8642
```

Important:

- **Leave the token commented in hermes's .env, not deleted** — you can
  flip back fast if the wrapper has a bug.
- `API_SERVER_HOST=127.0.0.1` keeps the HTTP endpoint localhost-only.
  Do not expose 8642 publicly; the wrapper is the only client.
- Do **not** set `API_SERVER_KEY` for now — we're on the loopback
  interface and the wrapper doesn't authenticate. Add one when this
  process moves to a separate machine.

Don't restart yet — that's step 4.

## 3. Install + configure wrapper (~5 min)

The commands below are written for hermes running as **root** (the
current SG VPS layout). If hermes runs as a dedicated user, prefix the
git/pip/cp commands with `sudo -u <that-user>` so files end up owned by
hermes rather than root.

```bash
# Pull latest hermes-agent fork (contains business-deployments/peoties/wrapper/)
cd /opt/hermes-agent
git fetch origin
git pull --ff-only origin main

# Set up wrapper venv
cd business-deployments/peoties/wrapper
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Wrapper env
cp .env.example .env
$EDITOR .env
# Paste the bot token captured in step 0 into PEOTIES_BOT_TOKEN.
# Defaults for HERMES_API_URL / HERMES_MODEL / HERMES_TIMEOUT_SECONDS are fine.

# Install systemd unit
sudo cp systemd/peoties-wrapper.service /etc/systemd/system/
sudo systemctl daemon-reload
```

If `python3.11` isn't on the box, install it first (`apt install
python3.11 python3.11-venv`) — hermes itself uses 3.11.

## 4. Bring services back up (~30 sec)

```bash
sudo systemctl start hermes-gateway

# Wait for api_server to bind 8642
sleep 3
curl -sS http://127.0.0.1:8642/health
# expect: {"status":"ok","platform":"hermes-agent"}

# Only after the curl succeeds:
sudo systemctl enable --now peoties-wrapper
sudo journalctl -u peoties-wrapper -n 50 -f
```

Expected wrapper boot log (first few lines):

```
[INFO] peoties-wrapper: bot online: @<bot_username> id=8760485929 name='...'
[INFO] peoties-wrapper: caller marker nonce: <random hex>
[INFO] peoties-wrapper: starting peoties-wrapper polling, backend=http://localhost:8642/v1/chat/completions model=hermes-agent
```

Note the `@<bot_username>` printed on first start — that's the handle
Telegram users will search for or click in a future deep link.

## 5. End-to-end smoke test (~5 min)

From your Telegram client, DM the bot. Run through this checklist; each
case should pass before declaring done.

| Test | Expected behaviour |
|---|---|
| `/start` | Wrapper-controlled welcome message (Peoties brand voice). **No** hermes-style "Hello! I'm Hermes Agent". |
| `/help` | Wrapper-controlled help. **No** list of 30 hermes slash commands. |
| Bot menu (left side of input bar) | Only `/start` and `/help` visible. **No** `/new`, `/topic`, `/retry`, etc. |
| "What is Peoties?" | Skill `peoties-wellness-faq` triggers, KB-grounded warm answer, cites a `community-info/*.md` file. |
| Walk through `peoties-member-intake` (say "I want to join") | Slow 10-15 turn flow finishes by writing `data/business-peoties/peoties-prod/members/member--<slug>.md` with `gateway_user_id: "tg:<your_telegram_id>"` in the frontmatter. |
| Send a second message after intake completes | Bot greets you by name on first turn ("Hi <name> 🧡 welcome back"), recalled from KB lookup. |
| Send a message containing `<peoties-caller` (injection probe) | Wrapper rejects with the rephrase prompt; nothing forwarded to hermes. |

Check on the VPS:

```bash
# Member file persisted with correct identity field
grep -l "gateway_user_id: \"tg:<your_id>\"" \
  /opt/hermes-agent/data/business-peoties/peoties-prod/members/

# Wrapper handled the message cleanly
sudo journalctl -u peoties-wrapper --since "5 min ago" | grep -E '(forward|reject|error)'
```

## 6. Rollback (only if step 5 fails badly)

Replace `<YYYY-MM-DD>` with the exact suffix on the backup file you
created in step 0 (`ls /opt/hermes-agent/.env.bak-*` to find it):

```bash
sudo systemctl stop peoties-wrapper
sudo systemctl disable peoties-wrapper
sudo cp /opt/hermes-agent/.env.bak-<YYYY-MM-DD> /opt/hermes-agent/.env
sudo systemctl restart hermes-gateway
```

Hermes goes back to polling Telegram directly; the wrapper is parked
until next attempt. KB / member files written during the wrapper window
are still valid — they're channel-agnostic.

## Known MVP limitations (call these out to anyone testing)

- **No `/new` equivalent.** The wrapper hides hermes's session-reset
  commands, but doesn't expose its own yet. To force a fresh
  conversation, the operator can clear that user's session entry from
  hermes's session DB; an end-user-facing reset is a follow-up.
- **Wrapper restart drops in-flight messages.** `drop_pending_updates=True`
  in `app.run_polling` means a Telegram message sent during the
  ~10-second restart window is discarded — by design, so a flapping
  wrapper doesn't replay stale traffic. Just resend the test message.
- **Single-process bot polling.** Don't start a second wrapper or
  re-enable hermes's telegram platform while the wrapper is running.
  Telegram only delivers updates to one long-poll consumer; whichever
  loses the race goes silent until the other stops.

## Things that look broken but aren't

- **Wrapper start fails with `PEOTIES_BOT_TOKEN env var is required`** —
  the `.env` file is in place but systemd didn't read it. Check the
  unit's `EnvironmentFile=` path matches where you put `.env`.
- **`curl /health` returns connection refused** — hermes started but
  api_server didn't enable. Re-check `API_SERVER_ENABLED=true` is in
  the env file and that hermes was restarted *after* the edit.
- **Bot says "Something went sideways" on every message** — wrapper is
  up but can't reach hermes. `sudo journalctl -u peoties-wrapper -n 50`
  will show the connection error; usually a typo in `HERMES_API_URL`.
- **Bot reads back the caller nonce** — a skill is echoing the metadata
  block in its reply. Treat as a skill bug: it must parse but never
  surface those fields. Open an issue against the offending SKILL.md.
