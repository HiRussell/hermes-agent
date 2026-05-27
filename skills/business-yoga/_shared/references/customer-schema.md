# Customer KB Schema

Path: `data/business-yoga/customers/customer--<slug>.md`

`<slug>` = lowercased name with hyphens + 4-digit random suffix (e.g. `wendy-tan-7a3f`).

## Frontmatter

```yaml
---
name: "Wendy Tan"                 # required, customer's chosen name (display)
phone: "+65 9123 4567"            # required, primary dedup key (SG: 8 digits w/ +65; or intl: +country)
level: "beginner"                 # required, enum: beginner / intermediate / advanced (zh: 初学/进阶/资深)
goal: "destress"                  # required, enum: destress / tone / recovery / other (zh: 减压/塑形/康复/其他)
preferred_time: "morning"         # required, enum: morning / noon / evening / weekend (zh: 早班/午班/晚班/周末)
status: "confirmed"               # required, enum: pending / confirmed / paused / churned. Customer self-service can't change.
created_at: "2026-05-27T15:30:00Z"  # required, ISO 8601 UTC. Immutable.
updated_at: "2026-05-27T15:30:00Z"  # required, ISO 8601 UTC. Updated on any patch.
created_via: "yoga-registration"  # required, provenance. Immutable.
gateway_user_id: "tg:1234567890"  # optional, the channel-specific user ID (Telegram chat_id, WhatsApp number, etc.)
membership_tier: null             # optional, enum: trial / monthly / annual / lifetime / null. Staff-only edit.
total_sessions: 0                 # optional, counted from confirmed appointments. Updated by batch job, not this skill.
last_visit: null                  # optional, ISO timestamp of last completed appointment.
---
```

## Body

A one-sentence summary used by `search_files` for keyword matches:

```markdown
Beginner-level yoga customer focused on destress, prefers morning classes.
```

Optionally a `## Change Log` section appended by `yoga-customer-mgmt`:

```markdown
## Change Log

- 2026-05-28: customer self-updated preferred_time from morning → evening
- 2026-06-01: staff updated status from confirmed → paused (extended travel)
```

## Read/Write Conventions

| Field group | Customer self-service | Staff |
|---|---|---|
| `name`, `goal`, `level`, `preferred_time` | ✓ edit | ✓ edit |
| `phone` | ✓ edit (with re-confirm) | ✓ edit |
| `status`, `membership_tier`, `total_sessions`, `last_visit` | ✗ read-only | ✓ edit |
| `created_at`, `created_via`, `gateway_user_id` | ✗ immutable | ✗ immutable |
| `updated_at` | auto-set on patch | auto-set on patch |
