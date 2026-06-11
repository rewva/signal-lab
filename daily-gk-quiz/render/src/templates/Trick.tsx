import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { TRICK } from "../theme";
import { buildTimeline } from "../timeline";
import { standardState } from "./Standard";
import type { QuizProps } from "../props";
import { QuestionView, OptionsView } from "../blocks/QuestionOptions";
import { CountdownView, LockBeatView, WhyView, SourceLineView, CtaView, VerifiedBadgeView } from "../blocks/Pieces";

export const TrickHookView: React.FC<{ trickHook: string }> = ({ trickHook }) => (
  <div style={{ fontSize: 110, fontWeight: 900, lineHeight: 0.9, textTransform: "uppercase",
                color: TRICK.ink, fontFamily: "Impact, 'Arial Narrow', sans-serif" }}>
    {trickHook}
  </div>
);

export const Trick: React.FC<QuizProps> = (props) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = standardState(frame, buildTimeline(fps));
  return (
    <AbsoluteFill style={{ background: TRICK.bg, padding: "64px 56px", display: "flex",
                           flexDirection: "column", fontFamily: "Arial, sans-serif", color: TRICK.ink }}>
      <TrickHookView trickHook={props.trickHook} />
      <div style={{ marginTop: 30, border: `8px solid ${TRICK.ink}`, background: "#fff7e8",
                    boxShadow: `16px 16px 0 ${TRICK.ink}`, padding: "40px 36px" }}>
        <div style={{ marginBottom: 22 }}><QuestionView question={props.question} /></div>
        <OptionsView options={props.options} correctLetter={props.correctLetter} revealed={s.revealed} />
        <div style={{ marginTop: 28, display: "flex", gap: 26, alignItems: "center" }}>
          {s.inCountdown && <CountdownView n={s.countdownN} />}
          {s.showLock && <LockBeatView />}
          {s.revealed && <VerifiedBadgeView />}
        </div>
        {s.showWhy && <div style={{ marginTop: 24 }}><WhyView explanation={props.explanation} /></div>}
      </div>
      <div style={{ marginTop: "auto" }}>
        <CtaView cta={props.cta} />
        <SourceLineView sourceLine={props.sourceLine} promoted={s.revealed} />
      </div>
    </AbsoluteFill>
  );
};
