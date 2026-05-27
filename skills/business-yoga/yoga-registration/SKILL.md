---
name: yoga-registration
description: Onboard new yoga customers with guided intake conversation.
version: 0.1.0
author: Guan (HiRussell)
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [business, yoga, customer-onboarding, intake]
    category: business-yoga
    related_skills: [yoga-chat, yoga-customer-mgmt, yoga-scheduling]
---

# Yoga Registration Skill

Guides the bot through onboarding a new yoga studio customer: collect name, phone, level, goal, and time preference, then write a `customer` entity to the KB. Downstream skills (`yoga-customer-mgmt`, `yoga-scheduling`) read this entity.

## When to Use

- New user adds the bot as a friend (Telegram / WhatsApp).
- Existing user says "我想报名 / 试课 / 加入会员" but no `customer` entity exists for them in KB.
- A `yoga-scheduling` lookup misses because the user is not registered yet — fall through to this skill.

Do NOT use if the customer already exists in KB (use `yoga-customer-mgmt` to update instead).

## Prerequisites

- KB schema must include a `customer` entity type with fields: `name`, `phone`, `level`, `goal`, `preferred_time`. See `references/customer-schema.md`.
- Tools: `knowledge_create` (Hermes native, used to persist the customer entity), `knowledge_query` (to check for duplicates).

## How to Run

Triggered automatically when a new user starts a conversation, or manually by admin pasting "新客户" + intro info. The bot drives the dialog one field at a time; the customer just answers in their own words.

## Quick Reference

| Field | Required | Validation |
|---|---|---|
| `name` | yes | Any non-empty text. Becomes the customer entity title. |
| `phone` | yes | 11 digits (CN mainland) or international `+...` format. |
| `level` | yes | One of: `初学` / `进阶` / `资深`. |
| `goal` | yes | One of: `减压` / `塑形` / `康复` / `其他`. |
| `preferred_time` | yes | One of: `早班` / `午班` / `晚班` / `周末`. |

## Procedure

1. **Greet warmly**. Introduce yourself as the studio assistant. Mention you will ask 5 quick questions (~1 min) to set up their profile.
2. **One field at a time**. Wait for the user reply before moving on. Acknowledge each answer briefly so the user feels heard.
3. **Validate format inline** (phone digit count, level enum). If invalid, politely re-ask with an example.
4. **Read back all 5 answers** when complete. Ask the user to confirm or correct.
5. **Check for duplicates**: `knowledge_query(entity_type="customer", filter={"phone": <phone>})`. If a match exists, do not create — handoff to `yoga-customer-mgmt`.
6. **Persist**: `knowledge_create(entity_type="customer", title=<name>, metadata={phone, level, goal, preferred_time, status: "confirmed", created_via: "yoga-registration"})`.
7. **Close warmly**: "已为你建档 ✓. 接下来我帮你看本周合适的课, 想试试哪个时段?"
8. **Handoff** to `yoga-scheduling` skill (or inline-surface schedule options).

### Off-script handling

- User asks pricing / location mid-flow → answer briefly using `yoga-chat` knowledge, then return to the current field.
- User says "以后再说" / stalls → persist whatever is filled with `status: "pending"`, list incomplete fields in metadata, greet on next contact and resume.

## Pitfalls

- Don't ask all 5 fields in one message — overwhelming for first contact.
- Don't ask for phone in a group chat (privacy). If user added the bot in a group, redirect to DM first.
- Don't invent customer data if the user hesitates. Leave fields blank, ask again later.
- Don't create duplicates. Always `knowledge_query` by phone before `knowledge_create`.
- **Language**: default to English. If the user opens with Chinese (or any CJK characters), mirror Chinese for the entire session. Pick the user's language and stick to it — don't mix languages mid-conversation.

## Verification

After the skill completes successfully:

1. `knowledge_query(entity_type="customer", filter={"phone": <phone>})` returns exactly one entry.
2. All 5 required fields populated (no `None` / empty strings).
3. The customer's title equals the provided `name`.
4. Metadata contains `created_via: "yoga-registration"` so future audits can trace the origin.

If any check fails, log a `SKILL_FAILED` event and surface the issue to the admin — do not silently mark the skill complete.
