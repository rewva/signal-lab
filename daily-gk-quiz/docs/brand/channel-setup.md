# Pakka GK — channel setup kit

Everything to create the YouTube + Instagram channels. Assets render from the Remotion
compositions `BrandAvatar` (1080x1080) and `BrandBanner` (2560x1440):

```
cd render
npx remotion still src/index.ts BrandAvatar out/brand/pakka-avatar.png
npx remotion still src/index.ts BrandBanner out/brand/pakka-banner.png
```

## Handles & links (reserve identical everywhere)
- Handle: **@pakkagk** (YouTube + Instagram) — YouTube + both domains confirmed free; eyeball Instagram.
- Domain: **pakkagk.in** (grab it; `.com` is also free as backup).
- Tagline: **Verified GK. Every day.**

## Avatar
`render/out/brand/pakka-avatar.png` — stacked "Pakka / GK" lockup on Exam-Ink. Upload as the
profile picture on both platforms (YouTube crops to a circle; the lockup sits safely centered).

## Banner (YouTube channel art)
`render/out/brand/pakka-banner.png` — 2560x1440, all text inside the 1546x423 safe area.

## Bios

**YouTube — channel description / About:**
> Pakka GK — one verified General Knowledge question every day for SSC, Banking (IBPS/SBI) and
> Railways (RRB) aspirants.
>
> Every answer is sourced from official references (Constitution of India, NCERT, PIB, RBI and
> more) — no guesswork, no slop. Static GK + the facts that actually repeat in exams, one Short
> at a time.
>
> New quiz daily. Comment your answer, challenge a friend, build your streak.
> #SSC #Banking #Railways #GK #CurrentAffairs

**Instagram bio (~150 chars):**
> Pakka GK ✅
> 1 verified GK question daily
> SSC · Banking · Railways
> Every answer sourced 📚 New quiz daily 👇

**One-line (X / handles directory):**
> Daily verified GK for SSC, Banking & Railways aspirants. Every answer sourced.

## Setup checklist
- [ ] Reserve @pakkagk on YouTube + Instagram (check IG availability first).
- [ ] Register pakkagk.in (and .com as backup).
- [ ] Upload avatar (both platforms) + banner (YouTube).
- [ ] Paste the bios; set links to pakkagk.in once it exists.
- [ ] YouTube: set channel keywords (SSC, IBPS, SBI, RRB, GK, current affairs, quiz).
- [ ] Connect accounts for auto-posting (publisher.connect youtube / meta) when ready.

## Brand extras (done)
- **On-video watermark:** `@pakkagk` renders at the bottom of every Short (in `Standard.tsx`) —
  applies on the next render; the 10 already queued predate it.
- **Logo sting** (4s intro/outro): `npx remotion render src/index.ts LogoSting out/brand/pakka-sting.mp4`
- **IG highlight covers** (1080x1080, parametric label):
  `npx remotion still src/index.ts HighlightCover out/brand/cover-polity.png --props='{"label":"POLITY"}'`
  Rendered set: DAILY, POLITY, HISTORY, GEOGRAPHY, ECONOMY, SCIENCE, STATIC GK, ABOUT.

## Backlog (offer-on-request)
Video end-card variant, an outro CTA frame, a square (1:1) sting for feed posts.
