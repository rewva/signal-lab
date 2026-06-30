import React from "react";
import { AbsoluteFill, Audio, Sequence, staticFile, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { STANDARD } from "../theme";
import { FONT_FAMILY } from "../font";
import { buildTimeline, type Timeline } from "../timeline";
import { audioCues } from "../audio-cues";
import type { QuizProps } from "../props";
import { BrandHeaderView, DifficultyChipView, CategoryBandView, PakkaSeal } from "../blocks/StaticBlocks";

// Pure frame -> view-state (unit-tested). No React, no Remotion hooks.
//   scene A: ask + in-place reveal (question + 4 options stay; correct one lights up here)
//   scene B: answer page (correct option + "why it matters" + source, Pakka-stamped)
//   scene C: bonus / comment challenge
export function standardState(frame: number, tl: Timeline) {
  const scene: "A" | "B" | "C" =
    frame >= tl.ctaHold.from ? "C" : frame >= tl.why.from ? "B" : "A";
  const revealed = frame >= tl.reveal.from;
  const counting = frame >= tl.countdown.from && frame < tl.reveal.from;
  return { scene, revealed, counting };
}

const PILL = (extra: React.CSSProperties = {}): React.CSSProperties => ({
  display: "flex", alignItems: "center", gap: 24, padding: "30px 36px", borderRadius: 28,
  fontSize: 50, fontWeight: 700, border: `3px solid ${STANDARD.pillOutline}`, color: STANDARD.text, ...extra,
});
// OMR-bubble option marker (circular, like a filled answer bubble).
const BADGE = (txt: string, bg: string, fg: string) => (
  <span style={{ width: 78, height: 78, borderRadius: 999, fontSize: 40, fontWeight: 800, background: bg, color: fg,
                 display: "flex", alignItems: "center", justifyContent: "center", flex: "0 0 auto" }}>{txt}</span>
);

export const Standard: React.FC<QuizProps> = (props) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const tl = buildTimeline(fps, props.vo);
  const s = standardState(frame, tl);

  // Each scene enters with a slide-from-right + fade (a "new slide arrives" cut).
  const sceneIn = (fromFrame: number) => {
    const p = spring({ frame: frame - fromFrame, fps, config: { damping: 18, mass: 0.8, stiffness: 110 }, durationInFrames: 18 });
    return { opacity: interpolate(p, [0, 1], [0, 1], { extrapolateRight: "clamp" }),
             transform: `translateX(${interpolate(p, [0, 1], [70, 0])}px)` };
  };
  const item = (i: number, base: number) => {
    const p = spring({ frame: frame - base - i * 5, fps, config: { damping: 15, mass: 0.7 }, durationInFrames: 18 });
    return { opacity: interpolate(p, [0, 1], [0, 1], { extrapolateRight: "clamp" }),
             transform: `translateY(${interpolate(p, [0, 1], [40, 0])}px)` };
  };

  // continuous animated background (shared across scenes for continuity)
  const t = frame / fps;
  const gx = 50 + 13 * Math.sin(t * 0.6), gy = 34 + 10 * Math.cos(t * 0.45);
  const gx2 = 72 + 15 * Math.cos(t * 0.35), gy2 = 80 + 10 * Math.sin(t * 0.5);
  const bgScale = 1.06 + 0.03 * Math.sin(t * 0.3);

  // --- small corner timer ring: depletes from countdown.from to reveal.from ---
  const ringProgress = interpolate(frame, [tl.countdown.from, tl.reveal.from], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const ringTotal = Math.max(1, tl.reveal.from - tl.countdown.from);
  const ringSecs = Math.max(0, Math.ceil((ringProgress * ringTotal) / fps));

  // --- in-place reveal easing on scene A (smooth, no hard snap) ---
  const revP = spring({ frame: frame - tl.reveal.from, fps, config: { damping: 14, mass: 0.8, stiffness: 120 }, durationInFrames: 22 });
  const correctGlow = s.revealed ? revP : 0;                 // 0..1 ease into the green state
  const correctPop = interpolate(revP, [0, 0.5, 1], [1, 1.06, 1.03]);
  const wrongDim = interpolate(correctGlow, [0, 1], [1, 0.32]); // wrong options fade back
  const flash = s.revealed ? interpolate(frame - tl.reveal.from, [0, 6, 22], [0, 0.4, 0], { extrapolateRight: "clamp" }) : 0;

  // scene B answer pill pop
  const ansP = spring({ frame: frame - tl.why.from, fps, config: { damping: 12, mass: 0.6, stiffness: 140 }, durationInFrames: 20 });
  const correct = props.options.find((o) => o.letter === props.correctLetter);

  // correct-answer state recolors in place toward the semantic green
  const correctBorder = correctGlow > 0 ? STANDARD.correct : STANDARD.pillOutline;
  const correctBg = `rgba(${STANDARD.correctRgb},${(0.18 * correctGlow).toFixed(3)})`;

  return (
    <AbsoluteFill style={{ background: STANDARD.bg, fontFamily: FONT_FAMILY, overflow: "hidden" }}>
      <AbsoluteFill style={{ transform: `scale(${bgScale})`, background:
        `radial-gradient(circle at ${gx}% ${gy}%, rgba(${STANDARD.accentRgb},0.16), transparent 42%),` +
        `radial-gradient(circle at ${gx2}% ${gy2}%, rgba(43,182,168,0.16), transparent 46%),` + STANDARD.bgDeep }} />

      {audioCues(props, tl).map((c) => (
        <Sequence key={c.key} from={c.from} name={`vo-${c.key}`}><Audio src={staticFile(c.src)} /></Sequence>
      ))}

      {/* persistent top brand strip */}
      <div style={{ position: "absolute", top: 56, left: 60, right: 60, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <BrandHeaderView dayNumber={props.dayNumber} />
        <DifficultyChipView difficulty={props.difficulty} examPrefix={props.examPrefix} />
      </div>

      {/* ============ SCENE A: ASK + IN-PLACE REVEAL ============ */}
      {s.scene === "A" && (
        <AbsoluteFill style={{ padding: "200px 64px 90px", display: "flex", flexDirection: "column", justifyContent: "center", ...sceneIn(tl.question.from) }}>
          <div style={item(0, tl.question.from)}><CategoryBandView category={props.category} /></div>
          <h1 style={{ fontSize: 86, fontWeight: 800, lineHeight: 1.07, letterSpacing: "-.02em", color: STANDARD.text, margin: "26px 0 46px", ...item(1, tl.question.from) }}>
            {props.question}
          </h1>
          <div style={{ display: "flex", flexDirection: "column", gap: 22 }}>
            {props.options.map((o, i) => {
              const isCorrect = o.letter === props.correctLetter;
              const enter = item(2 + i, tl.options.from);
              // smooth per-option state: correct glows/pops in place, wrong ones dim
              const opacity = isCorrect ? enter.opacity : (enter.opacity as number) * wrongDim;
              const scale = isCorrect ? correctPop : 1;
              const lit = isCorrect && correctGlow > 0.5;
              return (
                <div key={o.letter} style={PILL({
                  transform: `${enter.transform} scale(${scale})`,
                  opacity,
                  border: `3px solid ${isCorrect ? correctBorder : STANDARD.pillOutline}`,
                  background: isCorrect ? correctBg : "transparent",
                  transition: "none",
                })}>
                  {BADGE(o.letter, lit ? STANDARD.correct : STANDARD.pillOutline, lit ? STANDARD.bg : "#fff")}
                  <span style={{ fontWeight: lit ? 800 : 700 }}>{o.text}</span>
                </div>
              );
            })}
          </div>

          {/* depleting timer ring, bottom-right corner; brand vermilion; fades out once revealed */}
          <div style={{ position: "absolute", right: 60, bottom: 78, opacity: interpolate(correctGlow, [0, 1], [1, 0]),
                        display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
            <div style={{ width: 168, height: 168, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center",
                          boxShadow: `0 0 38px rgba(${STANDARD.accentRgb},${(0.45 * ringProgress).toFixed(3)})`,
                          background: `conic-gradient(${STANDARD.accent} ${ringProgress * 360}deg, rgba(255,255,255,0.12) 0deg)` }}>
              <div style={{ width: 128, height: 128, borderRadius: "50%", background: STANDARD.bg, display: "flex", alignItems: "center", justifyContent: "center" }}>
                <span style={{ color: STANDARD.accent, fontSize: 76, fontWeight: 800, transform: `scale(${interpolate(ringSecs % 1 === 0 ? (frame % fps) / fps : 0, [0, 0.15, 1], [1.25, 1, 1])})` }}>{ringSecs}</span>
              </div>
            </div>
            <span style={{ fontSize: 24, fontWeight: 800, letterSpacing: ".24em", color: STANDARD.muted }}>SECONDS</span>
          </div>
        </AbsoluteFill>
      )}

      {/* ============ SCENE B: ANSWER PAGE (question on top, answer+why in one stamped card) ============ */}
      {s.scene === "B" && (
        <AbsoluteFill style={{ padding: "168px 56px 96px", display: "flex", flexDirection: "column", ...sceneIn(tl.why.from) }}>
          {/* top: the question, for context */}
          <h2 style={{ fontSize: 58, fontWeight: 800, lineHeight: 1.14, color: STANDARD.text, margin: "0 0 40px", ...item(0, tl.why.from) }}>{props.question}</h2>

          {/* card: correct answer + why, grouped so spacing reads as padding, not a gap */}
          <div style={{ position: "relative", flex: 1, display: "flex", flexDirection: "column", justifyContent: "center", gap: 40,
                        border: `2px solid ${STANDARD.pillOutline}`, borderRadius: 36, padding: "56px 48px",
                        background: "rgba(255,255,255,0.04)", ...item(1, tl.why.from) }}>
            {/* the Pakka Seal, stamped onto the card corner */}
            <div style={{ position: "absolute", top: -34, right: 30,
                          transform: `scale(${interpolate(Math.min(ansP, 1.4), [0, 0.6, 1, 1.4], [0.5, 1.12, 1, 1])})`, transformOrigin: "center" }}>
              <PakkaSeal size={150} />
            </div>

            {/* the correct answer */}
            <div>
              <div style={{ fontSize: 28, fontWeight: 800, letterSpacing: ".18em", textTransform: "uppercase", color: STANDARD.correct, marginBottom: 18 }}>Correct answer</div>
              <div style={{ transform: `scale(${interpolate(Math.min(ansP, 1.4), [0, 0.6, 1, 1.4], [0.8, 1.08, 1, 1])})`, transformOrigin: "left center" }}>
                <div style={PILL({ border: `4px solid ${STANDARD.correct}`, background: `rgba(${STANDARD.correctRgb},0.18)`, fontSize: 56, padding: "30px 38px" })}>
                  {BADGE(props.correctLetter, STANDARD.correct, STANDARD.bg)}
                  <span style={{ fontWeight: 800 }}>{correct ? correct.text : ""}</span>
                </div>
              </div>
            </div>

            <div style={{ height: 2, background: "rgba(255,255,255,0.10)" }} />

            {/* why it matters */}
            <div style={{ borderLeft: `10px solid ${STANDARD.accent}`, paddingLeft: 28 }}>
              <div style={{ fontSize: 28, fontWeight: 800, letterSpacing: ".14em", textTransform: "uppercase", color: STANDARD.accent, marginBottom: 14 }}>Why it matters</div>
              <div style={{ fontSize: 48, fontWeight: 500, lineHeight: 1.32, color: STANDARD.text }}>{props.explanation}</div>
              <div style={{ marginTop: 24, fontSize: 28, fontWeight: 700, color: STANDARD.muted }}>Source: {props.sourceLine}</div>
            </div>
          </div>
        </AbsoluteFill>
      )}

      {/* ============ SCENE C: BONUS / COMMENT CHALLENGE ============ */}
      {s.scene === "C" && (
        <AbsoluteFill style={{ padding: "70px", display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", textAlign: "center", ...sceneIn(tl.ctaHold.from) }}>
          {props.commentChallenge ? (
            <>
              <div style={{ fontSize: 32, fontWeight: 800, letterSpacing: ".2em", textTransform: "uppercase", color: STANDARD.accent, ...item(0, tl.ctaHold.from) }}>Bonus Question</div>
              <div style={{ fontSize: 68, fontWeight: 800, color: STANDARD.text, lineHeight: 1.12, margin: "28px 0 40px", ...item(1, tl.ctaHold.from) }}>{props.commentChallenge}</div>
              <div style={{ fontSize: 50, fontWeight: 800, color: STANDARD.bg, background: STANDARD.accent, borderRadius: 999, padding: "24px 50px", ...item(2, tl.ctaHold.from) }}>Comment your answer below</div>
            </>
          ) : (
            <div style={{ fontSize: 70, fontWeight: 800, color: STANDARD.text, lineHeight: 1.15, ...item(0, tl.ctaHold.from) }}>{props.cta}</div>
          )}
          <div style={{ marginTop: 46, fontSize: 30, fontWeight: 700, color: STANDARD.muted, ...item(3, tl.ctaHold.from) }}>Source: {props.sourceLine}</div>
        </AbsoluteFill>
      )}

      <AbsoluteFill style={{ background: "#ffffff", opacity: flash, pointerEvents: "none" }} />
    </AbsoluteFill>
  );
};
