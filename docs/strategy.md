# Strategy

The founding thesis for signal-lab. This is the "why" behind every decision.

## The asset we're building on

The operator's real superpower is not any single topic. It is **a machine that conquers a domain with almost no human labor**: AI agent pipelines that produce *verified, trustworthy* output at scale, with a human who steers rather than labors. WhichWise was the first thing this machine was pointed at. signal-lab points it somewhere with a better effort-to-money ratio.

## The monetization truth (learned the hard way)

1. **Platforms barely pay — especially in India.**
   - Instagram: no reliable per-view payout in India; bonus programs gone/invite-only.
   - Facebook Reels: pays pennies; Indian rates among the lowest in the world.
   - YouTube: the only one that pays seriously, but Indian long-form RPM is ~Rs.50-200 / 1000 views and Shorts are far worse (~Rs.4-40 / 1000). You'd need tens of millions of views/month for meaningful ad income.

2. **Followers != money. Views != money.** A faceless account with no product behind it is a hobby.

3. **Money comes from a product the audience funnels into** — a paid app/tool, a course/membership, affiliate, or lead-gen. The content is the *mouth of the funnel*, never the thing sold.

## The funnel (concrete)

```
 TOP    -> free content (e.g. a daily question video) pulls strangers in
 MIDDLE -> a reason to leave the platform onto something WE own (app / email / WhatsApp)
 BOTTOM -> the paid upgrade earns from the small % who convert
```

The moving force at each step:
- Stranger -> viewer: content is useful + interactive, so the algorithm spreads it for free.
- Viewer -> ours: we give a reason to leave the platform (more value on our app). Most important step — platform followers aren't ours; app/email users are.
- User -> payer: free hooks them; the paid tier offers more/better/fresher.

## The moat filter (what survives ChatGPT)

A tool is defensible only if it does something a free chatbot *fundamentally cannot*. Chatbots are one-shot, have no live data, can't touch your accounts, and can't ship anything. So there are exactly four moats:

| Moat | What it means | Why a chatbot can't |
|------|---------------|---------------------|
| **ACT** | Do multi-step tasks across real sites / the user's accounts | It can't take actions in the world |
| **WATCH** | Run 24/7, alert the instant something happens | It's request-response, never continuous |
| **OWN-DATA** | Fresh, verified data not in any training set | Its knowledge is stale and unbrowsable at depth |
| **SHIP** | Produce a physical thing | It can't manufacture or mail |

Anything that doesn't sit on one of these is a **wrapper** and will be killed the moment a frontier model adds the feature. Reject wrappers.

**Feasibility corollary:** even a valid-moat idea fails if the data is locked away. Avoid aggressively bot-protected walled gardens (Facebook Marketplace, eBay, IG internals). Prefer open APIs, public records, and the user's own connected accounts.

## The geography lever

Target rich markets (US/UK/CA/AU). The headline reason people cite is higher ad RPM (5-15x India), but that's still the weak ad game. The real multiplier is **willingness to pay for a product**: a Western user paying $15/mo beats Indian ad-pennies by 100x+, in dollars. Content to *get* foreign viewers is harder (you compete with locals on native content), but the *product* sells worldwide with no border.

## Decision log (so we don't relitigate)

- **Rejected: B2B data API, widgets, FD/RD/savings/loans verticals.** Not because they're bad — they're already WhichWise's own roadmap. Out of scope here.
- **Rejected: carousel maker / content-generator tools.** Crowded (50+ competitors) and wrappers.
- **Rejected: verdict-machine / scam-scanner.** Good approach (operator liked the moat reasoning) but didn't land as the pick.
- **Rejected: flip-finder (resale arbitrage).** Loved the model, but data access is the wall — FB Marketplace / eBay actively block scraping. Failed the feasibility gate.
- **Kept: the moat filter itself** as the operator's preferred way to judge ideas.
- **Locked: GK / competitive-exam** as a candidate channel (see `plan.md`). Target market within it still open.
- **Adopted: multi-channel portfolio** as the operating model (see `plan.md`).
