import React from "react";
import { AbsoluteFill } from "remotion";
import { STANDARD } from "../theme";
import { FONT_FAMILY } from "../font";
import { PakkaSeal } from "../blocks/StaticBlocks";

const glow = (x: number, y: number, rgb: string, a: number, r: number) =>
  `radial-gradient(circle at ${x}% ${y}%, rgba(${rgb},${a}), transparent ${r}%)`;

// Stacked lockup: "Pakka" over the stamped "GK" chip.
const Lockup: React.FC<{ size: number }> = ({ size }) => (
  <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: size * 0.06 }}>
    <span style={{ fontWeight: 800, fontSize: size, color: STANDARD.text, lineHeight: 0.9, letterSpacing: "-.02em" }}>Pakka</span>
    <span style={{ fontWeight: 800, fontSize: size * 0.9, color: STANDARD.bg, background: STANDARD.accent,
                   padding: `${size * 0.03}px ${size * 0.24}px`, borderRadius: size * 0.16, transform: "rotate(-3deg)",
                   boxShadow: "0 10px 0 rgba(0,0,0,0.22)" }}>GK</span>
  </div>
);

// 1:1 channel avatar / profile mark.
export const BrandAvatar: React.FC = () => (
  <AbsoluteFill style={{ background: STANDARD.bg, fontFamily: FONT_FAMILY, alignItems: "center", justifyContent: "center" }}>
    <AbsoluteFill style={{ background: glow(50, 42, STANDARD.accentRgb, 0.22, 55) + `, ${STANDARD.bgDeep}` }} />
    <div style={{ zIndex: 1 }}><Lockup size={168} /></div>
  </AbsoluteFill>
);

// YouTube banner 2560x1440; keep all content inside the 1546x423 always-visible safe area.
export const BrandBanner: React.FC = () => (
  <AbsoluteFill style={{ background: STANDARD.bg, fontFamily: FONT_FAMILY }}>
    <AbsoluteFill style={{ background:
      glow(28, 30, STANDARD.accentRgb, 0.18, 42) + "," + glow(76, 80, "43,182,168", 0.16, 48) + `, ${STANDARD.bgDeep}` }} />
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
      <div style={{ width: 1546, height: 423, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 60 }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 22 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
            <span style={{ fontWeight: 800, fontSize: 132, color: STANDARD.text, letterSpacing: "-.02em" }}>Pakka</span>
            <span style={{ fontWeight: 800, fontSize: 112, color: STANDARD.bg, background: STANDARD.accent,
                           padding: "2px 28px", borderRadius: 20, transform: "rotate(-3deg)" }}>GK</span>
          </div>
          <div style={{ fontWeight: 600, fontSize: 50, color: STANDARD.text }}>Daily verified GK &middot; SSC &middot; Banking &middot; Railways</div>
          <div style={{ alignSelf: "flex-start", display: "inline-flex", alignItems: "center", gap: 14, fontWeight: 700, fontSize: 34,
                        color: STANDARD.accent, border: `2px solid ${STANDARD.accent}`, borderRadius: 999, padding: "10px 26px" }}>
            &#10003; Every answer sourced
          </div>
        </div>
        <PakkaSeal size={300} rotate={-9} />
      </div>
    </AbsoluteFill>
  </AbsoluteFill>
);
