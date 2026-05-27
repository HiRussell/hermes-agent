# Peoties Cohort KB Schema

A **cohort** is a circle's time-bound structured program — e.g. an 8-week journey with weekly themes, content drops, milestones. A circle runs multiple cohorts (waves) over time; each is its own file.

Path: `data/business-peoties/<tenant>/cohorts/cohort--<circle-slug>--<wave-num>.md`

Example: `cohort--midlife-1--w2.md` for the 2nd wave of Midlife Circle 1.

## Frontmatter

```yaml
---
circle_slug: "midlife-1"
wave_num: 2
name: "Midlife Transitions Circle 1 — Wave 2"
duration_weeks: 8
start_date: "2026-04-15"
end_date: "2026-06-10"
status: "active"                    # enum: forming / active / completing / graduated
timezone: "+08:00"                  # SGT; for cron scheduling
meeting_schedule:                    # inherits from circle but can override
  day: "wednesday"
  time: "19:30"
  duration_minutes: 90
weekly_themes:
  - week: 1
    theme: "Arrival — who we are, what brings us here"
  - week: 2
    theme: "Naming the in-between"
  - week: 3
    theme: "Boundaries — saying yes to ourselves"
  - week: 4
    theme: "Caregiving without losing yourself"
  - week: 5
    theme: "When parents become children again"
  - week: 6
    theme: "Identity beyond role"
  - week: 7
    theme: "Practices that hold us"
  - week: 8
    theme: "Closing — what we carry forward"
content_schedule:                    # bot-delivered curated resources, by week
  - week: 1
    practice: "community-info/practices/intro-grounding.md"
  - week: 3
    practice: "community-info/practices/boundary-journal.md"
  - week: 5
    practice: "community-info/practices/sandwich-generation-reading.md"
roster:                              # snapshot of members in THIS cohort (members may join/leave between cohorts)
  - "anna-tan-7a3f"
  - "bee-lim-9d4e"
  - "cara-ng-2b1c"
  - "dee-toh-5f3a"
  - "evan-goh-8e2d"
facilitators: ["mei-lin-7c2a"]
created_at: "2026-04-01T00:00:00+08:00"
---
```

## Body

```markdown
Second wave of Midlife Circle 1. Themes deepen from arrival → identity → practices. Carries forward 3 members from Wave 1 (returning) plus 2 new members from Spring 2026 intake.

Closing session: 2026-06-10, 7:30pm SGT. Facilitator will lead a closing reflection + invite to next steps (continue / pause / new circle).
```

## Cohort lifecycle

| Status | Trigger | Bot action |
|---|---|---|
| `forming` | Circle exists but cohort not yet started (members confirmed but no first session) | No facilitation crons active yet; bot greets new members in 1:1 DM |
| `active` | First session passed | Weekly check-in cron + content drop cron + session reminder crons all running |
| `completing` | 1 week before `end_date` | Facilitator gets prompt to schedule closing session; bot pauses content drops |
| `graduated` | Closing session marked done | All members' statuses updated; bot DMs each member about next-step options |
| `paused` | Crisis or facilitator hold | All crons paused 24-48h or until facilitator un-pauses |

## Role-based access

- **Founder**: R/W full.
- **Facilitator (of this cohort)**: R/W; updates status, edits themes if needed, adds notes.
- **Member (of this cohort)**: R schedule + themes; ❌ no access to other members' info via this file.
- **Other**: ❌.
