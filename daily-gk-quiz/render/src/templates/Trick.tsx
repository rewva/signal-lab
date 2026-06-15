import React from "react";
import { AbsoluteFill, Audio, Sequence, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { TRICK } from "../theme";
import { buildTimeline, type Timeline } from "../timeline";
import { audioCues } from "../audio-cues";
import type { QuizProps } from "../props";
import { QuestionView, OptionsView } from "../blocks/QuestionOptions";
import { CountdownView, LockBeatView, WhyView, SourceLineView, CtaView, VerifiedBadgeView } from "../blocks/Pieces";

export const TrickHookView: React.FC<{ trickHook: string }> = ({ trickHook }) => (
  <div style={{ fontSize: 110, fontWeight: 900, lineHeight: 0.9, textTransform: "uppercase",
                color: TRICK.ink, fontFamily: "Impact, 'Arial Narrow', sans-serif" }}>
    {trickHook}
  </div>
);

// Trick keeps the original single-card beat model (independent of Standard's scene model).
function trickState(frame: number, tl: Timeline) {
  const revealed = frame >= tl.reveal.from;
  const showLock = frame >= tl.lock.from && frame < tl.reveal.from;
  const inCountdown = frame >= tl.countdown.from && frame < tl.lock.from;
  const cdWindow = tl.lock.from - tl.countdown.from;
  const elapsed = frame - tl.countdown.from;
  const countdownN = inCountdown ? Math.max(1, Math.min(3, 3 - Math.floor(elapsed / (cdWindow / 3)))) : 0;
  const showWhy = frame >= tl.why.from;
  return { revealed, showLock, inCountdown, countdownN, showWhy };
}

export const Trick: React.FC<QuizProps> = (props) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const tl = buildTimeline(fps, props.vo);
  const s = trickState(frame, tl);
  return (
    <AbsoluteFill style={{ background: TRICK.bg, padding: "64px 56px", display: "flex",
                           flexDirection: "column", fontFamily: "Arial, sans-serif", color: TRICK.ink }}>
      {audioCues(props, tl).map((c) => (
        <Sequence key={c.key} from={c.from} name={`vo-${c.key}`}>
          <Audio src={staticFile(c.src)} />
        </Sequence>
      ))}
      <TrickHookView trickHook={props.trickHook} />
      <div style={{ marginTop: 30, border: `8px solid ${TRICK.ink}`, background: "#fff7e8",
                    boxShadow: `16px 16px 0 ${TRICK.ink}`, padding: "40px 36px" }}>
        <div style={{ marginBottom: 22 }}><QuestionView question={props.question} tone="dark" /></div>
        <OptionsView options={props.options} correctLetter={props.correctLetter} revealed={s.revealed} tone="dark" />
        <div style={{ marginTop: 28, display: "flex", gap: 26, alignItems: "center" }}>
          {s.inCountdown && <CountdownView n={s.countdownN} />}
          {s.showLock && <LockBeatView />}
          {s.revealed && <VerifiedBadgeView tone="dark" />}
        </div>
        {s.showWhy && <div style={{ marginTop: 24 }}><WhyView explanation={props.explanation} tone="dark" /></div>}
      </div>
      <div style={{ marginTop: "auto" }}>
        <CtaView cta={props.cta} tone="dark" />
        <SourceLineView sourceLine={props.sourceLine} promoted={s.revealed} tone="dark" />
      </div>
    </AbsoluteFill>
  );
};
