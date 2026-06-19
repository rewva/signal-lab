import React from "react";
import { DIFF } from "../theme";
import { POSES, type PoseKey } from "./poses";

// Pure presentational SVG cat. Geometry is constant except the gesture paw, ear tilt, mouth,
// and the optional idea spark, which come from POSES[pose]. Idle bob / blink are applied by the
// parent scene via a wrapping transform, so this stays hook-free and unit-testable.
export const MascotSvg: React.FC<{ pose: PoseKey; size?: number }> = ({ pose, size = 520 }) => {
  const p = POSES[pose];
  const mouth = p.mouth === "smile" ? "M232 262 q18 14 36 0" : "M236 264 q16 8 28 0";
  const out = DIFF.outline;
  return (
    <svg width={size} height={size * (640 / 540)} viewBox="0 0 540 640" role="img" aria-label={`cat ${pose}`}>
      {/* tail */}
      <path d="M392 470 q120 20 70 -120 q-30 70 -86 84 q-28 14 16 36 z" fill={DIFF.fur} stroke={out} strokeWidth={12} />
      {/* body + belly */}
      <ellipse cx={250} cy={410} rx={140} ry={150} fill={DIFF.fur} stroke={out} strokeWidth={12} />
      <ellipse cx={250} cy={450} rx={80} ry={100} fill={DIFF.belly} stroke={out} strokeWidth={10} />
      {/* ears (tilt for idea) */}
      <g transform={`rotate(${p.earTilt} 250 120)`}>
        <path d="M150 170 l-6 -96 l84 56 z" fill={DIFF.fur} stroke={out} strokeWidth={12} />
        <path d="M350 170 l6 -96 l-84 56 z" fill={DIFF.fur} stroke={out} strokeWidth={12} />
        <path d="M165 150 l-2 -54 l50 34 z" fill={DIFF.innerEar} />
        <path d="M335 150 l2 -54 l-50 34 z" fill={DIFF.innerEar} />
      </g>
      {/* head */}
      <circle cx={250} cy={215} r={128} fill={DIFF.fur} stroke={out} strokeWidth={12} />
      {/* eyes */}
      <circle cx={205} cy={205} r={16} fill={out} />
      <circle cx={295} cy={205} r={16} fill={out} />
      <circle cx={211} cy={199} r={5} fill="#fff" />
      <circle cx={301} cy={199} r={5} fill="#fff" />
      {/* nose + mouth */}
      <path d="M250 248 l-16 -14 l32 0 z" fill={DIFF.nose} stroke={out} strokeWidth={5} />
      <path d={mouth} fill="none" stroke={out} strokeWidth={6} strokeLinecap="round" />
      {/* whiskers (paths, never lines) */}
      <path d="M196 250 L110 236" stroke={out} strokeWidth={6} strokeLinecap="round" />
      <path d="M196 264 L112 272" stroke={out} strokeWidth={6} strokeLinecap="round" />
      <path d="M304 250 L390 236" stroke={out} strokeWidth={6} strokeLinecap="round" />
      <path d="M304 264 L388 272" stroke={out} strokeWidth={6} strokeLinecap="round" />
      {/* feet */}
      <ellipse cx={208} cy={548} rx={40} ry={24} fill={DIFF.fur} stroke={out} strokeWidth={8} />
      <ellipse cx={300} cy={548} rx={40} ry={24} fill={DIFF.fur} stroke={out} strokeWidth={8} />
      {/* short attached pointing arm (point poses only): outline stroke under a fur stroke */}
      {p.arm && (() => {
        const cx = (p.arm.x + p.paw.x) / 2;
        const cy = Math.min(p.arm.y, p.paw.y) - 20;
        const d = `M${p.arm.x} ${p.arm.y} Q${cx} ${cy} ${p.paw.x} ${p.paw.y}`;
        return (
          <g fill="none" strokeLinecap="round">
            <path d={d} stroke={out} strokeWidth={44} />
            <path d={d} stroke={DIFF.fur} strokeWidth={30} />
          </g>
        );
      })()}
      {/* gesture paw (pose-driven) */}
      <ellipse cx={p.paw.x} cy={p.paw.y} rx={32} ry={26} fill={DIFF.fur} stroke={out} strokeWidth={8} />
      {/* idea spark (the only <line> elements) */}
      {p.spark && (
        <g stroke={DIFF.accent} strokeWidth={10} strokeLinecap="round">
          <line x1={250} y1={40} x2={250} y2={10} />
          <line x1={300} y1={55} x2={322} y2={33} />
          <line x1={200} y1={55} x2={178} y2={33} />
        </g>
      )}
    </svg>
  );
};
