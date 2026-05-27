# Appointment KB Schema

Path: `data/business-yoga/appointments/appointment--<YYYY-MM-DD>--<HH-MM>--<customer-slug>--<tutor-slug>.md`

Filename encodes the time + customer + tutor for fast `search_files` lookups by any dimension.

Example: `appointment--2026-05-28--07-00--wendy-zhang-7a3f--lily-chen.md`

## Frontmatter

```yaml
---
customer_slug: "wendy-zhang-7a3f"
customer_name: "Wendy Zhang"
tutor_slug: "lily-chen"
tutor_name: "Lily Chen"
start_at: "2026-05-28T07:00:00+08:00"     # ISO 8601 with TZ. Studio's local TZ.
duration_minutes: 60
class_type: "Vinyasa"                      # one of tutor.specialty
status: "confirmed"                        # enum: confirmed / cancelled / completed / no-show
cancellation_policy_cutoff: "2026-05-27T07:00:00+08:00"  # start_at - 24h
refund_status: null                        # set on cancellation: credited / forfeited / null
cancelled_at: null
cancelled_reason: null
reminder_cron_id: null                     # set by yoga-scheduling when cronjob created
created_at: "2026-05-25T14:30:00Z"
updated_at: "2026-05-25T14:30:00Z"
---
```

## Body

Optional: customer's notes ("focus on hip openers please") or staff's notes ("first session — go gentle on alignment cues").

## Lifecycle

1. **Created** by `yoga-scheduling` with `status: confirmed`.
2. **Modified** by `yoga-scheduling` on reschedule (`start_at` + `updated_at` change) or cancel (`status: cancelled` + `cancelled_at` + `refund_status`).
3. **Completed** by a batch job after the class end time passes — `status: completed` (and `last_visit` on the customer is updated).
4. **No-show** by the same batch job if the customer didn't show up (tracked manually by staff or via attendance tool — future feature).

## Conflict detection

Before creating a new appointment, `yoga-scheduling` must verify NO existing file matches BOTH:
- Same `tutor_slug` AND same `start_at` AND `status: confirmed`
- Same `customer_slug` AND `start_at` overlapping (start_at to start_at + duration_minutes) AND `status: confirmed`

If either matches, refuse to create and explain to the user.
