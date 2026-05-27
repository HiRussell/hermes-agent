# Studio Info KB Schema

Path: `data/business-yoga/studio-info/<topic>.md`

Each topic = one markdown file. Topics are open-ended but conventional ones are:

| File | Purpose | Used by |
|---|---|---|
| `hours.md` | Open / close times per day, holidays | `yoga-chat` |
| `address.md` | Physical address, parking, public transport | `yoga-chat` |
| `contact.md` | Phone, email, WeChat, owner's contact for escalation | `yoga-chat` |
| `pricing.md` | Drop-in, packages, memberships, promos | `yoga-chat` |
| `classes.md` | Class catalog: Hatha / Vinyasa / Yin / Hot — what they are, who they're for | `yoga-chat` |
| `policies.md` | Cancellation, refund, makeup, late arrival, COVID, attire | `yoga-chat`, `yoga-scheduling` |
| `facility.md` | Showers, lockers, mats provided, water | `yoga-chat` |

## Frontmatter (minimal)

```yaml
---
topic: "pricing"             # required, matches filename
last_updated: "2026-05-01"   # required, ISO date
language_priority: ["en", "zh"]  # optional, ordered list of supported languages in this file
---
```

## Body

Free-form markdown. Optimize for `read_file` returning a useful chunk to the bot. Use:
- Clear `## Section` headers for sub-topics (e.g. pricing.md has `## Drop-in`, `## Monthly`, `## Annual`).
- Numbers and dates verbatim — `yoga-chat` is told NOT to round / paraphrase, so the source must be exact.
- Bilingual support: write both EN and ZH sections if `language_priority` lists both.

Example `pricing.md`:

```markdown
---
topic: "pricing"
last_updated: "2026-05-01"
language_priority: ["en", "zh"]
---

## Drop-in

- Single class: ¥180 / class
- Workshop (90 min): ¥280

## Monthly

- 8 classes / month: ¥1280 (¥160 / class)
- Unlimited / month: ¥2480

## Annual

- 100 classes / year: ¥12800 (¥128 / class)

## 价目 (中文)

(same structure, repeated in Chinese for native-language readers)
```

## Maintenance

- Update `last_updated` whenever the file content changes.
- `yoga-chat` will cite this file path + `last_updated` when answering customers, so a stale file = stale customer-facing answer. Owner should review monthly.
