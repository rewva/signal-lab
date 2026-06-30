import React from "react";
import { STANDARD, difficultyColor, type Difficulty } from "../theme";

export const BrandHeaderView: React.FC<{ dayNumber: number }> = ({ dayNumber }) => (
  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
    <span style={{ fontWeight: 900, fontSize: 34, color: STANDARD.text }}>
      Pakka <span style={{ color: STANDARD.accent }}>GK</span>
    </span>
    <span style={{ fontWeight: 800, fontSize: 26, color: STANDARD.bg,
                   background: STANDARD.accent, padding: "8px 18px", borderRadius: 999 }}>
      DAY {dayNumber}
    </span>
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
  <span style={{ fontSize: 200, fontWeight: 900, lineHeight: 0.8, color: STANDARD.accent }}>
    {dayNumber}
  </span>
);
