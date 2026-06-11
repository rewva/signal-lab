import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { STANDARD } from "../theme";
import { buildTimeline, type Timeline } from "../timeline";
import type { QuizProps } from "../props";
import { BrandHeaderView, DifficultyChipView, CategoryBandView, DayNumberView } from "../blocks/StaticBlocks";
import { QuestionView, OptionsView } from "../blocks/QuestionOptions";
import { CountdownView, LockBeatView, WhyView, VerifiedBadgeView, SourceLineView, CtaView } from "../blocks/Pieces";

// Pure frame -> view-state (unit-tested). No React, no Remotion hooks.
export function standardState(frame: number, tl: Timeline) {
  const revealed = frame >= tl.reveal.from;
  const showLock = frame >= tl.lock.from && frame < tl.reveal.from;
  const inCountdown = frame >= tl.countdown.from && frame < tl.lock.from;
  const cdWindow = tl.lock.from - tl.countdown.from; // split into thirds so 3-2-1 all show
  const elapsed = frame - tl.countdown.from;
  const countdownN = inCountdown
    ? Math.max(1, Math.min(3, 3 - Math.floor(elapsed / (cdWindow / 3))))
    : 0;
  const showWhy = frame >= tl.why.from;
  return { revealed, showLock, inCountdown, countdownN, showWhy };
}

export const Standard: React.FC<QuizProps> = (props) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const tl = buildTimeline(fps);
  const s = standardState(frame, tl);
  return (
    <AbsoluteFill style={{ background: STANDARD.bg, padding: "64px 60px",
                           display: "flex", flexDirection: "column",
                           fontFamily: "Arial, Helvetica, sans-serif" }}>
      <BrandHeaderView dayNumber={props.dayNumber} />
      <div style={{ display: "flex", gap: 20, alignItems: "center", marginTop: 26 }}>
        <DayNumberView dayNumber={props.dayNumber} />
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <CategoryBandView category={props.category} />
          <DifficultyChipView difficulty={props.difficulty} examPrefix={props.examPrefix} />
        </div>
      </div>
      <div style={{ marginTop: 34 }}><QuestionView question={props.question} /></div>
      <div style={{ marginTop: 40 }}>
        <OptionsView options={props.options} correctLetter={props.correctLetter} revealed={s.revealed} />
      </div>
      <div style={{ marginTop: 36, minHeight: 140, display: "flex", alignItems: "center", gap: 26 }}>
        {s.inCountdown && <CountdownView n={s.countdownN} />}
        {s.showLock && <LockBeatView />}
        {s.revealed && <VerifiedBadgeView />}
      </div>
      {s.showWhy && <div style={{ marginTop: 8 }}><WhyView explanation={props.explanation} /></div>}
      <div style={{ marginTop: "auto" }}>
        <CtaView cta={props.cta} />
        <div style={{ marginTop: 14 }}>
          <SourceLineView sourceLine={props.sourceLine} promoted={s.revealed} />
        </div>
      </div>
    </AbsoluteFill>
  );
};
