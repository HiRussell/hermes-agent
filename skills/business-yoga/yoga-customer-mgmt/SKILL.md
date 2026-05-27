---
name: yoga-customer-mgmt
description: Query and update customer profiles by name or phone.
version: 0.1.0
author: Guan (HiRussell)
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [business, yoga, customer-management, kb-mutation]
    category: business-yoga
    related_skills: [yoga-registration, yoga-chat, yoga-scheduling]
---

# Yoga Customer Management Skill

Looks up and updates existing customer profile files in `data/business-yoga/customers/`. Two primary callers:

1. **Studio staff / owner** asks "Show me Wendy's profile" / "Update X's phone to Y" — full access.
2. **Customer themselves** says "I want to change my number" — self-service for their own record only.

The skill enforces a role distinction: full profile is visible to staff, redacted (no phone, no payment history) to the customer themselves.

## When to Use

- Owner/staff asks any customer-specific question that requires loading a profile.
- Customer says "my phone changed to X" / "update my preferred time to evening" / "what level am I in your records?"

Do NOT use for:
- New customer registration (use `yoga-registration`).
- Class booking / cancellation (use `yoga-scheduling`).
- Generic info questions (use `yoga-chat`).

## Prerequisites

- KB directory exists: `data/business-yoga/customers/`. Schema in `references/customer-schema.md`.
- Hermes builtin tools: `search_files` (lookup by name/phone), `read_file` (load profile), `patch` (modify frontmatter or body in place).
- Caller role context: the bot must know whether the user is staff or a customer. By default, **assume customer self-service** (lower privilege); only treat as staff if the conversation context includes a staff identifier or if the user is in a known staff list.

## How to Run

Triggered when an existing customer or staff member needs to read/update a customer profile. Steps differ based on role and intent (read vs update).

## Quick Reference

| Action | Role | Tool | Notes |
|---|---|---|---|
| Read own profile (redacted) | customer | `search_files` → `read_file` | Hide phone, hide other customers' attendance |
| Read any profile (full) | staff | `search_files` → `read_file` | Full fields visible |
| Update own profile (name, preferred_time, goal, level) | customer | `patch` on frontmatter | Self-service edits limited to soft fields |
| Update phone (own) | customer | `patch` + confirm via OTP-like step | Phone change is sensitive (impacts dedup), require re-confirm |
| Update any field (any profile) | staff | `patch` | Full write access |
| Mark status (active / paused / churned) | staff only | `patch` on `status` field | Customer can't self-pause / self-churn |

## Procedure

### Lookup (read)

1. **Identify** the target customer from the user message: a name, phone, or "me" (for self-service).
2. **Search**: `search_files target='files' path='data/business-yoga/customers/' pattern='<name or phone>'`. Match against `name` frontmatter or `phone` field.
3. **Disambiguate** if multiple matches: use `clarify` ("I found 2 Wendy's — Wendy Z. (139xxx) or Wendy C. (138xxx)?").
4. **Read** with `read_file`.
5. **Render** based on role:
   - **Staff**: full profile, formatted as a brief card (name / phone / level / goal / preferred_time / status / last_visit).
   - **Customer self-service**: redact phone (show last 4 digits only) and exclude any other-customer references.

### Update

1. **Identify** target customer (same as Lookup step 1-4).
2. **Confirm change** with the user before writing: "I'm updating preferred_time from `evening` to `morning` — confirm?"
3. **Apply** with `patch`:
   - Frontmatter field change: `patch path='customers/customer--<slug>.md' search='preferred_time: <old>' replace='preferred_time: <new>'`
   - Update `updated_at: <ISO timestamp>` in frontmatter at the same time.
4. **Log** the change in the file body (append `## Change Log` section):
   - `- 2026-05-27: customer self-updated preferred_time from evening → morning`
5. **Acknowledge** to user: "Updated ✓. Your preferred time is now `morning`."

### Sensitive: phone change

Phone is the dedup key. If a customer wants to change phone:
1. Confirm via two-step: "To confirm, your new phone is `<new>`? Reply YES to update."
2. After YES, also `search_files` with the new phone to ensure no other customer already uses it (collision detection).
3. If collision: stop, escalate to staff ("This number is already on file under another profile. Let me get the owner to help sort this out.").

## Pitfalls

- **Privacy**: customer self-service can ONLY see/edit their own profile. Never leak other customers' info — not even names ("Hmm, is your friend Wendy in our system?" → "I can't share that, but they can ask me directly.").
- **Confirm before write**: every `patch` call must be preceded by an explicit user confirmation. Don't write silently.
- **Don't delete profiles**: even at staff request, `patch` the `status` to `churned`. Hard delete only via owner manual action.
- **Don't update `created_via` or `created_at`** — those are provenance fields, immutable.
- **Status field is staff-only**: customer can update soft fields (name, preferred_time, goal, level) but not status / billing / membership_tier.
- **Language**: default to English. If the user opens with Chinese (or any CJK characters), mirror Chinese for the entire session.

## Verification

After a read:
1. Response contains only fields appropriate to the caller's role (no phone leak to customer self-service).
2. No other customer's info appeared in the response.

After an update:
1. The target file's frontmatter has the new value.
2. `updated_at` timestamp matches now (within last minute).
3. The body has a Change Log entry for this update.
4. No other customer's file was modified.
