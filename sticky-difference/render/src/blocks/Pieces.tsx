import React from "react";
import { DIFF } from "../theme";

// Masthead. Brand name is a v1 placeholder ("CURIOUS") -- final name TBD per the spec.
export const BrandHeaderView: React.FC<{ brandHandle?: string }> = ({ brandHandle }) => (
  <div style={{ position: "absolute", top: 60, left: 0, right: 0, textAlign: "center" }}>
    <span style={{ fontSize: 32, fontWeight: 900, letterSpacing: ".30em", color: DIFF.accent }}>CURIOUS</span>
    {brandHandle ? (
      <span style={{ marginLeft: 18, fontSize: 26, fontWeight: 700, color: DIFF.muted }}>{brandHandle}</span>
    ) : null}
  </div>
);

// Rounded, coral-outlined image card. `src` is already resolved (the scene calls staticFile),
// keeping this component pure and testable outside the Remotion bundler.
export const ItemImageView: React.FC<{ src: string; name: string; height?: number }> = ({ src, name, height = 430 }) => (
  <div style={{
    width: "100%", height, borderRadius: 30, background: DIFF.frame,
    border: `4px solid ${DIFF.frameLine}`, boxShadow: "0 24px 60px rgba(0,0,0,.18)",
    overflow: "hidden", display: "flex", alignItems: "center", justifyContent: "center",
  }}>
    <img src={src} alt={name} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
  </div>
);
