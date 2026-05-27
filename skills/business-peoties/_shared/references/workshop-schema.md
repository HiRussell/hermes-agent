# Peoties Workshop KB Schema

A **workshop** is a point-in-time event (single day or multi-day intensive) led by a guest expert — separate from peer circles. Examples: Dr. Sujata Singhi's 3-Day Sound Therapy Training, the 90-min Relax / Restore / Rejuvenate sessions.

Path: `data/business-peoties/<tenant>/workshops/workshop--<slug>--<YYYY-MM-DD>.md`

Example: `workshop--sound-therapy-3day--2026-06-15.md`

Registration files are separate: `workshops/registration--<workshop-slug>--<YYYY-MM-DD>--<member-or-name-slug>.md`

## Workshop Frontmatter

```yaml
---
name: "3-Day Intensive Professional Sound Therapy Training Workshop"
slug: "sound-therapy-3day"
date_start: "2026-06-15"
date_end: "2026-06-17"
duration_days: 3
start_time: "09:00"
end_time: "17:00"
timezone: "+08:00"
location_type: "in-person"          # enum: in-person / online / hybrid
location_address: "TBD — Singapore studio"   # full address for in-person
facilitator_slug: "dr-sujata-singhi"
facilitator_name: "Dr. Sujata Singhi"
description_short: "Learn to practise and teach Himalayan bowl sound healing."
description_full_path: "workshops/workshop--sound-therapy-3day--2026-06-15-description.md"   # long-form sales page content
capacity: 12
registrations_count: 0
price_standard: 3315                # SGD
price_founding_member: 2984          # SGD; founding-100 members get ~10% off
currency: "SGD"
cancellation_policy: ">14 days before: full refund. 7-14 days: 50% refund. <7 days: no refund."
status: "open"                       # enum: open / waitlist / closed / cancelled
created_at: "2026-05-01T00:00:00+08:00"
updated_at: "2026-05-01T00:00:00+08:00"
---
```

## Workshop Body

```markdown
Led by Dr. Sujata Singhi, this 3-day intensive teaches practitioners to use Himalayan singing bowls for sound healing sessions with clients. Suitable for yoga teachers, bodyworkers, and wellness practitioners adding sound work to their offering.

**What you'll learn**: bowl selection + tuning, intentional placement, session structuring, contraindications, professional ethics.

**You leave with**: a practitioner foundation certificate + ongoing community access for questions.
```

## Registration Frontmatter

Path: `data/business-peoties/<tenant>/workshops/registration--sound-therapy-3day--2026-06-15--anna-tan-7a3f.md`

```yaml
---
workshop_slug: "sound-therapy-3day"
workshop_date: "2026-06-15"
registrant_type: "member"           # enum: member / non-member
registrant_slug: "anna-tan-7a3f"     # nullable if non-member
registrant_name: "Anna Tan"
registrant_email: "anna@example.com"
registrant_phone: "+65 9XXX XXXX"
price_charged: 2984                  # SGD; reflects founding-member discount if applied
payment_status: "pending"            # enum: pending / paid / refunded / cancelled
payment_method: null                 # filled when paid: paynow / bank-transfer / stripe / cash
registered_at: "2026-05-28T10:30:00+08:00"
cancelled_at: null
refund_status: null                  # null / partial-refund / full-refund / no-refund
reminder_cron_id: null               # 24h-before reminder cronjob ID
---
```

## Registration Body

Optional: registrant's notes ("First time at a sound healing workshop"), or staff notes ("Member referred by Anna T from Midlife Circle").

## Lifecycle

1. **Created** by `peoties-circle-cohort` workshop-register flow with `payment_status: pending`.
2. **Payment confirmed** by founder (manual or via payment webhook in future) → `payment_status: paid`, `payment_method` filled.
3. **Cancelled** by registrant: `cancelled_at` filled, `refund_status` determined by `cancellation_policy` of the workshop.
4. **Reminder** sent automatically 24h-before via `cronjob` (id stored in `reminder_cron_id`).

## Role-based access

- **Founder**: full R/W on workshops + registrations.
- **Facilitator (this workshop)**: R on registration roster (names, contact for logistics); ❌ no access to other workshops.
- **Registrant**: R own registration; can cancel (subject to policy).
- **Other member**: R on workshop info (date, price, description); ❌ no access to registration list / other registrants.
