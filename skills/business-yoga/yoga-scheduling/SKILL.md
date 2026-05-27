---
name: yoga-scheduling
description: Book, reschedule, or cancel yoga classes for customers.
version: 0.1.0
author: Guan (HiRussell)
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [business, yoga, scheduling, appointments]
    category: business-yoga
    related_skills: [yoga-registration, yoga-chat, yoga-customer-mgmt]
---

# Yoga Scheduling Skill

Handles class booking, rescheduling, cancellation, and availability queries. Reads tutor availability + customer history from KB markdown, writes appointment markdown files. Optionally schedules a class reminder via `cronjob` 24h before the session.

## When to Use

- Customer says: "Book me 7am Wednesday with Lily" / "Reschedule my Friday class to Thursday" / "Cancel my Saturday session" / "Is Lily free Tuesday morning?"
- Customer-driven booking after `yoga-registration` completes.
- Staff says: "Move all of X's classes next week to a different tutor".

Do NOT use for:
- New customer onboarding (use `yoga-registration` first — must have a customer profile to book).
- Pricing / class catalog questions (use `yoga-chat`).
- Customer profile updates (use `yoga-customer-mgmt`).

## Prerequisites

- KB directories exist: `data/business-yoga/{customers,tutors,appointments}/`. Schemas in `references/`.
- Customer being booked has a profile in `customers/`. If not, handoff to `yoga-registration`.
- Hermes builtin tools: `search_files`, `read_file`, `write_file`, `patch`, `cronjob` (for reminders).

## How to Run

Triggered by a scheduling intent in the user message. The bot classifies intent (book / reschedule / cancel / query), checks availability, and writes or modifies appointment files.

## Quick Reference

| Intent | Tool sequence | KB writes |
|---|---|---|
| Query "Is X free at time Y?" | `search_files` appointments + `read_file` tutor schedule | none |
| Book new class | check availability → `write_file` new appointment + optional `cronjob` reminder | 1 new appointment file |
| Reschedule | check new slot availability → `patch` appointment + reschedule `cronjob` | 1 modified appointment file |
| Cancel | check 24h policy → `patch` appointment status to `cancelled` + delete `cronjob` | 1 modified appointment file |

### Appointment file naming

`data/business-yoga/appointments/appointment--<YYYY-MM-DD>--<HH-MM>--<customer-slug>--<tutor-slug>.md`

Example: `appointment--2026-05-28--07-00--wendy-tan-7a3f--lily-tan.md`

### Frontmatter

- `customer_slug`, `customer_name`
- `tutor_slug`, `tutor_name`
- `start_at` (ISO 8601 datetime)
- `duration_minutes` (default 60)
- `class_type` (Hatha / Vinyasa / Yin / Hot / private)
- `status` (`confirmed` / `cancelled` / `completed` / `no-show`)
- `cancellation_policy_cutoff` (ISO datetime, default `start_at - 24h`)
- `created_at`, `updated_at`

### Cancellation policy

- ≥24h before `start_at`: free cancellation, refund credit.
- <24h before `start_at`: counts as a used session, no refund.
- < 2h before: also notify the tutor via `send_message` (if gateway configured).

## Procedure

### Booking (new class)

1. **Verify customer exists**: `search_files target='files' path='data/business-yoga/customers/' pattern='<customer name or phone>'`. If no match → handoff to `yoga-registration`.
2. **Parse the request**: extract `tutor`, `start_at` (date + time), `class_type` (default to tutor's primary type if omitted).
3. **Check tutor availability**:
   - `read_file path='data/business-yoga/tutors/tutor--<tutor-slug>.md'` for their weekly availability.
   - `search_files target='files' path='data/business-yoga/appointments/' pattern='start_at: <YYYY-MM-DDTHH:MM>'` — filter where `tutor_slug` matches. If any with `status: confirmed` exists, the slot is taken.
4. **Conflict check on customer side too**: `search_files` appointments where `customer_slug` matches + `start_at` overlaps. Customer might have another class at the same time.
5. **If conflict**: explain ("Lily is teaching Vinyasa at 7am Wed — would 7am Thursday work, or a different tutor?"). Don't book.
6. **If free**: confirm with user ("Booking Lily, 7am Wed May 29, Vinyasa class. Confirm?").
7. **On confirm**, `write_file` the appointment markdown (see naming + frontmatter above).
8. **Schedule reminder** via `cronjob`: trigger 24h before `start_at`, action = `send_message` to customer ("Reminder: your yoga class with Lily is tomorrow 7am — see you there!").
9. **Acknowledge**: "Booked ✓. See you Wed 7am with Lily. I'll send a reminder 24h before."

### Reschedule

1. **Locate existing appointment**: `search_files` by customer + old `start_at`.
2. **Check new slot availability** (same conflict logic as booking).
3. **Confirm change** with user.
4. **Patch the file**: update `start_at`, `updated_at`, append change log.
5. **Reschedule `cronjob`**: delete old reminder, create new.
6. **Acknowledge**: "Moved to Thu 7am ✓."

### Cancellation

1. **Locate appointment** (same as Reschedule).
2. **Read** to check `start_at` vs now.
3. **Apply policy**:
   - ≥24h before: free cancellation, refund a credit (note in frontmatter: `refund_status: credited`).
   - <24h: explain policy ("Within 24 hours, this counts as a used session — sorry I can't refund. Cancel anyway?").
4. **Patch `status` to `cancelled`** + `cancelled_at: <ISO>` + reason if user gave one.
5. **Delete the reminder `cronjob`**.
6. **If <2h before**, notify tutor: `send_message` to tutor's gateway ID.
7. **Acknowledge**: "Cancelled ✓. [Refund credited / per policy, this counts as a used session.]"

## Pitfalls

- **Double-booking is the worst failure mode**. Always do BOTH the tutor-side conflict check AND the customer-side conflict check. Never skip step 4 of booking.
- **Don't book past the cancellation window for a competing customer**. If Wendy wants 7am Wed but X already booked it ≥24h ago, X has priority — offer alternatives to Wendy.
- **Cron reminder leak**: if a cancellation removes an appointment, also remove its reminder cron — otherwise the customer gets a "see you tomorrow" ping for a class they cancelled.
- **Time zones**: assume studio local time (configured in `data/business-yoga/studio-info/hours.md`). Don't accept ambiguous "7am" if customer is in a different TZ — confirm.
- **Tutor availability is per-tutor**, not global. Lily's "Wed 7am" might be Hatha but Yin (Wed 7am) is on a different tutor. Always match the right tutor file.
- **No-show vs cancel**: after a class ends, if status was still `confirmed`, batch job (not this skill) updates to `completed` or `no-show`. This skill doesn't handle that.
- **Language**: default to English. If the user opens with Chinese (or any CJK characters), mirror Chinese for the entire session.

## Verification

After a booking:
1. Exactly one new file in `appointments/` with the correct naming pattern.
2. Frontmatter has all required fields (`customer_slug`, `tutor_slug`, `start_at`, `status: confirmed`).
3. No conflicting appointment in the same `start_at` for the same `tutor_slug` (re-`search_files` to double-check).
4. A `cronjob` exists scheduled for `start_at - 24h`.

After a cancellation:
1. The target file has `status: cancelled` and `cancelled_at` populated.
2. The original `cronjob` reminder is removed (verify via `cronjob list`).
3. If <2h to class, tutor was notified.

If any verification fails, surface to the admin and DO NOT mark the action complete to the customer.
