import React from "react";
import { STANDARD } from "../theme";

export type Option = { letter: "A" | "B" | "C" | "D"; text: string };

export const QuestionView: React.FC<{ question: string }> = ({ question }) => (
  <h1 style={{ fontSize: 74, fontWeight: 900, lineHeight: 1.08, letterSpacing: "-.02em",
               color: STANDARD.text, margin: 0 }}>
    {question}
  </h1>
);

export const OptionsView: React.FC<{ options: Option[]; correctLetter: string; revealed: boolean }> =
  ({ options, correctLetter, revealed }) => (
    <div style={{ display: "flex", flexDirection: "column", gap: 26 }}>
      {options.map((o) => {
        const isCorrect = revealed && o.letter === correctLetter;
        const dim = revealed && o.letter !== correctLetter;
        return (
          <div key={o.letter} data-testid={`opt-${o.letter}`} data-correct={String(isCorrect)}
               style={{ display: "flex", alignItems: "center", gap: 26, padding: "28px 34px",
                        borderRadius: 999, fontSize: 48, fontWeight: 700, opacity: dim ? 0.45 : 1,
                        border: `3px solid ${isCorrect ? STANDARD.accent : STANDARD.pillOutline}`,
                        background: isCorrect ? "rgba(198,242,78,0.15)" : "transparent",
                        color: STANDARD.text }}>
            <span style={{ width: 70, height: 70, borderRadius: 999, fontSize: 38, fontWeight: 900,
                           display: "flex", alignItems: "center", justifyContent: "center",
                           background: isCorrect ? STANDARD.accent : STANDARD.pillOutline,
                           color: isCorrect ? STANDARD.bg : "#fff" }}>{o.letter}</span>
            {o.text}
          </div>
        );
      })}
    </div>
  );
