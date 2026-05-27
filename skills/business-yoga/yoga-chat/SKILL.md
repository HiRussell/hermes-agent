---
name: yoga-chat
description: Answer customer questions about studio classes and pricing.
version: 0.1.0
author: Guan (HiRussell)
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [business, yoga, customer-service, faq]
    category: business-yoga
    related_skills: [yoga-registration, yoga-customer-mgmt, yoga-scheduling]
---

# Yoga Chat Skill

Answers customer questions about studio classes, pricing, tutors, facilities, and policies. Reads from KB markdown files (`data/business-yoga/{studio-info,tutors}/`) using `search_files` + `read_file`. Never fabricates: if the KB has no answer, the bot says so and offers to check with the owner.

## When to Use

- Customer asks an info-seeking question: "What classes do you have?" / "How much per session?" / "Who teaches Hatha?" / "Studio hours?" / "Refund policy?" / "Where are you?"
- Customer browses before committing to register (use this skill, not yoga-registration, until they say "sign me up").

Do NOT use for:
- New customer onboarding (use `yoga-registration`).
- Booking specific classes (use `yoga-scheduling`).
- Modifying customer profile fields (use `yoga-customer-mgmt`).

## Prerequisites

- KB directories exist: `data/business-yoga/studio-info/`, `data/business-yoga/tutors/`. See `references/studio-info-schema.md` and `references/tutor-schema.md`.
- Hermes builtin tools: `search_files` (to find the right KB file), `read_file` (to load its content).

## How to Run

Triggered when the user asks an info-seeking question and the bot has no clear scheduling/registration intent. The bot classifies the question, queries KB, answers concisely with the source file name as a soft attribution.

## Quick Reference

| Query type | Where to look |
|---|---|
| Studio hours / address / contact | `data/business-yoga/studio-info/hours.md`, `address.md`, `contact.md` |
| Pricing / packages / promotions | `data/business-yoga/studio-info/pricing.md` |
| Refund / cancellation / makeup-class policy | `data/business-yoga/studio-info/policies.md` |
| Class catalog (Hatha / Vinyasa / Yin / Hot) | `data/business-yoga/studio-info/classes.md` |
| Tutor profile (specialty / schedule / bio) | `data/business-yoga/tutors/tutor--<name>.md` |
| Facility (showers, mats, parking) | `data/business-yoga/studio-info/facility.md` |

## Procedure

1. **Classify** the question into one of the Quick Reference rows. If unclear, use `clarify` to ask the user one focused question.
2. **Search** the relevant KB path with `search_files`:
   - For broad info: `search_files target='files' path='data/business-yoga/studio-info/' pattern='<keyword>'`
   - For a specific tutor: `search_files target='files' path='data/business-yoga/tutors/' pattern='<tutor name>'`
3. **Read** the matched file(s) with `read_file`.
4. **Answer concisely** (2-4 sentences max). Quote prices / hours / dates verbatim from the file — do not round, do not paraphrase numbers.
5. **Cite source** softly at the end: "(source: studio-info/pricing.md, last updated 2026-04)". This builds trust + helps the customer ask follow-ups.
6. **If KB has no answer**: do NOT fabricate. Respond "Good question — I don't have that in my notes. Let me check with the owner and get back to you within the day." Optionally log via `memory` so the owner can answer + update KB.

## Pitfalls

- **Never fabricate numbers** (prices, hours, class capacity). If unsure, say "let me check" instead of guessing.
- **Don't quote stale data**: always `search_files` for the latest, don't rely on memory from earlier turns in the session.
- **Privacy**: never expose other customers' info ("X already booked Wednesday 7am") — that's `yoga-customer-mgmt` privileged territory.
- **Don't process registration here**. If the user says "I want to join", handoff to `yoga-registration`: "Great! Let me set up your profile — a few quick questions."
- **Language**: default to English. If the user opens with Chinese (or any CJK characters), mirror Chinese for the entire session.

## Verification

After answering an info question:

1. The response cites a real KB file path (not made up).
2. Any numbers / dates / names in the answer match the source file verbatim.
3. If the user's question wasn't covered, the bot honestly said "I don't have that" — no fabrication.
4. The bot did not leak any customer-specific info (names, phones, attendance history).

If the bot is uncertain about #1 or #2, it should re-`read_file` to verify before sending the response.
