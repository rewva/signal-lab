import React from "react";
import { STANDARD, difficultyColor, type Difficulty } from "../theme";

// Master lockup: "Pakka" (constant) + a stamped vertical chip ("GK", swaps per channel).
export const BrandHeaderView: React.FC<{ dayNumber: number }> = ({ dayNumber }) => (
  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
    <span style={{ display: "inline-flex", alignItems: "center", gap: 12 }}>
      <span style={{ fontWeight: 800, fontSize: 36, color: STANDARD.text, letterSpacing: "-.01em" }}>Pakka</span>
      <span style={{ fontWeight: 800, fontSize: 30, color: STANDARD.bg, background: STANDARD.accent,
                     padding: "3px 14px", borderRadius: 10, transform: "rotate(-3deg)",
                     boxShadow: `0 4px 0 rgba(0,0,0,0.18)` }}>GK</span>
    </span>
    <span style={{ fontWeight: 700, fontSize: 25, color: STANDARD.muted, letterSpacing: ".06em",
                   border: `2px solid ${STANDARD.pillOutline}`, padding: "8px 18px", borderRadius: 999 }}>
      DAY {dayNumber}
    </span>
  </div>
);

// The signature: a rotated rubber-stamp seal that "stamps" each verified answer.
export const PakkaSeal: React.FC<{ size?: number; rotate?: number }> = ({ size = 150, rotate = -9 }) => (
  <div style={{ width: size, height: size, borderRadius: "50%", transform: `rotate(${rotate}deg)`,
                border: `3px solid ${STANDARD.accent}`, color: STANDARD.accent, position: "relative",
                display: "flex", alignItems: "center", justifyContent: "center", opacity: 0.96 }}>
    <div style={{ position: "absolute", inset: 8, borderRadius: "50%", border: `2px solid ${STANDARD.accent}` }} />
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", lineHeight: 1 }}>
      <span style={{ fontSize: size * 0.115, fontWeight: 800, letterSpacing: ".22em", marginBottom: size * 0.04 }}>VERIFIED</span>
      <span style={{ fontSize: size * 0.27, fontWeight: 800, letterSpacing: ".02em" }}>PAKKA</span>
      <span style={{ fontSize: size * 0.115, fontWeight: 800, letterSpacing: ".16em", marginTop: size * 0.04 }}>&#10003; SOURCED</span>
    </div>
  </div>
);

export const DifficultyChipView: React.FC<{ difficulty: Difficulty; examPrefix: string }> =
  ({ difficulty, examPrefix }) => {
    const { label, color } = difficultyColor(difficulty);
    const text = examPrefix ? `${examPrefix} . ${label}` : label;
    return (
      <span style={{ display: "inline-flex", alignItems: "center", gap: 12,
                     fontWeight: 800, fontSize: 26, color: STANDARD.text }}>
        <span style={{ width: 22, height: 22, borderRadius: 999, background: color }} />
        {text}
      </span>
    );
  };

export const CategoryBandView: React.FC<{ category: string }> = ({ category }) => (
  <span style={{ fontWeight: 800, fontSize: 28, letterSpacing: ".08em",
                 textTransform: "uppercase", color: STANDARD.bg, background: STANDARD.accent,
                 padding: "10px 20px", display: "inline-block" }}>
    {category}
  </span>
);

export const DayNumberView: React.FC<{ dayNumber: number }> = ({ dayNumber }) => (
  <span style={{ fontSize: 200, fontWeight: 800, lineHeight: 0.8, color: STANDARD.accent }}>
    {dayNumber}
  </span>
);
