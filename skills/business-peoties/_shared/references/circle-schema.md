# Peoties Circle KB Schema

A **circle** is a stable group of 5-8 members + 1-2 facilitators who meet weekly. Circles persist across multiple cohorts (waves of structured programs). Use `cohort--<circle-slug>--<wave>.md` for the time-bound program a circle is currently running.

Path: `data/business-peoties/<tenant>/circles/circle--<slug>.md`

`<slug>` = topic + sequence number (e.g. `parenting-1`, `midlife-2`, `leadership-1`).

## Frontmatter

```yaml
---
name: "Midlife Transitions Circle 1"
slug: "midlife-1"
topic: "midlife-transition"        # primary topic; circles can have secondary topics
secondary_topics: ["caregiving", "career-pivot"]
city: "Singapore"                   # primary city; circle can be remote-friendly
remote_friendly: false              # if true, members in other cities can join
primary_language: "en"              # en / zh / ms / ta
meeting_schedule:
  day: "wednesday"
  time: "19:30"
  duration_minutes: 90
  timezone: "+08:00"
capacity: 8
current_size: 5                     # incremented when member joins, decremented when leaves/graduates
status: "active"                    # enum: forming / active / completing / graduated / paused
formed_at: "2026-04-01"             # ISO date
graduated_at: null                  # set when status → graduated
facilitators: ["mei-lin-7c2a"]     # slugs from facilitators/
members:                             # current member roster, in join order
  - "anna-tan-7a3f"
  - "bee-lim-9d4e"
  - "cara-ng-2b1c"
  - "dee-toh-5f3a"
  - "evan-goh-8e2d"
---
```

## Body

```markdown
A peer circle for members navigating midlife transitions — caregiving demands, career inflection points, redefining purpose.
Primary language English, occasional Mandarin code-switching welcomed. Wednesday evenings 7:30-9pm SGT.

Current wave (2): 8 weeks, started 2026-04-15, closing 2026-06-10.
```

## Role-based access

- **Founder**: full R/W.
- **Facilitator of this circle**: R/W; can add members (with founder confirm), can update status.
- **Member of this circle**: R (current roster size + meeting schedule + facilitator only — NOT other members' names unless privacy allows).
- **Other member (not in circle)**: R (status + topic + capacity available) only if applicant matching consideration.
- **Anyone else**: ❌ no access.

## Notes for skills

- `peoties-circle-cohort` reads circles in `status: forming` for matching candidates.
- `peoties-circle-facilitation` reads the active circle for context per cohort.
- `peoties-member-mgmt` reads circle to determine if a caller is a member of a given circle (for role-based access decisions).
- Member roster respects privacy: when surfacing to a non-member (e.g. an applicant considering this circle), show `current_size: 5`, NEVER member names or details.
