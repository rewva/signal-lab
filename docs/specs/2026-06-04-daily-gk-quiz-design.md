# Design: `daily-gk-quiz` — Autonomous Daily GK Quiz Shorts (Claude Code skill)

**Date:** 2026-06-04
**Status:** Approved design (plan only — no implementation in this phase)
**Owner:** sdevendran

---

## 1. Concept

A Claude Code skill the operator launches manually each morning (`/daily-gk-quiz`).
Claude itself is the orchestrator: it researches and writes **one** GK / current-affairs
**multiple-choice question** aimed at Indian competitive-exam aspirants (in **English**),
the operator verifies the fact against a cited source, the skill renders a clean animated
quiz Short, and — only after operator approval — posts it to **YouTube Shorts, Instagram
Reels, and Facebook Reels**.

The channel is **audience-first**. Monetization is a deliberately deferred later phase
(funnel to a Telegram community), because Indian short-form ad revenue is structurally tiny.

### Why a Claude skill (not a cron pipeline)
- Claude (the running session) does the research + scripting natively -> **no separate Claude API cost, no scheduler, no host.**
- The two approval gates are **inline** in the session — no extra approval bot needed.
- Effective infra cost: **~$0/month.**

---

## 2. Strategic context (from verified research)

Two deep-research passes (web-sourced, adversarially verified) established the constraints
this design is built around:

1. **Short-form barely monetizes.** Shorts RPM ~= **$0.03-0.30 per 1,000 views**; long-form
   earns **10-100x more per view**. The only documented faceless-AI success (Textify) made
   **96.5% of income from long-form**, not Shorts. -> *Shorts are a growth/discovery engine,
   not a revenue engine.* Decision: **audience-first, monetize off-platform later.**
2. **YouTube's July 15, 2025 "inauthentic content" policy** demonetizes *"mass-produced
   content using a similar or unoriginal template across multiple videos"* and requires
   *"the substance of each video to be materially varied."* **AI use is explicitly allowed** —
   what gets killed is templated sameness with no added value. -> The format must vary
   substance daily and add genuine educational value (both satisfied by a fresh daily MCQ).
3. **Niche fit:** Daily GK/current-affairs is near-perfect for *daily sustainability*
   (current affairs are new every day + a huge static-GK bank) but is *heavily saturated*
   (Adda247, StudyIQ, Testbook, Wifistudy). The differentiation wedge is **format + reliability**,
   not topic.

---

## 3. Scope decisions (locked)

| Dimension | Decision |
|---|---|
| Goal | Audience growth; monetization deferred |
| Niche | Daily GK + current affairs for Indian competitive-exam aspirants |
| Language | **English** (better TTS quality, easier fact-checking, higher-value audience) |
| Exam target | **REFINED 2026-06-10: SSC / Banking / Railways "General Awareness" tier** (SSC CGL/CHSL, IBPS/SBI, RRB) -- was "broad daily GK (widest audience)"; narrowed for intent signal + exact GA-section format fit. UPSC excluded (poor quiz-short fit). See `docs/specs/2026-06-10-gk-topic-selection-design.md`. |
| Format wedge | **Interactive MCQ quiz** — Q -> countdown -> answer + one-line why |
| Questions per video | **1** (punchy, high completion rate, drives comments) |
| Content mix | **Ad-hoc** — best available question each day (current affairs or static GK) |
| Platforms | YouTube Shorts + Instagram Reels + Facebook Reels |
| Automation level | Manual launch + **two human approval gates** before posting |
| Budget | $0-30/month (target ~$0) |

---

## 4. Product — what one video is (~15-20s)

```
[0-2s]   Hook:    "Daily GK Quiz — today's question"
[2-7s]   Question + 4 options (A/B/C/D)
[7-10s]  countdown 3...2...1
[10-18s] Correct answer + one-line "why it matters / exam relevance"
[end]    CTA: "Comment your answer  /  Follow for daily GK"
```

The countdown and "comment your answer" are intentional **retention + engagement
mechanics** — the strongest signals the Shorts algorithm rewards.

---

## 5. Daily flow (the skill recipe)

1. **Pick today's question** — Claude reads `state/question-history.json`, web-searches the
   day's exam-relevant current affairs, and drafts **one** MCQ (correct answer + 3 plausible
   distractors). On a thin-news day, falls back to a strong static-GK question. Ad-hoc: best
   question wins. Must not duplicate recent history.
2. **Accuracy gate (critical)** — Claude presents the **question, correct answer, the three
   distractors, and a cited source URL** proving the fact. **Nothing renders until the operator
   confirms the fact is correct.** This is the primary anti-hallucination safeguard — mandatory
   because wrong facts in exam prep are actively harmful and destroy channel credibility.
3. **Voiceover** — `tts.sh` -> Kokoro TTS (local, free) narrates question + answer.
   *(Optional fallback: music-only, no narration.)*
4. **Render** — `render` -> Remotion (free for solo/<=3) builds the animated quiz card:
   question, four options, countdown timer, answer reveal. **Text-first card design** — no
   copyrighted news photos, no stock-footage mismatch, fully automatable.
5. **Review gate** — Claude reports the output path; operator watches `quiz.mp4` and
   approves or requests changes (redo voice, fix wording, etc.).
6. **Publish (on approval only)** — runs the three posting scripts, sets the YouTube AI
   disclosure toggle if a synthetic voice is used, appends to `state/posted-log.json`, and adds
   the question to `state/question-history.json`.

---

## 6. Tech stack (all $0 in normal use)

| Step | Tool | Cost | Notes |
|---|---|---|---|
| Research + write MCQ + cite source | **Claude (this session)** | $0 | the skill's brain |
| Voiceover (TTS) | **Kokoro** (local) | $0 | prefer over edge-tts (unstable, 403s) |
| Render quiz card | **Remotion** (React templates) | $0 | free for solo/<=3 employees; ideal for countdown + reveal animation |
| Captions (if voiced) | Whisper.cpp (local) | $0 | word-level timing |
| Posting | YouTube Data API v3 + Meta Graph API | $0 | limits far exceed 1/day |

**Dropped from earlier generic plan:** Pexels stock video — a text-first quiz card needs no
stock footage, which also eliminates image-copyright risk.

**Fallbacks:** FFmpeg + pre-designed PNG card template (if Remotion's learning curve bites);
music-only audio (if Kokoro English quality is insufficient).

---

## 7. Skill structure

```
daily-gk-quiz/
├── SKILL.md                  # the daily recipe Claude follows
├── scripts/
│   ├── tts.sh                # answer/question text -> voiceover.wav (Kokoro)
│   ├── render/               # Remotion project: animated quiz card
│   ├── captions.sh           # Whisper.cpp word-level timing (if voiced)
│   ├── post_youtube.py       # YouTube Data API v3 videos.insert (+ AI disclosure)
│   ├── post_instagram.py     # IG Graph API: create REELS container -> publish
│   └── post_facebook.py      # FB Pages API: /{page_id}/video_reels
├── references/
│   ├── api-setup.md          # one-time account/token setup (all 3 platforms)
│   ├── question-style.md     # MCQ writing rules, distractor quality, exam relevance
│   └── compliance.md         # slop-avoidance + AI disclosure rules
└── state/
    ├── question-history.json # dedupe + force daily variation
    └── posted-log.json       # what posted where, when
```

---

## 8. Platform posting — limits & access (verified)

| Platform | API | Daily limit | Access requirement |
|---|---|---|---|
| YouTube Shorts | Data API v3 (`videos.insert`) | hard cap **100 videos.insert/day** (separate allocation, not the unit pool) | Google Cloud project + OAuth. Confirmed 2026-06-08: default 10,000 units/day + dedicated 100 inserts/day. 1/day trivially fine; no increase needed. |
| Instagram Reels | Graph API (`media_type=REELS`) | ~100 posts/24h | **Business/Creator account linked to a Facebook Page** + content-publish permission. Personal accounts can't post via API. |
| Facebook Reels | Pages API (`/{page_id}/video_reels`) | 30 posts/24h | Page access token + `pages_manage_posts`, `pages_read_engagement`, `pages_show_list`. |

**Biggest upfront hurdle — RESOLVED 2026-06-08 (GO):** Self-posting to the operator's OWN
FB Page + IG Business/Creator accounts does **NOT** require App Review or Business
Verification. Role-holder-only apps stay in **Standard Access** (all permissions grantable,
no review). App Review + Business Verification only apply to **Advanced Access** (acting on
accounts you don't own). **Precondition:** add own FB Page + IG accounts as role-holders
(Admin/Dev/Tester) on the Meta app; accept ~25 IG posts/24h Standard Access limit (fine for
1/day). See `docs/posting-pipeline-api-research.md`.

---

## 9. Compliance & quality guardrails (built into the skill)

- **Slop-policy safe-harbor:** (a) substance varies daily (different question), (b) genuine
  educational value (real exam prep). Both met by design. Additionally, the skill **rotates
  2-3 card layout/color variants** and writes a fresh per-day "why" line so output isn't one
  identical visual template.
- **Accuracy:** every fact carries a cited source the operator verifies at gate #2.
- **AI disclosure:** if a realistic synthetic voice narrates, enable YouTube's synthetic-media
  toggle (safe default). AI used only for scripting/research is exempt. Re-verify Meta's 2026
  AI-disclosure rules for automated Reels at build time.

---

## 10. Monetization funnel (later phase — NOT v1)

Audience -> **Telegram channel** (CTA evolves to this once there's a following) -> PDFs / weekly
quiz compilations / affiliate to test-series platforms (Testbook-style) / eventually a course.
**No ad-revenue dependency** — the correct call given low Indian Shorts RPM.

---

## 11. Out of scope (YAGNI)

- Cron / scheduler (operator launches manually)
- Fully-autonomous posting (both approval gates stay)
- Long-form video
- Paid APIs / stock-video services
- The monetization funnel as v1 work (deferred phase)

---

## 12. Risks & open questions

**Risks**
1. **Hallucinated facts** — mitigated by the cited-source accuracy gate (operator verifies).
2. ~~**Meta App Review / Business Verification** for a solo operator — feasibility unconfirmed; the biggest unknown.~~ **RESOLVED 2026-06-08 (GO):** not required for self-posting (Standard Access via role-holder app). See `docs/posting-pipeline-api-research.md`.
3. **Saturated niche** — wedge is interactive format + reliability; expect format iteration.
4. **Remotion learning curve / Kokoro English quality** — fallbacks defined (FFmpeg+PNG; music-only).

**Open questions — status (resolved 2026-06-08, see `docs/posting-pipeline-api-research.md`)**
- ~~Can a solo operator without a registered business clear Meta Business Verification?~~ **RESOLVED:** not needed for self-posting (Standard Access via role-holder app).
- ~~Actual YouTube quota allocation.~~ **RESOLVED:** 10,000 units/day + 100 videos.insert/day cap; no increase needed.
- **Current 2026 Meta AI-disclosure requirements for automated Reels — STILL OPEN.** YouTube side resolved (own/cloned voice + AI scripts exempt); Meta "AI info" label + API field unresolved, needs a dedicated pass.

---

## 13. Build order (when implementation begins)

1. **Prove publish access** on YouTube + Meta. ~~Meta verification~~ confirmed not required (2026-06-08); reduced to a setup step: create the Meta app, add own FB Page + IG Business/Creator as role-holders, accept role invites, generate page + IG tokens. Create the Google Cloud project + OAuth client for YouTube. Do this first.
2. Write `SKILL.md` + the Remotion quiz-card template + `state/` files.
3. Test one end-to-end video locally (pick question -> voice -> render -> review).
4. Wire the three posting scripts; test against the operator's own accounts.
5. Run manually for ~2 weeks; tune format, distractor quality, card variants.
6. Add the Telegram funnel as a separate later phase.

---

## Sources (verified research)

- YouTube monetization / inauthentic-content policy: https://support.google.com/youtube/answer/1311392
- YouTube AI disclosure: https://blog.youtube/news-and-events/disclosing-ai-generated-content/
- YouTube quota costs: https://developers.google.com/youtube/v3/determine_quota_cost
- YouTube Partner Program thresholds: https://support.google.com/youtube/answer/72851
- Instagram content publishing: https://developers.facebook.com/docs/instagram-platform/content-publishing/
- Facebook Reels publishing: https://developers.facebook.com/docs/video-api/guides/reels-publishing/
- Shorts vs long-form RPM + niche CPM tiers: https://vidiq.com/blog/post/youtube-shorts-monetization/ , https://vidiq.com/blog/post/most-profitable-youtube-niches/
- Faceless-AI case study (Textify): https://flippa.com/blog/how-a-faceless-youtube-channel-sold-for-300k/
- Reference generation stacks: https://github.com/gyoridavid/short-video-maker , https://github.com/MatteoFasulo/Whisper-TikTok

---

## Operator note (added on filing)

Filed into signal-lab as the design for the **GK test bet** (see `docs/plan.md`). This resolves
the previously-open "GK target market" decision: **English, broad daily GK/current-affairs,
Indian competitive-exam aspirants, MCQ format, audience-first.** Treated as a serious approved
artifact, not a draft.
