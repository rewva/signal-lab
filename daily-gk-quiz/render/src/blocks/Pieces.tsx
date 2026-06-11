import React from "react";
import { STANDARD } from "../theme";

export const CountdownView: React.FC<{ n: number }> = ({ n }) => (
  <div style={{ width: 132, height: 132, borderRadius: 999, border: `7px solid ${STANDARD.accent}`,
                color: STANDARD.accent, fontSize: 70, fontWeight: 900, display: "flex",
                alignItems: "center", justifyContent: "center" }}>{n}</div>
);

export const LockBeatView: React.FC = () => (
  <div style={{ fontSize: 60, fontWeight: 900, color: STANDARD.accent, letterSpacing: "-.01em" }}>
    Lock your answer...
  </div>
);

export const WhyView: React.FC<{ explanation: string }> = ({ explanation }) => (
  <div style={{ borderLeft: `10px solid ${STANDARD.accent}`, paddingLeft: 28 }}>
    <div style={{ fontSize: 24, fontWeight: 800, letterSpacing: ".14em", textTransform: "uppercase",
                  color: STANDARD.accent, marginBottom: 12 }}>Why it matters</div>
    <div style={{ fontSize: 38, fontWeight: 600, lineHeight: 1.32, color: STANDARD.text }}>
      {explanation}</div>
  </div>
);

export const VerifiedBadgeView: React.FC = () => (
  <span style={{ fontSize: 22, fontWeight: 800, color: STANDARD.accent,
                 border: `2px solid ${STANDARD.pillOutline}`, borderRadius: 999, padding: "10px 20px" }}>
    &#10003; VERIFIED SOURCE
  </span>
);

export const SourceLineView: React.FC<{ sourceLine: string; promoted?: boolean }> =
  ({ sourceLine, promoted }) => (
    <div style={{ fontSize: promoted ? 38 : 32, fontWeight: promoted ? 700 : 400,
                  color: promoted ? STANDARD.text : STANDARD.muted }}>
      Source: {sourceLine}
    </div>
  );

export const CtaView: React.FC<{ cta: string }> = ({ cta }) => (
  <div style={{ fontSize: 60, fontWeight: 900, color: STANDARD.text, letterSpacing: "-.01em" }}>
    {cta}
  </div>
);
