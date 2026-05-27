---
name: yoga-registration
description: Onboard new yoga customers with guided intake conversation.
version: 0.2.0
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

Guides the bot through onboarding a new yoga studio customer: collect name, phone, level, goal, and time preference, then write a customer markdown file to the KB. Downstream skills (`yoga-customer-mgmt`, `yoga-scheduling`) read these files.

## When to Use

- New user starts a conversation with the bot (Telegram / WhatsApp / CLI).
- Existing user says "I want to register / 我想报名 / 试课 / 加入会员" but no customer file exists for them.
- A `yoga-scheduling` lookup misses because the user is not registered yet — fall through to this skill.

Do NOT use if the customer already has a file in `data/business-yoga/customers/` (use `yoga-customer-mgmt` to update instead).

## Prerequisites

- KB directory exists: `data/business-yoga/customers/`. See `references/customer-schema.md` for the markdown schema.
- Hermes builtin tools: `search_files` (to check for duplicate phone numbers), `read_file` (to inspect existing customer files), `write_file` (to persist the new customer markdown).

## How to Run

Triggered automatically when a new user starts a conversation, or manually by admin pasting "new customer" + intro info. The bot drives the dialog one field at a time; the customer answers in their own words.

## Quick Reference

| Field | Required | Validation |
|---|---|---|
| `name` | yes | Any non-empty text. Becomes the customer file title and slug. |
| `phone` | yes | 11 digits (CN mainland) or international `+...` format. Used as primary dedup key. |
| `level` | yes | One of: `beginner` / `intermediate` / `advanced` (or zh: `初学` / `进阶` / `资深`). |
| `goal` | yes | One of: `destress` / `tone` / `recovery` / `other` (or zh: `减压` / `塑形` / `康复` / `其他`). |
| `preferred_time` | yes | One of: `morning` / `noon` / `evening` / `weekend` (or zh: `早班` / `午班` / `晚班` / `周末`). |

## Procedure

1. **Greet warmly**. Introduce yourself as the studio assistant. Mention you will ask 5 quick questions (~1 min) to set up their profile.
2. **One field at a time**. Wait for the user reply before moving on. Acknowledge each answer briefly so the user feels heard.
3. **Validate format inline** (phone digit count, level/goal/preferred_time enum). If invalid, politely re-ask with an example.
4. **Read back all 5 answers** when complete. Ask the user to confirm or correct.
5. **Check for duplicates** with `search_files`:
   - `search_files target='files' path='data/business-yoga/customers/' pattern='phone: <phone>'`
   - If any match found, do NOT create a new file — handoff to `yoga-customer-mgmt` ("looks like you're already registered, let me pull up your profile").
6. **Persist** with `write_file`:
   - Path: `data/business-yoga/customers/customer--<slug>.md` where `<slug>` is the name lowercased + hyphenated + 4-digit random suffix (e.g. `customer--wendy-zhang-7a3f.md`).
   - Content: markdown with frontmatter (`name`, `phone`, `level`, `goal`, `preferred_time`, `status: confirmed`, `created_via: yoga-registration`, `created_at: <ISO timestamp>`) + a one-sentence summary body.
   - See `references/customer-schema.md` for the exact template.
7. **Close warmly**: "All set! ✓ I'll help you find a class this week — which time slot looks good?" (zh: "已为你建档 ✓. 接下来我帮你看本周合适的课, 想试试哪个时段?").
8. **Handoff** to `yoga-scheduling` skill (or inline-surface schedule options if the user is ready).

### Off-script handling

- User asks pricing / location mid-flow → answer briefly using `yoga-chat` knowledge, then return to the current field.
- User says "later" / "以后再说" / stalls → persist whatever is filled with `status: pending` in frontmatter, list incomplete fields in metadata, greet on next contact and resume.

## Pitfalls

- Don't ask all 5 fields in one message — overwhelming for first contact.
- Don't ask for phone in a group chat (privacy). If user added the bot in a group, redirect to DM first.
- Don't invent customer data if the user hesitates. Leave fields blank, ask again later.
- Don't create duplicate files. Always `search_files` by phone before `write_file`.
- **Language**: default to English. If the user opens with Chinese (or any CJK characters), mirror Chinese for the entire session. Pick the user's language and stick to it — don't mix languages mid-conversation.

## Verification

After the skill completes successfully:

1. `search_files target='files' path='data/business-yoga/customers/' pattern='phone: <phone>'` returns exactly one file.
2. The file's frontmatter has all 5 required fields populated (no empty strings).
3. The file's frontmatter contains `created_via: yoga-registration` so future audits can trace the origin.
4. The filename matches the `customer--<slug>.md` pattern.

If any check fails, surface the issue to the admin via `send_message` (if gateway configured) or print a clear error — do not silently mark the skill complete.
