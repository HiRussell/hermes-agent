# Peoties Facilitator KB Schema

A **facilitator** is a human (paid or volunteer) trained by Jenny to hold space in a peer circle. Different from a **workshop expert** (e.g. Dr. Sujata Singhi for Sound Therapy) — both can share this schema with `role: facilitator` or `role: workshop-expert`.

Path: `data/business-peoties/<tenant>/facilitators/facilitator--<slug>.md`

Example: `facilitator--jenny-chew.md` (founder herself), `facilitator--mei-lin-7c2a.md` (circle facilitator), `facilitator--dr-sujata-singhi.md` (workshop expert).

## Frontmatter

```yaml
---
name: "Mei Lin"
display_name_zh: null               # optional Mandarin name
slug: "mei-lin-7c2a"
role: "facilitator"                  # enum: founder / facilitator / workshop-expert
status: "active"                    # active / on-leave / departed
languages: ["en", "zh"]              # en / zh / ms / ta
specialties: ["midlife-transition", "caregiving"]   # circle topics they can facilitate
bio_short: "Trained facilitator with 6 years in group therapy + somatic work. Holds Midlife Circle 1."
bio_zh: null
training:
  - "RYT-200 (2019)"
  - "Peoties facilitator certification (2025)"
  - "Hakomi method, intro level (2023)"
contact_email: "mei.lin@peoties.com"   # internal-only
gateway_user_id: "tg:9876543210"
circles_facilitated: ["midlife-1"]    # list of circle slugs they currently facilitate
cohorts_active: ["cohort--midlife-1--w2"]   # current cohorts (for permission checks)
created_at: "2026-01-15T00:00:00+08:00"
updated_at: "2026-04-01T00:00:00+08:00"
---
```

## Body

```markdown
Mei trained as a clinical psychologist before stepping back from formal practice to focus on community work. She brings a non-pathologizing, peer-leveling presence to circles — members say her quiet attention "makes it feel safe to not have it all figured out."

Facilitates: Midlife Circle 1 (currently Wave 2). Available for circle matching consultations with Jenny.
```

## Role: workshop-expert example

For a workshop-only expert (no peer circle role), e.g. Dr. Sujata Singhi:

```yaml
---
name: "Dr. Sujata Singhi"
slug: "dr-sujata-singhi"
role: "workshop-expert"
status: "active"
languages: ["en", "hi"]
specialties: ["sound-therapy", "himalayan-bowl-healing"]
bio_short: "Practitioner and trainer in Himalayan bowl sound therapy with 15+ years experience."
workshops_led: ["sound-therapy-3day"]
---
```

Workshop experts have no `circles_facilitated` / `cohorts_active` — they only appear in `workshops/`.

## Role-based access

- **Founder**: R/W on all facilitator records.
- **Facilitator self**: R/W on own record (bio, training, contact); ❌ on `circles_facilitated` / `cohorts_active` (those are admin assignments).
- **Member**: R short bio + specialties + language (used to give applicants visibility into who'd facilitate them); ❌ contact_email, training detail, internal notes.
- **Anyone else**: same as member, public-facing read of bio + role.
