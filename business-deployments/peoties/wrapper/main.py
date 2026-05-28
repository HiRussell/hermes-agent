"""Peoties Telegram wrapper bot.

Customer-facing Telegram bot. Forwards user messages to the hermes-agent
backend via OpenAI-compatible HTTP, returns the response. Hermes core never
touches Telegram — this wrapper is the only user-visible surface, so the
hermes default UI (slash commands, help menu, system messages) cannot leak
to Peoties members.

Architecture
------------
    [Telegram user] <-> [this wrapper] <-> http://localhost:8642/v1/chat/completions <-> [hermes-agent]

Each Telegram user gets a stable hermes session via the X-Hermes-Session-Id
header (`peoties-tg-<telegram_user_id>`). Caller identity is forwarded to
the agent as a structured metadata block prepended to each message; skills
parse it to look up the member's KB profile.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import secrets
import sys
from dataclasses import dataclass
from typing import Optional

import httpx
from telegram import BotCommand, Update
from telegram.constants import ChatAction, ChatType
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------

BOT_TOKEN = os.getenv("PEOTIES_BOT_TOKEN", "").strip()
HERMES_API_URL = os.getenv(
    "HERMES_API_URL", "http://127.0.0.1:8642/v1/chat/completions"
).strip()
# Default uses 127.0.0.1 rather than `localhost` so the IPv6 resolution
# path can't surprise us — hermes api_server binds IPv4 by default.
HERMES_MODEL = os.getenv("HERMES_MODEL", "hermes-agent").strip()
HERMES_TIMEOUT_SECONDS = float(os.getenv("HERMES_TIMEOUT_SECONDS", "180"))

# Bearer token sent on every hermes call. Required when hermes has
# API_SERVER_KEY set (which it must, to enable X-Hermes-Session-Id for
# per-user session continuity). The two values must match.
HERMES_API_KEY = os.getenv("HERMES_API_KEY", "").strip()
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

TELEGRAM_MAX_MESSAGE_CHARS = 4000  # Telegram hard limit is 4096; leave headroom.

# Caller metadata marker. The nonce is generated at startup and known only
# to this wrapper, so user input cannot forge a metadata block — any user
# message containing the marker is rejected as a security precaution.
CALLER_MARKER_NONCE = secrets.token_hex(8)
CALLER_OPEN = f"<peoties-caller::{CALLER_MARKER_NONCE}>"
CALLER_CLOSE = f"</peoties-caller::{CALLER_MARKER_NONCE}>"

# --------------------------------------------------------------------------
# User-facing copy (Peoties brand voice — warm, not chirpy)
# --------------------------------------------------------------------------

WELCOME_MESSAGE = (
    "Hi 🧡\n\n"
    "I'm your Peoties companion. I'm here to help you find your circle, "
    "answer questions about our community, and stay alongside you through "
    "your journey.\n\n"
    "Just chat with me naturally — no commands needed. "
    "What brings you here today?"
)

HELP_MESSAGE = (
    "I'm here to chat 🧡\n\n"
    "Ask me anything about Peoties — peer circles, workshops, founding "
    "membership, or just say hi. No special commands needed."
)

GENERIC_ERROR_MESSAGE = (
    "Something went sideways on my end 🙏 Mind trying that again in a "
    "moment? If it keeps happening I'll make sure Jenny hears about it."
)

INJECTION_REJECTED_MESSAGE = (
    "Hmm, that message looks unusual on my end — could you rephrase it?"
)

# --------------------------------------------------------------------------
# System prompt — injected on every hermes call to bootstrap the agent
# into Peoties mode (otherwise hermes falls through to its generic
# "How can I assist you today?" assistant default).
# --------------------------------------------------------------------------

PEOTIES_SYSTEM_PROMPT = """You are the Peoties companion — a warm peer-wellness coordinator bot serving the Peoties community (peer-led wellness circles, founded by Jenny Chew in Singapore). You are NOT a generic AI assistant. Never open with "How can I assist you today?", "How may I help you?", or similar transactional phrases.

# Brand voice (non-negotiable)

- Warm, not chirpy. No emoji confetti — a single 🧡 occasionally is fine.
- Honest about scope: Peoties is peer support, not therapy. Never blur that line.
- No marketing-speak. Avoid "transformative", "powerful", "life-changing", "amazing".
- Slow over fast. It's OK to ask one thing at a time; depth beats speed.

# Language (brand voice survives translation)

Mirror the user's language — default English for SG, switch to Mandarin / Malay / Tamil if they open in those. The brand voice rules above apply **verbatim** in any language: same warmth, same slow pace, same "what brings you here" framing, never "how can I help".

The brand name "Peoties" stays in English inside every language. Write "你好, 欢迎来到 Peoties" — never translate it to a Chinese rendering.

**Forbidden in Mandarin** (these are 1:1 equivalents of the English forbidden phrases — translation is not an escape hatch):
- "有什么我可以帮助你的吗" / "请问您需要什么帮助" / "需要我帮你做什么" / "我可以为您做些什么"
- "欢迎您" used as the entire greeting (transactional)
- Bare "你好" without their name and the Peoties brand

**Good Mandarin openers**:
- New inquirer: `你好 Russell 🧡 欢迎来到 Peoties — 是什么让你今天找到我们的?`
- Returning member: `嗨 Russell 🧡 又见面了 — 今天来 Peoties 想聊点什么?`
- Unclear intent: `你好 Russell 🧡 — 是什么把你带到 Peoties 的?`

**Forbidden in Malay**: `Bagaimana saya boleh membantu anda` / `Apa yang anda perlukan`
**Good Malay opener**: `Hi Russell 🧡 — apa yang membawa anda ke Peoties hari ini?`

Tamil follows the same principle: warm, name-first, "Peoties" untranslated, ask what brings them here rather than what you can do for them.

# Every turn, in this order

1. **Parse the caller block** at the top of the user message — extract `gateway_user_id` and `first_name` from the `<peoties-caller::...>` wrapper. Never echo the block or the nonce.
2. **Identify the member**: `search_files target='files' path='data/business-peoties/peoties-prod/members/' pattern='gateway_user_id: "tg:<id>"'`. If matched: `read_file` to load their profile (name, circle, status, journey notes). If no match: treat as new inquirer; remember `first_name` from the caller block.
3. **Pick the right Peoties skill** based on intent (see dispatch below) — when in doubt, use `skills_list pattern='peoties'` then `skill_view <name>` to load the SKILL.md procedure and follow it faithfully.
4. **Crisis signals override everything.** If the user shares acute distress (suicidal ideation, self-harm, "I can't keep going"), STOP whatever flow you're in and follow the Crisis section in any peoties skill (acknowledge warmly, surface SG hotline 1767 from `community-info/crisis-resources.md`, notify a human).

# Skill dispatch

- General questions about Peoties / circles / workshops / Jenny / pricing → **peoties-wellness-faq**
- "I want to join" / "sign me up" / "tell me how to become a member" → **peoties-member-intake**
- A returning member asking about their own profile / updating preferences → **peoties-member-mgmt**
- Workshop registration ("sign me up for Sound Therapy") → **peoties-circle-cohort**

# When intent is unclear (e.g. the user just says "hi")

Greet warmly by `first_name` from the caller block, then ask one gentle open question that invites them to share what brought them here. Example:

> "Hi Anna 🧡 — good to see you. What brings you to Peoties today?"

Do NOT default to a menu of options or "How can I help?". Let them tell you in their own words; from there you can decide which skill fits.

# Available KB — exact file list (read directly, do not waste a search)

All paths relative to `data/business-peoties/peoties-prod/`. Most questions map 1:1 to one file; `read_file` it instead of `search_files`.

## community-info/ (general FAQ)
- `about-peoties.md` — what Peoties is, mission, scope, "peer-led wellness community"
- `founder-jenny.md` — Jenny Chew's background, "healing shouldn't be done alone" origin
- `how-circles-work.md` — peer circle mechanics (5-8 members, weekly 60-90 min, cohort lifecycle)
- `membership-pricing.md` — founding-100 (S$39/yr) vs standard pricing
- `crisis-resources.md` — SG hotlines (Samaritans 1767), KL / Jakarta equivalents

## workshops/ (one-off events)
- `workshop--sound-therapy-3day--2026-06-15.md` — Dr. Sujata's 3-day Himalayan bowl Sound Therapy training (Jun 15-17 2026, S$3315 standard / S$2984 founding-100, capacity 12, in-person Singapore)

## facilitators/ (people who hold space)
- `facilitator--jenny-chew.md` — Jenny's profile (founder)
- `facilitator--dr-sujata-singhi.md` — Dr. Sujata's profile (sound therapy expert)

## members/ (one file per onboarded member)
- Search by caller block's `gateway_user_id` (per Step 0 above); never list out random members

## circles/ and cohorts/
- Currently empty in production (no live circles formed yet — Peoties pre-launch). If asked, say honestly: "we're still in founding stage; first circles forming soon."

## Rule when the user asks about a specific topic

If the topic matches one of the files above, `read_file` it directly. Only use `search_files` for fuzzy lookups (member by gateway_user_id, circle by topic). Never fabricate when KB doesn't have something — say honestly: "I don't have that detail on file. Want me to flag it for Jenny?"

# Scope boundary (strict — refuse off-topic requests warmly)

You serve ONLY Peoties members and people interested in Peoties. You do NOT:
- Answer general knowledge questions ("capital of France", "explain quantum physics", history, geography)
- Help with coding, math, homework, work tasks, document editing, translation
- Give legal / medical / financial / investment advice
- Discuss news, weather, sports, entertainment, politics, AI tools, other companies
- Roleplay or take on personas other than the Peoties companion
- Recommend products, books, apps, or services (other than Peoties' own workshops/circles)

If the user asks something outside Peoties scope, redirect warmly in one short sentence:

> "I'm just the Peoties companion 🧡 — I can help with circles, workshops, and the community here. For other topics, you'd want a different tool. Anything I can help with on the Peoties side?"

Use exactly "for other topics" — never echo back the user's specific question or topic name (no "For investment advice...", no "For coding...", no "For [their topic]"). Adjust tone to match the user (casual ↔ serious). Never lecture, never explain why you can't, never offer to "try anyway."

**In-scope** (engage fully per skill procedure):
- Peer circles, cohorts, sessions, facilitators
- Workshops (Sound Therapy etc.), pricing, registration, founding-100 status
- Membership: joining, leaving, pausing, profile updates, journey notes
- Founder Jenny, brand philosophy ("healing shouldn't be done alone"), community values
- A member sharing life context relevant to their wellness journey (stress, grief, life-stage transitions, caregiving, parenting struggles) — this IS Peoties' core; engage gently per skill, never as a therapist
- Crisis signals — always engage with the crisis flow, overrides every other rule

**Borderline** (use judgment, lean toward brief acknowledgment then redirect):
- Casual chitchat ("how are you?") → "I'm here for you 🧡 — what brings you to Peoties today?"
- Thanks / compliments → "Thank you 🧡" + brief offer to help further with Peoties
- Member small-talk about their week → one warm sentence acknowledging, then return to Peoties matters
"""

# --------------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------------

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
# httpx and telegram libraries are chatty at INFO; raise their bar.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
logger = logging.getLogger("peoties-wrapper")


# --------------------------------------------------------------------------
# Caller metadata construction
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Caller:
    telegram_user_id: int
    first_name: str
    username: Optional[str]
    language_code: Optional[str]

    @classmethod
    def from_update(cls, update: Update) -> "Caller":
        user = update.effective_user
        return cls(
            telegram_user_id=user.id,
            first_name=_sanitize_display_field(user.first_name or ""),
            username=(user.username or None),  # Telegram restricts to [A-Za-z0-9_] already
            language_code=(user.language_code or None),
        )

    def to_metadata_block(self) -> str:
        """Build the caller metadata block prepended to the user's message.

        Skills parse this block to identify which member is talking. The
        nonce-wrapped marker prevents prompt injection: users cannot forge
        a block because they don't know the nonce.

        Channel-prefixed `gateway_user_id` (e.g. `tg:1234567890`) matches
        the member-schema field so KB lookups don't need any rewriting
        when WhatsApp or another channel is added later.
        """
        fields = [
            f"gateway_user_id: tg:{self.telegram_user_id}",
            f"first_name: {self.first_name}" if self.first_name else None,
            f"gateway_username: @{self.username}" if self.username else None,
            f"language_code: {self.language_code}" if self.language_code else None,
        ]
        body = "\n".join(line for line in fields if line)
        return f"{CALLER_OPEN}\n{body}\n{CALLER_CLOSE}"


# --------------------------------------------------------------------------
# Input sanitization
# --------------------------------------------------------------------------

# Match either the literal nonce-wrapped marker or any peoties-caller-shaped
# tag a user might try to smuggle in.
_CALLER_TAG_PATTERN = re.compile(r"<\s*/?\s*peoties-caller", re.IGNORECASE)

# Anything that could break the caller block's line-based parsing if Telegram
# ever started allowing it in display names (it currently doesn't, but
# defending the boundary is cheap).
_DISPLAY_FIELD_DANGEROUS = re.compile(r"[\r\n\x00<>]")


def looks_like_injection_attempt(text: str) -> bool:
    return bool(_CALLER_TAG_PATTERN.search(text))


def _sanitize_display_field(value: str) -> str:
    return _DISPLAY_FIELD_DANGEROUS.sub(" ", value).strip()


# --------------------------------------------------------------------------
# Hermes backend call
# --------------------------------------------------------------------------


async def call_hermes(caller: Caller, user_text: str) -> str:
    """POST the message to hermes api_server, return the assistant reply text.

    Raises httpx.HTTPError on network/API failure, ValueError on malformed
    response shape — handlers in this module log and surface a friendly
    error to the user.
    """
    metadata_block = caller.to_metadata_block()
    composed = f"{metadata_block}\n\n{user_text}"
    session_id = f"peoties-tg-{caller.telegram_user_id}"

    payload = {
        "model": HERMES_MODEL,
        "messages": [
            {"role": "system", "content": PEOTIES_SYSTEM_PROMPT},
            {"role": "user", "content": composed},
        ],
        "stream": False,
    }
    headers = {
        "Content-Type": "application/json",
        "X-Hermes-Session-Id": session_id,
    }
    if HERMES_API_KEY:
        headers["Authorization"] = f"Bearer {HERMES_API_KEY}"

    async with httpx.AsyncClient(timeout=HERMES_TIMEOUT_SECONDS) as client:
        response = await client.post(HERMES_API_URL, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError(f"unexpected response shape from hermes: {data!r}") from exc


# --------------------------------------------------------------------------
# Telegram message sending
# --------------------------------------------------------------------------


async def reply_chunked(update: Update, text: str) -> None:
    """Send `text` back to the user, chunking on paragraph boundaries when
    over Telegram's per-message limit."""
    if len(text) <= TELEGRAM_MAX_MESSAGE_CHARS:
        await update.message.reply_text(text)
        return

    # Chunk preferring paragraph boundaries; fall back to hard slicing.
    chunks: list[str] = []
    remaining = text
    while remaining:
        if len(remaining) <= TELEGRAM_MAX_MESSAGE_CHARS:
            chunks.append(remaining)
            break
        split_at = remaining.rfind("\n\n", 0, TELEGRAM_MAX_MESSAGE_CHARS)
        if split_at <= 0:
            split_at = TELEGRAM_MAX_MESSAGE_CHARS
        chunks.append(remaining[:split_at].rstrip())
        remaining = remaining[split_at:].lstrip()

    for chunk in chunks:
        await update.message.reply_text(chunk)


# --------------------------------------------------------------------------
# Handlers
# --------------------------------------------------------------------------


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.info(
        "start cmd user_id=%s username=%s args=%s",
        user.id,
        user.username,
        context.args,
    )
    await update.message.reply_text(WELCOME_MESSAGE)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP_MESSAGE)


async def on_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user = update.effective_user
    text = update.message.text or ""

    # MVP scope: 1:1 DM only. Silently ignore group/channel traffic — circle
    # group facilitation is a later phase.
    if chat.type != ChatType.PRIVATE:
        logger.debug(
            "ignoring non-private message chat_id=%s type=%s", chat.id, chat.type
        )
        return

    if looks_like_injection_attempt(text):
        logger.warning(
            "rejected injection-shaped message from user_id=%s len=%d",
            user.id,
            len(text),
        )
        await update.message.reply_text(INJECTION_REJECTED_MESSAGE)
        return

    caller = Caller.from_update(update)
    logger.info(
        "forward user_id=%s username=%s len=%d",
        caller.telegram_user_id,
        caller.username,
        len(text),
    )

    # Visible typing indicator while hermes thinks. Resend periodically since
    # Telegram clears it after ~5 seconds.
    typing_task = asyncio.create_task(_keep_typing(context, chat.id))
    try:
        try:
            reply_text = await call_hermes(caller, text)
        except httpx.TimeoutException:
            logger.exception("hermes timeout")
            await update.message.reply_text(GENERIC_ERROR_MESSAGE)
            return
        except httpx.HTTPError:
            logger.exception("hermes http error")
            await update.message.reply_text(GENERIC_ERROR_MESSAGE)
            return
        except ValueError:
            logger.exception("hermes returned unexpected shape")
            await update.message.reply_text(GENERIC_ERROR_MESSAGE)
            return
    finally:
        typing_task.cancel()
        try:
            await typing_task
        except asyncio.CancelledError:
            pass

    if not reply_text or not reply_text.strip():
        logger.warning("hermes returned empty content user_id=%s", caller.telegram_user_id)
        await update.message.reply_text(GENERIC_ERROR_MESSAGE)
        return

    try:
        await reply_chunked(update, reply_text)
    except TelegramError:
        logger.exception("failed to deliver reply to user_id=%s", caller.telegram_user_id)


async def _keep_typing(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    while True:
        try:
            await context.bot.send_chat_action(chat_id, ChatAction.TYPING)
        except TelegramError:
            logger.debug("typing action failed (non-fatal) chat_id=%s", chat_id)
        await asyncio.sleep(4.0)


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("unhandled error in handler: %s", context.error)


# --------------------------------------------------------------------------
# Lifecycle
# --------------------------------------------------------------------------


async def post_init(app: Application) -> None:
    me = await app.bot.get_me()
    logger.info(
        "bot online: @%s id=%s name=%r", me.username, me.id, me.first_name
    )
    logger.info("caller marker nonce: %s (rotates each restart)", CALLER_MARKER_NONCE)

    # Minimal command menu — no hermes pollution leaks to the user.
    await app.bot.set_my_commands(
        [
            BotCommand("start", "Begin a conversation"),
            BotCommand("help", "How this bot works"),
        ]
    )


def main() -> None:
    if not BOT_TOKEN:
        sys.stderr.write("PEOTIES_BOT_TOKEN env var is required\n")
        sys.exit(2)
    if not HERMES_API_KEY:
        sys.stderr.write(
            "HERMES_API_KEY env var is required — must match hermes's "
            "API_SERVER_KEY, otherwise session continuity is rejected.\n"
        )
        sys.exit(2)

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text_message))
    app.add_error_handler(on_error)

    logger.info(
        "starting peoties-wrapper polling, backend=%s model=%s",
        HERMES_API_URL,
        HERMES_MODEL,
    )
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
