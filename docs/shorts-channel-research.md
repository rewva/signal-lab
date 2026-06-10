# Shorts / Reels Channel Research
_Session date: 2026-06-05. Two deep-research workflows (5 agents + 13 agents). Do not relitigate these findings without new data._

## Context

Starting point: observed "Sticky Info" style comparison Shorts (Coffin vs Casket, 308K likes) and asked whether this format is worth building an autonomous pipeline around.

**Constraints locked during this session:**
- Short-form only — Shorts and Reels, not long-form YouTube.
- Finance content excluded — belongs to WhichWise (`D:\Rewva\credit-card`).
- Full automation preferred — ChatGPT/Claude script + ElevenLabs voice + simple visuals.
- Indian operator: TikTok Creator Rewards excluded from India, YouTube Shorts RPM is low. Monetization must come from affiliate, ebook, or digital product — not AdSense.
- Western audience preferred for higher purchase intent and CPM.
- GK/competitive exam quiz channel already locked (see `docs/plan.md` and `docs/specs/2026-06-04-daily-gk-quiz-design.md`).

---

## Universal Patterns (from research)

1. **AdSense alone never works from India.** Every channel making real money has an off-platform product. Content = top of funnel.
2. **CapCut has no API.** Cannot automate video assembly with it. Use Remotion (free, React-based) or Creatomate ($54/month).
3. **n8n self-hosted** is the right orchestration tool — free with $5–7/month hosting on Hetzner/Railway. Six published faceless video automation templates exist on n8n.io (IDs: 2971, 2875, 3442, 4630, 8404, 10455).
4. **TikTok Creator Rewards excludes India** — hard constraint. YouTube is the only platform that pays.
5. **Anti-slop enforcement is real.** YouTube terminated 16 channels with 4.7B combined views in Jan 2026. Five highest-risk patterns: AI voice + static slideshow, template clones with no variation, music + looping visuals without narration, compilations without commentary, 10+ daily uploads with uniform structure.
6. **Multi-platform posting:** one n8n workflow via Upload-Post.com API publishes to TikTok, Instagram, YouTube, Facebook, LinkedIn simultaneously. Post everywhere; monetize through YouTube + owned channels.
7. **Build-to-exit is real:** Textify (horror storytelling) sold for $300K on Flippa after 8 months. Design for this from day one — clean AdSense history, documented SOPs, consistent branding.

---

## Tier 1 — Build These

### 1. Psychology / Narcissism Recovery

**Revenue ceiling:** $5K–$30K/month
**Automation:** 7.5/10
**Monthly cost:** ~$75–110

**Why:** Every proof channel (Crappy Childhood Fairy, Surviving Narcissism, Sam Vaknin) is on-camera personal brand — the faceless automated Shorts lane has no dominant player. Open position. BetterHelp affiliate infrastructure is proven at scale: 1,277 YouTube channels already sponsored, $45–200 per converting referral. Audience (women 25–45, 70–80% US/UK/CA/AU) has the highest willingness to pay for digital products of any niche researched. Psychology scripts are not YMYL in the same way health content is — no mandatory fact-checker.

**Best sub-niche:** Covert narcissism + trauma bond recovery — tightest search intent, fewest faceless competitors, highest affiliate conversion.

**Monetization path:**
- Primary: BetterHelp affiliate ($45–200/referral, 60-day cookie) + Talkspace/Calm as backup
- Secondary: $27 ebook on Gumroad ("Narcissist Survival Workbook")
- Tertiary: $97 mini-course ("Break the Trauma Bond in 30 Days")
- AdSense is the floor, not the plan

**Stack:**
| Tool | Purpose | Cost |
|---|---|---|
| Claude/ChatGPT | Script generation (templated, 2 min/short) | $20/month |
| ElevenLabs Creator | Warm female voice | $22/month |
| InVideo AI or Pictory | Auto-matches stock footage to script | $19–25/month |
| CapCut / Captions.ai | Captions (mandatory — 80% watch muted) | Free |
| Canva Pro | Text-heavy thumbnails | $13/month |
| Buffer | Scheduling | $0–15/month |

**Sample topics:**
- 5 Signs You Are Trauma-Bonded to a Narcissist (And Why You Cannot Leave)
- The Covert Narcissist's 3 Tactics That Are Harder to Spot Than Obvious Abuse
- What Intermittent Reinforcement Does to Your Brain — Why You Miss Someone Who Hurt You
- The Gray Rock Method: How to Make a Narcissist Lose Interest in You in 7 Days
- Love Bombing vs Genuine Interest — How to Tell the Difference in the First 48 Hours
- Why Empaths Are a Narcissist's Favorite Target (The Neuroscience Behind It)
- The 4 Attachment Styles in 60 Seconds — Which One Is Keeping You Stuck?
- Narcissist's Discard Phase: Why They Go Ice Cold Overnight With No Warning
- 10 Gaslighting Phrases Narcissists Use to Make You Doubt Your Own Memory
- The Anxious-Avoidant Trap: Why Opposites Attract and Then Destroy Each Other

**Sample video idea (first video):**
> **"The Gray Rock Method: How to Make a Narcissist Lose Interest in You"**
> Hook: "If you're dealing with a narcissist, stop arguing. Do this instead."
> Format: text-on-screen + ElevenLabs calm female voice + stock footage (gray stone → person walking away free). 55 seconds. Ends: "Full recovery guide — link in bio."

---

### 2. Animal Behavior / Zoology

**Revenue ceiling:** $2K–$20K/month
**Automation:** 7.5/10
**Monthly cost:** ~$66–96

**Why:** Cleanest automation story in all 12 niches researched. No YMYL medical policy risk, no mandatory fact-checker. Storyblocks Unlimited ($30/month) solves visuals entirely with real licensed footage — eliminates AI anatomy error risk. Virality mechanics (disgust, surprise, scale contrast) are among the strongest for Shorts — mantis shrimp and crow intelligence videos routinely hit 10M+ views. Affiliate stack activates from day one with no follower threshold.

**Best sub-niche:** Animal cognition + extreme biology (crows, octopuses, pistol shrimp, tardigrades) — highest viral coefficient, least crowded vs apex predator content.

**Monetization path:**
- Primary: Amazon Associates for wildlife cameras, trail cams, binoculars, field guides (AOV $80–400, 3–4% commission)
- Secondary: Direct brand deals — OpticsPlanet (ShareASale 3%), Bushnell (AvantLink 6%), Bass Pro (3–5.6%) at 20K–100K followers
- Tertiary: YouTube Partner Program AdSense ($4–10 RPM) as floor
- Digital product: $19 species behavior PDF on Gumroad at 50K subscribers

**Stack:**
| Tool | Purpose | Cost |
|---|---|---|
| Claude/ChatGPT | Animal behavior scripts from PubMed/PNAS sources | $5–20/month |
| ElevenLabs Creator | Authoritative narration | $22/month |
| Storyblocks Unlimited | 4K wildlife footage (unlimited downloads) | $30/month |
| Pexels / Pixabay | Supplement footage | Free |
| CapCut | Shorts assembly + auto-captions | Free |
| Make.com | Automation orchestration | $9/month |

**Sample topics:**
- The pistol shrimp creates a plasma bubble hotter than the surface of the sun — to stun a fish
- Crows remember your face, hold grudges for years, and teach their children to avoid you
- Orcas flipped a great white shark upside down and ate only the liver
- The mantis shrimp punches with the force of a bullet and sees 16 types of color
- How wolves changed the course of rivers in Yellowstone just by existing there
- Tardigrades are the only animal confirmed to survive in open space
- Ants are running a supercolony with military structure more complex than most human armies
- The octopus has three hearts, blue blood, and a brain in each arm — it is not one animal, it is nine
- Honey badgers are genuinely immune to cobra venom
- The mimic octopus can impersonate 15 different species on demand

**Sample video idea (first video):**
> **"The Pistol Shrimp Creates a Flash Hotter Than the Surface of the Sun"**
> Hook: "This 2-inch shrimp generates a plasma bubble at 8,000°C to kill prey. Here's how."
> Format: Storyblocks underwater footage + ElevenLabs voice + slow-motion shrimp clip. 45 seconds. Amazon Associates link for underwater camera in description.

---

### 3. Language / Etymology / Linguistics

**Revenue ceiling:** $3K–$20K/month
**Automation:** 7.5/10
**Monthly cost:** ~$84–117

**Why:** No dominant faceless automated channel exists as of mid-2026 — Etymology Nerd (3.3M combined following) is a face-on personal brand, not automatable. Open lane. Etymology scripts are among the easiest for AI to generate correctly: dates, Latin/Greek roots, and word histories are factual, verifiable against open sources (Online Etymology Dictionary, Oxford Latin Dictionary), with minimal hallucination risk. Duolingo/Babbel sponsorship path activates early (micro-influencer deals at 10K–100K subscribers). Audience (educated adults 25–45, US/UK/CA/AU) is the western buyer persona that converts on language app subscriptions.

**Best sub-niche:** Etymology + untranslatable words from other languages — highest virality (shareability from "I never knew that" reaction), lowest competition.

**Monetization path:**
- Primary: Duolingo, Babbel, Rosetta Stone sponsorships ($500–2,000/video at 100K–300K subscribers)
- Secondary: $37 "Words Without English Equivalents" PDF pack on Gumroad (launch at 10K subscribers)
- Tertiary: Substack at $7/month for weekly etymology deep-dives
- AdSense meaningful only on long-form companion videos ($8–14 RPM)

**Stack:**
| Tool | Purpose | Cost |
|---|---|---|
| Claude/ChatGPT | Word origin scripts from Online Etymology Dictionary | $20/month |
| ElevenLabs Creator | Clear US-English voice (builds western audience signal) | $22/month |
| Pika Labs / Runway Gen-3 | Etymology tree animations, map visualizations | $20–35/month |
| CapCut | Animated text for word reveals (reveal mechanic is core) | Free |
| Canva Pro | Thumbnails with word + breakdown visible | $13/month |
| Make.com + Buffer | Cross-posting to YouTube Shorts + Instagram Reels | $9–18/month |

**Sample topics:**
- The word "Disaster" literally means "bad star" — Romans blamed misfortune on misaligned planets
- English has no word for this Portuguese feeling — saudade explained in 60 seconds
- Contronyms: "Sanction" means both to allow AND to punish
- Why the letter Q exists when K does the same job (the Latin conquest explanation)
- The last speaker of Ubykh died in 1992 — what disappears when a language goes extinct
- Berserk comes from Viking warriors who wore bear pelts and entered battle in a trance
- Algospeak: why TikTok censorship is creating an entirely new coded language in real time
- The word "Muscle" comes from Latin for "little mouse" — a flexing bicep looks like one under skin
- Why Australians turn every word into "arvo", "servo", "brekky" — the linguistic rule behind it
- Schadenfreude, Hygge, Mamihlapinatapai — 5 emotions English has no word for

**Sample video idea (first video):**
> **"The Word 'Disaster' Literally Means Bad Star"**
> Hook: "Every time you say disaster, you're blaming the planets."
> Format: animated star map zooming in → Latin text reveal → English word reveal. ElevenLabs voice. 40 seconds. Ends: "Follow for one word origin daily."

---

## Tier 2 — Viable but Lower Priority

| Niche | Best sub-niche | Why lower |
|---|---|---|
| Self-Improvement / Habits | Cognitive biases + decision-making | 20,000+ active channels, extremely saturated. Survivable only with a precise differentiating angle. |
| Historical Mysteries | LiDAR archaeology + non-Western lost civilizations | Medium competition. AI visuals flagged for accuracy — needs real stock footage. |
| Neuroscience / Brain | Procrastination + motivation neuroscience | Too similar audience to psychology channel. Better as that channel's content expansion. |
| Crime / Scam Psychology | Scam mechanics + manipulation tactics | Automation 6/10. AdSense suppressed by brand-safety filters. More complex backend. |

---

## Tier 3 — Skip

| Niche | Reason |
|---|---|
| Health / Nutrition Myths | YMYL — ChatGPT fabricates citations 16% of the time. Needs human fact-checker (4–8 hrs/week). Not viable for solo operator. |
| Broad Science Facts | Redundant with animal channel. Competes with Bright Side (44M subs), SciShow (8.38M). |
| Career / Workplace | Face-brand dominant. Weak affiliates ($12–30/sale vs $45–200 for BetterHelp). No moat. |
| Parenting | COPPA demonetization risk — "made for kids" classification kills comments, end screens, and most ads. Structural, not fixable. |
| Weird Facts / Comparisons (Sticky Info style) | No product path. Lowest RPM in the set ($0.06–0.18/1K views). Highest slop-saturation risk. Channels = distribution but no money. |

---

## Portfolio Plan

Four channels, $224–323/month total operating cost:

| Channel | Audience | Primary monetization | Cost/month |
|---|---|---|---|
| GK Quiz *(locked, in plan.md)* | Indian exam aspirants | Telegram premium + digital products | ~$5 |
| Psychology / Narcissism | Western women 25–45 | BetterHelp affiliate + $27 ebook | $75–110 |
| Animal Behavior | Western nature enthusiasts | Amazon Associates + brand deals | $66–96 |
| Etymology / Linguistics *(optional 3rd)* | Western educated adults 25–45 | Duolingo sponsors + $37 PDF | $84–117 |

**Test window:** 60 days per channel.
**Kill signal:** below 500 followers/week growth OR zero affiliate clicks at 30 days.
**Double-down signal:** intent signal (click-through to off-platform destination). Launch digital product at 5K subscribers.

---

## Next Steps

1. Pick which channel to build pipeline for first (Psychology, Animal, or Etymology).
2. Spec the automation pipeline for chosen channel (n8n + ElevenLabs + video assembly + posting).
3. Define the off-platform destination (Gumroad product or affiliate link) before posting video one.
4. Build a 30-video batch before first post — signals viability to algorithm, prevents stall.
