# Tutor KB Schema

Path: `data/business-yoga/tutors/tutor--<slug>.md`

`<slug>` = lowercased name with hyphens (e.g. `lily-chen`).

## Frontmatter

```yaml
---
name: "Lily Chen"
display_name_zh: "陈丽丽"        # optional, Chinese display name
slug: "lily-chen"
specialty: ["Vinyasa", "Hatha"]  # list, class types they teach. Used by yoga-scheduling for matching.
bio_short: "RYT-500 with 8 years teaching experience, focus on alignment and breath."
bio_zh: "RYT-500 八年教学经验, 专注体式和呼吸"  # optional
languages: ["en", "zh"]
status: "active"                  # enum: active / on-leave / departed
availability:                     # required, weekly recurring schedule (UTC times)
  monday:    [{ start: "07:00", end: "08:00", class_type: "Vinyasa" }]
  wednesday: [{ start: "07:00", end: "08:00", class_type: "Vinyasa" },
              { start: "18:00", end: "19:00", class_type: "Hatha" }]
  friday:    [{ start: "07:00", end: "08:00", class_type: "Vinyasa" }]
  saturday:  [{ start: "09:00", end: "10:30", class_type: "Vinyasa-workshop" }]
created_at: "2026-04-01T00:00:00Z"
updated_at: "2026-05-15T10:00:00Z"
---
```

## Body

A 2-3 paragraph bio for `yoga-chat` to surface when customers ask "Who teaches X?":

```markdown
Lily started yoga at 16 to recover from a running injury and never looked back. She
trained at the Yoga Alliance E-RYT 500 program and has taught at studios across
Shanghai, Singapore, and Bali. Her style emphasizes precise alignment paired with
long breath cycles — beginners love how unintimidating she is, advanced students
love how she catches subtle posture drifts.

Weekly: Wed 7am Vinyasa, Wed 6pm Hatha, Sat 9am workshop. Private sessions by request.
```

## Notes for skills

- `yoga-scheduling` reads `availability` to check if a tutor is free at a requested slot.
- `yoga-chat` reads `bio_short` / `body` to answer "who is X?" questions.
- `status: on-leave` means temporarily unavailable — `yoga-scheduling` should not book; `yoga-chat` should say "Lily is on leave until [date], try Mei?"
