# Peoties Member KB Schema

Path: `data/business-peoties/<tenant>/members/member--<slug>.md`

`<slug>` = lowercase firstname-lastname-4digit (e.g. `anna-tan-7a3f`) OR firstname-4digit if `privacy_preference: pseudonymous` (e.g. `anna-7a3f`).

## Frontmatter

```yaml
---
name: "Anna Tan"                   # required; may be first-name only if pseudonymous
email: "anna@example.com"           # required, primary contact
phone: "+65 9XXX XXXX"              # required; never shared in circle group chat
city: "Singapore"                   # required: Singapore / Kuala Lumpur / Jakarta / other
life_stage: "midlife-transition"   # required, enum: parenting / midlife-transition / leadership / health-change / career-pivot / caregiving / other
join_motivation: "Feeling stretched between aging parents and teenagers — want to talk with people in similar season."   # required, open text in user's own words
circle_topic_interest: ["midlife", "caregiving"]   # required, list
wellness_experience: "Years of journaling, occasional therapy. Read The Wisdom of Insecurity."   # optional, free text
privacy_preference: "standard"     # required, enum: pseudonymous / standard
availability_for_circle: ["weekday-evenings", "weekend-mornings"]   # required, list from: weekday-mornings / weekday-lunch / weekday-evenings / weekend-mornings / weekend-afternoons / weekend-evenings
status: "applicant"                # required, enum: applicant / member / paused / paused-crisis-detected / left / graduated
membership_tier: null              # nullable, enum: founding-100 / standard / null. Founder-only field.
assigned_circle: null              # nullable, set by peoties-circle-cohort match. Slug of circle--<...>.md.
consent_kb_journey_notes: false    # required, explicit consent for team to add private journey context
consent_email_updates: false       # required, explicit consent for community emails
created_at: "2026-05-28T10:30:00+08:00"   # required, ISO 8601 SGT
updated_at: "2026-05-28T10:30:00+08:00"   # required, updated on any patch
gateway_user_id: "tg:1234567890"   # optional, channel-specific ID
---
```

## Body

A neutral 1-2 sentence summary written by `peoties-member-intake` using ONLY what the user shared. No inference:

```markdown
Midlife transition, navigating caregiving for aging parents while raising teenagers. Looking for a circle of peers in similar season; values weekday evening availability.
```

Followed by sections appended over time (only by founder / facilitator / member themselves, per role permissions):

### `## Journey Notes`

```markdown
## Journey Notes

- 2026-05-28 (Jenny): Articulate, ready for circle conversation. Strong fit for Midlife Circle 1 (Wave 2, forming).
- 2026-06-10 (Mei, facilitator): First session went well. Anna shared openly about caregiving fatigue.
```

### `## Change Log`

```markdown
## Change Log

- 2026-05-28: member self-updated availability_for_circle from [weekday-evenings] to [weekday-evenings, weekend-mornings]
- 2026-06-15: founder updated status from applicant → member after circle match confirmed
```

### `## Open Requests` (rare, for things needing founder action)

```markdown
## Open Requests

- 2026-07-20: member requested journey note deletion. Founder action required by 2026-07-22.
```

## Role-based field access

| Field group | Founder | Facilitator (of member's cohort) | Member-self | Anyone else |
|---|---|---|---|---|
| `name`, `city`, `circle_topic_interest`, `availability_for_circle`, `join_motivation` | ✓ R/W | ✓ R | ✓ R/W | ❌ |
| `email`, `phone` | ✓ R/W | ✓ R | ✓ R/W (w/ re-confirm) | ❌ |
| `life_stage`, `wellness_experience` | ✓ R/W | ✓ R | ✓ R/W | ❌ |
| `privacy_preference` | ✓ R/W | ✓ R | ✓ R/W (w/ re-confirm) | ❌ |
| `status`, `assigned_circle`, `membership_tier` | ✓ R/W | ✓ R | ✓ R (self-pause only for status) | ❌ |
| `consent_*` flags | ✓ R/W | ✓ R | ✓ R/W (own consent) | ❌ |
| `## Journey Notes` | ✓ R/W (append) | ✓ R/W (append, own cohort only) | ✓ R (folded summary) | ❌ |
| `created_at`, `created_via`, `gateway_user_id` | ✗ immutable | ✗ immutable | ✗ immutable | — |
