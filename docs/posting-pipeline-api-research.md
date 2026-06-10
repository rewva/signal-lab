# Posting Pipeline -- Platform API Research (Verdict: GO)

_Session date: 2026-06-08. Deep-research workflow: 6 angles, 104 agents, 21 primary sources, 88 claims extracted, 25 adversarially verified (24 confirmed, 1 killed). Resolves the open questions left by the 2026-06-05 pass. Do not relitigate without new data._

## Why this mattered

Both `docs/plan.md` and the daily-gk-quiz design named **Meta App Review + Business Verification for a solo operator** as the single biggest unknown -- "validate FIRST, gate everything else on it." This pass resolves it, plus the four other open API questions.

---

## VERDICT: GO (with one binding precondition)

A solo operator in India with **no registered company** can programmatically auto-post Reels/Shorts to their **own** YouTube, Facebook Page, and Instagram Business/Creator accounts in 2026. Meta Business Verification and App Review are **NOT required** for this self-posting scenario.

**The binding precondition (this is the CONDITIONAL part):** the operator MUST add their own FB Page and IG Business/Creator accounts as **role-holders (Admin / Developer / Tester)** on their own Meta app. Self-posting then stays in **Standard Access**, which never hits the verification gate. Standard Access imposes lower rate limits (e.g. ~25 IG API posts/24h) -- fine for 1-5/day, but a ceiling to respect.

---

## Blocker 1 -- Meta App Review / Business Verification: RESOLVED (GO)

A role-holder-only app operates under **Standard Access**, where all permissions can be granted and all features stay active **without App Review or Business Verification**. App Review + Business Verification are only triggered by **Advanced Access** -- i.e. acting on accounts you do NOT own/manage (the multi-tenant Tech Provider case).

- Meta's App Review doc: "My app is only for a business I own or manage" -> Standard Access -> App Review "Not required."
- Business Verification doc (verbatim): "If your app will only be used by app users who have a role on the app itself you do not need to complete verification; these users can grant your app any permissions at any time and all features are always active."
- This **sidesteps the no-registered-company problem entirely** -- the operator never reaches the verification gate, so the GST/legal-entity question is moot for self-posting.

**Confidence:** high (3-0, primary docs).

**Mild internal tension (flagged):** a Feb-2023 Meta blog post says individual verification will no longer be allowed once business verification is complete; the authoritative app-review and business-verification pages resolve in favor of "no verification needed for the self-posting/role-holder case." Re-verify the Standard-vs-Advanced boundary before building -- Meta has tightened verification repeatedly since Feb 2023.

Sources:
- https://developers.facebook.com/docs/instagram-platform/app-review/
- https://developers.facebook.com/docs/development/release/business-verification/
- https://developers.facebook.com/docs/graph-api/overview/access-levels/
- https://developers.facebook.com/docs/resp-plat-initiatives/individual-processes/app-review

---

## Blocker 2 -- Facebook Page Reels upload flow: RESOLVED

Three-phase flow (Graph API v25.0):

1. **start** -- `POST graph.facebook.com/v25.0/{page_id}/video_reels` with `upload_phase=start` -> returns `video_id` (+ an `upload_url` field; treat cautiously, see note).
2. **upload** -- binary `POST` to the dedicated host `rupload.facebook.com/video-upload/{version}/{video_id}` with headers `Authorization: OAuth {page_access_token}`, `Content-Type: application/octet-stream`, `file_size`, `offset`. (Binary goes to **rupload.facebook.com**, NOT graph.facebook.com.)
3. **finish** -- `POST {page_id}/video_reels` with `upload_phase=finish`, `video_id`, `video_state=PUBLISHED`.

- `upload_phase` values are lowercase (`start` / `finish`).
- Permissions: `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`, plus the `CREATE_CONTENT` task capability on the Page.
- **Do NOT confuse with the generic Video API** (`POST /{APP_ID}/uploads` -> `POST /upload:{session_id}` -> `POST /{PAGE_ID}/videos`). That is a separate endpoint for ordinary Page videos, not Reels.
- **Refuted sub-claim (1-2 killed):** that the `start` response's `upload_url` is the binary destination. Rely on the documented `rupload.facebook.com` host instead.

**Confidence:** high (3-0, primary docs + Meta's own fbsamples Postman collection).

Sources:
- https://developers.facebook.com/docs/video-api/guides/reels-publishing/
- https://developers.facebook.com/docs/graph-api/reference/page/video_reels/
- https://github.com/fbsamples/Facebook-Reels-Publishing-API-Postman-Collection

---

## Blocker 3 -- Instagram Reels publish + encoding specs: RESOLVED

Container flow:

1. `POST /{ig-user-id}/media` with `media_type=REELS` (+ `video_url` for hosted media, OR `upload_type=resumable` for direct upload to `rupload.facebook.com/ig-api-upload/{container-id}`).
2. Poll `GET /{container-id}?fields=status_code` until `FINISHED` (required for async video processing).
3. `POST /{ig-user-id}/media_publish` with `creation_id`.

**Permissions differ by login path:**
- **Instagram Login path:** `instagram_business_basic` + `instagram_business_content_publish`.
- **Facebook Login path:** `instagram_basic` + `instagram_content_publish` + `pages_read_engagement` (plus `ads_management` OR `business_management` if the Page role was granted via Business Manager).
- Note: the scope was renamed `instagram_content_publish` -> `instagram_business_content_publish` (Jan 2025) on the IG Login path.

**Reels encoding specs:** MOV/MP4 (no edit lists, moov atom at front), HEVC or H.264 (progressive, closed GOP, 4:2:0), 23-60 fps, max 1920 horizontal px (9:16 recommended), VBR up to 25 Mbps, AAC audio 128 kbps up to 48 kHz, 1-2 channels, 3s-15min, 300MB max.

**IG is MORE permissive than FB Reels:** allows HEVC, 23-60 fps, up to 25 Mbps, up to 15min/300MB at the API level (Reels-tab eligibility separately prefers ~5-90s).

**Common baseline that satisfies BOTH platforms:** a single encode targeting **MP4 / H.264 / 1080x1920 / 24-60 fps / AAC-LC 128k / 48kHz**. This confirms the FFmpeg-normalizer design (one normalized file works for FB + IG).

After publishing, IG `media_type` returns `VIDEO` not `REELS` -- use `media_product_type` to confirm a Reel.

**Confidence:** high (3-0, primary docs).

Sources:
- https://developers.facebook.com/docs/instagram-platform/content-publishing/
- https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media/

---

## Blocker 4 -- YouTube Data API v3 quota: RESOLVED

A new project gets a **default 10,000 units/day** (combined for all endpoints) PLUS separate capped allocations of **100 search.list calls/day** and **100 videos.insert calls/day**.

- Google getting-started (verbatim): "Projects that enable the YouTube Data API have a default quota allocation of 100 search.list calls, 100 videos.insert calls, and 10,000 units per day combined for all other endpoints."
- **Resolves the prior conflict:** uploads draw against the dedicated **100-calls/day cap**, independent of the disputed per-call unit cost (1600 old vs ~100 reduced Dec 2025). Whether videos.insert costs 1600 or 100 units is **moot** -- the call-count cap governs.
- 1-5 uploads/day across a few channels is trivially under the 100-upload ceiling. **No quota increase request needed.**

**Confidence:** high (3-0, primary docs).

Sources:
- https://developers.google.com/youtube/v3/getting-started
- https://developers.google.com/youtube/v3/determine_quota_cost

---

## Blocker 5 -- AI disclosure: PARTIALLY RESOLVED

**YouTube (resolved):** Disclosure is REQUIRED only for realistic synthetic/altered media that could mislead -- making a real person appear to say/do something, altering footage of a real event/place, or synthetically generating a real person's voice. Disclosure is **NOT required** for:
- AI used for productivity (scripts, content ideas, automatic captions),
- clearly unrealistic content, minor edits (color/filters/beauty/blur),
- **cloning one's OWN voice** for voiceovers/dubs.

=> For our faceless channels (generic AI narrator or operator's own cloned voice over non-deceptive visuals like quiz cards / stock wildlife footage), **no YouTube disclosure is triggered.** (Disclosure exemption does NOT exempt content from the inauthentic-mass-produced-content / anti-slop scrutiny -- that is separate.)

**Meta (UNRESOLVED -- still open):** No surviving claim addressed whether Meta requires an "AI info" label on automated Reels in 2026, what triggers it (AI voiceover vs scripting), or whether an API field exists to set it programmatically. **Treat as an open question, not a cleared blocker.**

Sources:
- https://support.google.com/youtube/answer/14328491
- https://blog.youtube/news-and-events/disclosing-ai-generated-content/

---

## Remaining open questions

1. **Meta AI-disclosure (Blocker 5 Meta side):** Does Meta require an "AI info" label on automated Reels in 2026, and is there an API field on the video_reels / media container to set it? Needs a dedicated pass against Meta business help + Graph API reference.
2. **FB Page Reels Standard Access volume ceiling:** the 25/24h limit is documented for Instagram; confirm the Facebook Page Reels equivalent before scaling FB cadence.
3. **Durability of the role-holder exemption:** Meta has expanded Business Verification repeatedly since Feb 2023. Monitor whether "app users with a role" stays exempt; have a fallback if Meta later requires verification even for self-posting.
4. **videos.insert per-call cost** (1600 vs ~100 units, Dec 2025): immaterial to the verdict (call-count cap governs), still unconfirmed.

---

## Impact on the build

- **The Meta gate is cleared.** The daily-gk-quiz build order step 1 ("prove publish access, especially Meta verification") and plan.md risk #2 are resolved to GO -- no longer blocking.
- All three adapters (YouTube, Facebook Reels, Instagram Reels) now have confirmed flows and permission sets -- the `signal-lab-publisher` adapters can be built.
- The FFmpeg normalizer's single-encode target (MP4/H.264/1080x1920/24-60fps/AAC-LC 128k/48kHz) is confirmed to satisfy YouTube + FB + IG.
- One precondition before any Meta API call: add own FB Page + IG Business/Creator accounts as role-holders on the Meta app, and have the IG account accept the role invite.
