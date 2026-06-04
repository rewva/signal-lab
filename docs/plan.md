# Plan: the multi-channel test portfolio

The operating playbook. Read `strategy.md` first.

## Core idea

> **Spray to discover -> concentrate to monetize.**

Don't bet everything on one unproven channel. Use the AI pipeline (near-zero marginal cost per channel) to run a *small portfolio* of bets, let the data reveal which gets signal, then concentrate effort and build the paid product behind the winner.

This is a **discovery engine, not the destination.** One great channel beats ten mediocre ones; the portfolio exists to *find* the one worth focusing on.

## Why the portfolio approach works here

- **Hedges the virality lottery** — organic reach is unpredictable; more bets = more shots at a hit.
- **Plays to the operator's superpower** — a pipeline that spins up + runs faceless channels makes each extra channel nearly free.
- **Fast, cheap learning** — kill duds in 30-60 days, double down on winners.

## The three catches (don't forget)

1. **Channels multiply distribution, not money.** Each winner still needs a funnel to a paid product.
2. **2026 platform crackdown on AI slop is real** — survive only via quality + a verification moat, not volume-spam (ban risk).
3. **Focus still wins eventually** — the portfolio is temporary scaffolding to find the winner.

## The process

1. **Spin up 3-5 channels** across different themes / markets / formats. GK is one of them.
2. **Run a fixed test window** (~30-60 days), roughly equal effort each.
3. **Measure cold:** views, follow-rate, engagement, and crucially *funnel signal* (does anyone click through toward a product?).
4. **Kill losers. Double down on winner(s)** — then build the paid product / funnel behind it.
5. **Keep the pipeline running** to keep testing new bets cheaply.

## Success metrics (define before launch, judge without emotion)

- Reach: views / impressions per post over the window.
- Stickiness: follow-rate, return viewers, watch-through.
- Intent: click-through to an off-platform destination we own (the real predictor of monetizability).
- A channel "wins" only if it shows *intent signal*, not just vanity reach.

## The GK candidate (locked as a test bet — design approved)

**Full approved design:** `docs/specs/2026-06-04-daily-gk-quiz-design.md` (`daily-gk-quiz` Claude Code skill). Treat as serious/approved, not a draft.

- **Concept:** a `/daily-gk-quiz` skill where Claude researches + writes one MCQ, the operator verifies the fact against a cited source, the skill renders an animated quiz Short, and (after a second approval gate) posts to YouTube Shorts + Instagram Reels + Facebook Reels. Infra cost ~$0 (Claude session is the orchestrator; Kokoro TTS + Remotion render, both local/free).
- **Why it can have a moat:** competitive-exam current affairs change daily; ChatGPT/Gemini are stale and unreliable on the latest material. The wedge is **format (interactive MCQ) + reliability (cited, operator-verified facts)** — the operator's exact strength. Reliability is **OWN-DATA**-flavored and should become the brand.
- **Target market — RESOLVED:** English, broad daily GK / current affairs, Indian competitive-exam aspirants, single-MCQ format, **audience-first** (monetization deferred to a later Telegram funnel phase — correct given tiny Indian Shorts RPM).
- **Biggest gating risk (validate FIRST):** Meta App Review + Business Verification for a solo operator (controls IG/FB API posting). Everything else is gated on proving publish access — see the design's build order.

## Next steps

1. Decide GK's target market (above), OR
2. Pick the other 2-4 test-portfolio channels from `idea-bank.md` (must pass moat + feasibility gates).
3. For each chosen channel: define format, posting cadence, the off-platform destination, and the eventual paid product.
4. Spec the shared pipeline that generates + verifies + renders + posts across all channels.
