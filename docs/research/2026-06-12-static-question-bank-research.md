# Research brief: static GK question bank (SSC / Banking / Railways GA tier)

**Date:** 2026-06-12
**Method:** 4 parallel online research agents (content blueprint, MCQ generation+QA method,
authoritative source map, competitor/format scan), each cross-checking 2+ sources. Findings below
are tagged by confidence. This brief informs the question-bank schema, the generation+QA pipeline,
and the sourcing/citation strategy. It is research input -- not yet a design decision.

---

## 1. Headline conclusions (what the research changes)

1. **The accuracy moat is real -- but the framing matters.** The top-5 incumbents (Adda247,
   Testbook, Exampur, Wifistudy, StudyIQ) are NOT demonstrably wrong -- they have human educators.
   The accuracy rot is in the **long-tail apps + AI-slop content farms** that dominate
   algorithm-served Shorts. Our wedge is therefore *visible* per-question source citation (the trust
   badge we already built into the pipeline), not "incumbents are wrong." This validates the moat
   design but sharpens the pitch: "every question source-cited" shown on-screen / pinned.

2. **YouTube's 2026 anti-slop purge is a tailwind, not a threat.** Jul 2025 YPP policy now targets
   "inauthentic content ... minimal human input"; Jan 2026 YouTube wiped 16 channels (4.7B views).
   A channel posting **1 human-reviewed daily Short with original VO + cited sources** sits squarely
   in the explicitly-permitted zone, and the purge removes low-quality competitors. (Corroborates our
   non-negotiable principle #6.) **Implication:** never mass-post; 1/day with a human gate is
   strategically correct, not just resource-bound.

3. **The format is solved -- execute with discipline, don't innovate.** Proven anatomy:
   hook (identity/exam-specific) -> question on-screen+VO -> ~10s countdown -> "comment your answer"
   mid-video -> reveal in green + 1-2 sentence explanation. Our render layer already matches this.
   The differentiation is question *quality* + *exam-relevance specificity*, not novel format.

4. **Bank size target: 1,500 minimum viable -> 3,000-5,000 before monetizing.** At 3-5k items the
   bank yields ~30-50 non-repeating videos per topic before cycling. Below 2k it exhausts within
   months. (Medium confidence -- extrapolated from GKToday-scale banks.)

5. **Static vs current-affairs must be a hard schema split.** Several "static-looking" facts are
   actually volatile (repo/CRR/SLR rates, tiger-reserve counts, latest award winners, NH numbering).
   These must NOT live in the static bank; they belong in a time-stamped current-affairs lane with an
   expiry date. Ask "RBI founded in which year" (static), never "current repo rate" (volatile).

---

## 2. Content blueprint -- taxonomy + weighting

GA section is ~identical static core across SSC/Bank/RRB; Banking adds a current-affairs+banking
layer, RRB leans science-heavier. Recommended bank weighting (share of total items):

| Domain | Weight | Yield notes |
|---|---|---|
| History (all periods; freedom struggle ~half) | 14-16% | 2nd highest density; freedom struggle is the hottest sub-area |
| General Science (Phys/Chem/Bio) | 14-16% | Highest in RRB; NCERT-bounded -> finite, verifiable fact-set |
| Indian Polity & Constitution | 12-14% | Highest density in SSC CGL; deeply factual (articles/schedules/amendments) |
| Static Awareness (days/awards/books/dances/firsts/superlatives) | 12-15% | Very high; classical-dance->state pairs are near-certain exam material |
| Indian Geography | 10-12% | Rivers/dams/parks/passes most tested |
| Economy & Banking Awareness | 10-12% | Higher in IBPS; static banking history is bankable |
| Govt Schemes | 5-7% | Rising post-2019 (PMJDY/PMAY/PM-KISAN recur) |
| Sports | 5-6% | Static facts (rules/venues/historical medals) only |
| World Geography (capitals/currencies/org HQs) | 5-6% | country-capital-currency, intl org HQ |
| Art & Culture / Festivals | 4-5% | Folk dances, state festivals, UNESCO sites |

Note: this overlaps but is finer-grained than the existing `data/domains.json` 9-domain blueprint --
reconcile the two when designing the bank schema (don't blindly replace the verified weights already
in the repo).

**High-confidence anchor facts** (verified across 2+ sources -- usable as seed/tests): 8 Sangeet
Natak Akademi classical dances->states; Gandhian movement chronology (Champaran 1917, Non-Coop
1920-22, Dandi Mar 1930, Quit India 1942); RBI founded 1 Apr 1935 / nationalised 1949 / 1st Indian
governor C.D. Deshmukh; PMJDY 28 Aug 2014, PM-KISAN 24 Feb 2019; SSC CGL T1 GA = 25Q/50, RRB NTPC
CBT1 = 40Q/40.

**Operator-verify-before-publish (LOW confidence / volatile):** exact Schedule-7 list counts (change
with amendments); current CRR/SLR/repo (volatile -- exclude from static); tiger-reserve & national-park
counts (annual); NH numbering old-vs-new (NH-7 renumbered NH-44 in 2010); per-shift PYQ topic counts
(download real ssc.nic.in papers to confirm). "National game of India" trap: there is officially NONE
-- any bank asserting Hockey is wrong.

---

## 3. Generation + QA pipeline (the anti-slop engine)

The core problem: generate many MCQs cheaply (LLM) yet verify every fact before it enters the bank.
Documented LLM failure modes to defend against: **wrong answer key** (>6% of MMLU items were broken),
multiple-correct-answers, hallucinated correct answer, accidentally-correct distractor, outdated
"static" facts (e.g. J&K became a UT 2019), ambiguous stems, and self-verification bias (an LLM
grading its own questions picks "least incorrect," not "correct").

**Recommended 7-step pipeline:**
1. **Grounded generation** -- RAG over a vetted corpus (Constitution text, NCERT PDFs, official
   lists, PYQ papers); require a cited source per claim. (~59% fewer hallucinations vs ungrounded.)
2. **Claim extraction -> fact ledger** -- each MCQ's correct answer + stem assertions + distractor
   claims become rows with {claim, source, url, retrieved_date}.
3. **Cross-source corroboration** -- verify each claim against >=1 independent source; require >=2 for
   high-risk claims (dates, numbers, article numbers, awards). Flag disagreements.
4. **Structural QA (rule-based)** -- exactly one correct; options homogeneous & mutually exclusive;
   no negative stems; no "all/none of the above"; no absolute terms in distractors; 4 options;
   flag option-length imbalance (>1.5x avg = answer-length tell).
5. **Adversarial LLM reviewer** -- a *different* prompt scores hallucination risk 0-10 + checks for
   multiple-correct; >3 goes to human. (Multi-agent detect+refine cut hallucination >90% in studies.)
6. **Human expert gate** -- reviews only flagged items (this is our existing accuracy gate #1);
   Approve / Edit / Reject, logged with rationale.
7. **Audit trail** -- store source URLs, last-fact-check date, generation prompt, reviewer id ->
   enables retroactive re-checking when facts change.

**Distractor design (decisive for quiz value):** all distractors same ontological category as the
answer (capital->capitals, year->nearby years +/-decade, person->same-era real figures); prefer
misconception-based near-misses; replace any distractor chosen by <5% of users (non-functioning).
Indian MCQ banks average ~38% non-functioning distractors -- this is the single most actionable QC
metric once we have response data.

**Dedup:** exact = normalized-text hash; near-dup = sentence-embedding cosine (use a
Hindi-capable model for bilingual): >=0.87 auto-reject, 0.80-0.87 human-review, 0.70-0.80 allowed but
clustered. FAISS/ANN at scale.

**Difficulty:** start with expert/LLM-simulated labels (target mix ~20-25% easy / 50-60% med /
20-25% hard), then calibrate from real responses -- CTT p-value (easy >0.70, hard <0.30) +
discrimination index (retire items with D<0.10 after ~500 responses). Items performing below the
0.25 chance level are likely flawed (wrong key/ambiguous), not just "hard."

---

## 4. Authoritative source map (the citation backbone)

Tiering for the `sources`/`source_citation` fields:

- **Tier 1 (official/primary):** Constitution -- legislative.gov.in / indiacode.nic.in (PDF, not
  per-article linkable); Economy -- rbi.org.in, indiabudget.gov.in, sebi.gov.in, mospi.gov.in;
  Culture/Sports -- **ich.unesco.org** & **whc.unesco.org** (confirmed PER-ITEM deep links),
  indiaculture.gov.in, sangeetnatak.gov.in; Schemes/awards -- **pib.gov.in** (per-release PRID deep
  links), padmaawards.gov.in, awards.gov.in; Census -- censusindia.gov.in.
- **Tier 2 (academic/established):** **ncert.nic.in** (chapter PDFs, linkable;
  `ncert.nic.in/textbook/pdf/[code].pdf` pattern) for History/Geo/Science;
  **constitutionofindia.net** (CLPR non-profit) -- the ONLY confirmed **per-Article** deep-link
  (`/articles/article-14-equality-before-law/`), pair with the GoI PDF for authority.
- **Tier 3 (only where 1/2 absent):** Manorama Yearbook, India: A Reference Annual (both paywalled,
  no public deep links).

**Best deep-linkable sources (operator/viewer can click to verify):** constitutionofindia.net
(per-article), ich.unesco.org & whc.unesco.org (per-site), pib.gov.in (per-release), ncert chapter
PDFs, sebi.gov.in (per-act). Many GoI portals (legislative.gov.in, censusindia, indiabudget,
padmaawards) are live in browsers but return 403/SSL to bots -- citeable but not auto-fetchable.

**Domains with WEAK sourcing (concentrate human verification here):** "first-in-India"/superlatives &
national symbols (no single authoritative deep-link; the national-game trap); important days (MHA PDF
only, no per-day link); books/authors (no govt list); classical-dance count (Min. of Culture says 9,
many sources say 8 -- reconcile); static banking definitions (RBI glossary not term-deep-linkable ->
cite the RBI Act on indiacode); state-specific geography (cite NCERT chapter, not a per-fact URL).

---

## 5. Channel / format / monetization context

- **Incumbents** use YouTube as a *free funnel*, monetizing via paid test-series/courses, NOT the
  channel. Testbook: 33M users, 1.5M paid, ~Rs136.7Cr FY24, 5% free->paid at Rs699-3,499. Adda247:
  ~Rs221Cr, acquired StudyIQ. (Inc42/Business Standard/Tracxn -- accept.)
- **Monetization ranked for us:** (1) paid test-series/crash-course funnel [highest ceiling, proven];
  (2) free Telegram -> paid premium group Rs199-499/mo; (3) edtech sponsorships Rs5k-50k/Short at
  50k+ subs; (4) affiliate; (5) AdSense LAST (India Shorts RPM ~Rs30-100/1k -- supplement only).
  Confirms principle #1 (products = money, views != money).
- **Format specifics:** 10s countdown dominant; "comment your answer" *mid-video* (not end) drives
  comments; identity hooks ("only a topper can..."); 5-Q sequences create completion motivation;
  India is Shorts' largest market (460M+) and the big channels are **Hindi-first** -- English-only
  narrows the funnel (language is an open strategic lever for us).
- **Build the Telegram funnel from day one** -- every incumbent does; the Short is acquisition, the
  community is retention/upsell. Define the first paid product (a Rs499-999 "30-day GK crash test
  series") *before* 10k subs.

---

## 6. Implications for the build (proposed, for discussion)

1. **Schema:** the bank entry should carry everything the QA pipeline + render + publisher need:
   `fact_key`, `domain`, `difficulty`, `entity`, `question`, `answer`, `distractors[3]`,
   `exam_relevance[]`, `is_trick`, `explanation`, `mnemonic`, `source_citation`, `sources[]`
   (already the `Question` shape) **plus** bank-management fields: `static_class`
   (permanent / slowly-changing / current-adjacent), `verified_date`, `review_due_date`,
   `source_tier` (1/2/3), `status` (draft/verified/retired), and dedup `embedding`/hash. Reconcile
   `domain` taxonomy + weights with the existing verified `data/domains.json`.
2. **Pipeline:** implement the 7-step generate->verify flow as a batch tool writing into
   `state/question-bank.json` (or a SQLite bank); the existing operator accuracy gate #1 IS step 6.
3. **Sourcing rule:** prefer Tier 1/2 deep-linkable sources so `sources[]` URLs are clickable in the
   review dashboard's verify chip; flag weak-sourcing domains for mandatory human verification.
4. **Hard static/current split** in the schema so volatile facts never ship as "static."
5. **Seed set:** start from the ~30 high-confidence anchor facts above as the first verified entries +
   pipeline test fixtures.

---

## 7. Confidence + caveats

- HIGH: anti-slop platform signals (multi-source), incumbent financials (Inc42/BS/Tracxn), MCQ
  item-writing rules (NBME/university testing guidance), the anchor facts in SS2, deep-linkability of
  ich/whc.unesco.org + constitutionofindia.net + ncert PDFs (fetched live).
- MEDIUM: bank-size + weighting numbers (extrapolated), per-shift PYQ topic counts (coaching
  aggregates), "countdown = 2.5x engagement" (single source -- directional).
- LOW / verify-before-use: all volatile facts (rates/counts/winners/NH numbers), classical-dance
  count 8-vs-9, exact Schedule-7 list sizes. No incumbent was caught with a specific wrong on-screen
  answer -- the documented errors are in long-tail apps/farms (Play Store reviews), so position the
  moat against the long tail, not the top 5.

Full per-agent source lists are in the session transcript; key fetched sources include
practicemock.com, testbook.com, oliveboard.in (syllabi/weightage); arxiv 2601.14280, 2501.13125,
2503.08551, NBME/university item-writing guides, PMC12803428 (QA/distractors); ncert.nic.in,
rbi.org.in, ich.unesco.org, constitutionofindia.net (sources); inc42.com, tracxn.com, techcrunch.com,
tubefilter.com, searchenginejournal.com (market/anti-slop).
