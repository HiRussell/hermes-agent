---
name: yoga-group-mgmt
description: Manage bot behavior in yoga studio group chats.
version: 0.1.0
author: Guan (HiRussell)
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [business, yoga, group-chat, broadcasting]
    category: business-yoga
    related_skills: [yoga-chat, yoga-scheduling]
---

# Yoga Group Management Skill

Governs bot behavior when it's a member of a group chat (e.g. "Early Bird Class Group", "Weekend Warriors", "VIP Members"). The default posture is **passive**: read the room, only reply when explicitly @mentioned, never auto-process sensitive flows (registration, profile updates, phone collection) in a group. Used together with `cronjob` for broadcasting class reminders.

## When to Use

- The bot is in a group chat (vs DM 1:1).
- Triggered automatically by the gateway when a message arrives in a group context.
- For scheduled broadcasts (class reminders, weekly schedule, holiday closures).

Do NOT use for:
- 1:1 customer interactions — use `yoga-chat` / `yoga-registration` / `yoga-customer-mgmt` / `yoga-scheduling`.
- Anything requiring private data (phone, payment) — redirect to DM.

## Prerequisites

- The gateway must surface a `chat_type: group` signal in the incoming envelope (Telegram / WhatsApp / Feishu all support this).
- Tools: `send_message` (for broadcasts), `cronjob` (for scheduled sends), `search_files` + `read_file` (to look up class schedule for the reminder).
- Optional: a `data/business-yoga/groups/group--<id>.md` file per known group, describing its purpose, members (high-level), and broadcast preferences.

## How to Run

Passively activates when a group message arrives. The bot reads, classifies, and decides between four actions: stay silent, brief inline answer, redirect to DM, or trigger a scheduled flow.

## Quick Reference

| Group event | Bot action |
|---|---|
| Message not @mentioning bot | **Stay silent** (read only, no reply) |
| Message @mentions bot + asks an info question | Brief inline answer (≤3 sentences) via `yoga-chat` knowledge |
| Message @mentions bot + asks scheduling | "Let me DM you — booking needs your profile" |
| Message @mentions bot + asks registration | "Welcome! DM me and I'll set you up in 1 min" |
| Customer sends phone / private info in group | "Heads up — let me DM you so we keep your info private" + redirect |
| `cronjob` fires for daily class reminder | Broadcast next day's classes via `send_message` |
| `cronjob` fires for class-specific reminder | Broadcast 2h before class start ("In 2h: Vinyasa with Lily — see you there!") |

## Procedure

### Reactive (responding to group message)

1. **Check group context**: confirm `chat_type == "group"`. If wrong context, fall through to default 1:1 skills.
2. **Was the bot @mentioned?** If not, return silently — log to `memory` for awareness but DO NOT respond.
3. **Classify intent**: info / scheduling / registration / private-data-leak / chitchat.
4. **Act per Quick Reference**:
   - **Info**: load relevant KB file (`search_files` + `read_file`), reply inline ≤3 sentences. No source citation needed in group (keep it casual).
   - **Scheduling / registration**: do NOT process in group. Reply with a DM pivot: "DM'd you ✓" (and actually `send_message` privately to the user).
   - **Private-data-leak**: customer typed their phone / payment in group → reply IMMEDIATELY: "Please don't share that in the group — DM me and I'll handle it privately." Do NOT echo the private data.
   - **Chitchat**: brief friendly reply (1 sentence). Don't lecture.

### Proactive (scheduled broadcast)

1. **Cron fires** (e.g. daily 6pm: tomorrow's class schedule).
2. **Load schedule**: `search_files` appointments where `start_at` is tomorrow.
3. **Compose** a short bulletin: "📅 Tomorrow: 7am Vinyasa (Lily) · 9am Hatha (Mei) · 6pm Yin (Lily). DM me to book."
4. **Send** via `send_message` to the group ID.
5. **Frequency cap**: ≤1 broadcast per group per day. If multiple cron jobs fire (daily schedule + class reminder), batch into single message.

## Pitfalls

- **Don't be chatty**. Group members will mute the bot if it talks too much. The bar: would a thoughtful human assistant chime in on this? If no, stay silent.
- **Never ask for phone in group**. Phone collection = `yoga-registration` in DM only. If a flow needs phone, pivot the user to DM first.
- **Never expose other customers' info in group**. "X booked Wednesday 7am" → never. Group is public; private profiles are private.
- **Don't echo accidental leaks**. If a customer pastes their phone into the group, the bot's reply must NOT repeat the phone (even as part of a redirect). Just say "let's DM".
- **Respect broadcast frequency**. Daily schedule + last-minute reminder = OK. Multiple promos / multiple reminders for one class = spammy.
- **No DMs from group context unless user explicitly invited**. The bot can `send_message` to a user privately only if the user @mentioned the bot in the group (implicit consent to engage) OR is already a customer (existing relationship).
- **Language**: default to English. If the group's primary language (inferred from majority of recent messages) is Chinese, default to Chinese for that group. Stay consistent within the group.

## Verification

After a reactive turn:
1. Bot replied only if @mentioned OR the message was a private-data-leak warning.
2. No private data was echoed in any reply.
3. Scheduling / registration intents were redirected to DM, not processed inline.

After a broadcast:
1. The message went to the correct group ID.
2. The content references only public info (no individual customer names without consent).
3. Frequency cap respected (≤1 broadcast per group per day from this skill).

If verification fails (e.g. bot accidentally replied without @mention), log to `memory` for human review.
