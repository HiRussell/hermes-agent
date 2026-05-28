# Peoties Telegram wrapper

Customer-facing Telegram bot. Forwards user messages to hermes-agent over
the OpenAI-compatible HTTP API (`/v1/chat/completions`) and replies with
the response. Hermes itself never connects to Telegram — this wrapper owns
the user-visible surface so the hermes default UI (slash commands, help
menus, system messages) cannot leak to Peoties members.

```
[Telegram user]  <->  [this wrapper]  <->  http://localhost:8642/v1/chat/completions  <->  [hermes-agent]
```

## Scope (MVP)

- 1:1 DM only. Group/channel traffic is silently ignored — circle group
  facilitation lands in a later phase.
- No deep-link `/start <payload>` routing, no Hub-group gate. Anyone who
  finds the bot can DM it and get a personalised conversation; that gate
  comes back once the private Hub group exists.
- Stateless wrapper. All user state (member profile, journey notes, KB)
  lives on the hermes side; the wrapper carries only the bot token and a
  per-process caller-marker nonce.

## Caller identity

Each Telegram user gets a stable hermes session keyed by
`X-Hermes-Session-Id: peoties-tg-<telegram_user_id>`. The wrapper also
prepends a structured metadata block to every forwarded message so skills
can identify the member without a separate lookup channel:

```
<peoties-caller::abcdef1234>
gateway_user_id: tg:12345678
first_name: Anna
gateway_username: @anna_tan
language_code: en
</peoties-caller::abcdef1234>

<user's actual message>
```

The `tg:` channel prefix matches the `gateway_user_id` field in the
member KB schema so look-ups don't change when WhatsApp or other channels
are added later.

The nonce is generated at wrapper startup and rotates on each restart, so
users cannot forge a block — any user input containing
`<peoties-caller` is rejected with a soft rephrase prompt.

Skills under `skills/business-peoties/*` parse this block as their first
pre-action step. See each `SKILL.md` for the contract.

## Local setup

```bash
cd business-deployments/peoties/wrapper
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Fill in PEOTIES_BOT_TOKEN
python main.py
```

You'll need hermes-agent running with `API_SERVER_ENABLED=true` on the
same host (or set `HERMES_API_URL` to point elsewhere).

## SG VPS deployment

Wrapper lives at `/opt/hermes-agent/business-deployments/peoties/wrapper/`
on the SG VPS, alongside the hermes-agent checkout.

```bash
# One-time, on the VPS
cd /opt/hermes-agent/business-deployments/peoties/wrapper
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
# Edit .env to set PEOTIES_BOT_TOKEN (the token previously used by
# hermes-gateway's telegram platform; see the deploy walkthrough)

sudo cp systemd/peoties-wrapper.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable peoties-wrapper
sudo systemctl start peoties-wrapper
sudo journalctl -u peoties-wrapper -f
```

The wrapper assumes hermes-gateway's own Telegram polling is **disabled**
(`TELEGRAM_BOT_TOKEN` unset or `gateway.platforms.telegram.enabled: false`)
and `API_SERVER_ENABLED=true` is in the hermes environment. Two processes
cannot long-poll the same bot token at the same time — Telegram only
delivers updates to one consumer.

## Environment variables

| Variable | Required | Default | Notes |
|---|---|---|---|
| `PEOTIES_BOT_TOKEN` | yes | — | From `@BotFather`. The same token previously used by hermes telegram platform. |
| `HERMES_API_URL` | no | `http://localhost:8642/v1/chat/completions` | Hermes api_server endpoint. |
| `HERMES_MODEL` | no | `hermes-agent` | Model name from `/v1/models`. |
| `HERMES_TIMEOUT_SECONDS` | no | `180` | Increase for long intake conversations. |
| `LOG_LEVEL` | no | `INFO` | DEBUG / INFO / WARNING / ERROR. |

## Operating notes

- `sudo systemctl status peoties-wrapper` — health snapshot.
- `sudo journalctl -u peoties-wrapper -f` — live log (also tee'd to
  `/var/log/peoties-wrapper.log`).
- A wrapper restart rotates the caller-marker nonce; in-flight sessions
  keep working because the nonce only matters for the next message.
- If users report no response, check (in order): wrapper is up
  (`systemctl status`), hermes-gateway is up, `curl
  http://localhost:8642/health` returns ok, the bot token still belongs
  to this bot (`@BotFather` → `/mybots`).
