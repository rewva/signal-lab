export type PoseKey = "thinking" | "point-left" | "point-right" | "idea";

export type Pose = {
  paw: { x: number; y: number }; // gesture-paw tip in the 540x640 viewBox
  earTilt: number;               // degrees; ears perk for 'idea'
  spark: boolean;                // show the idea spark over the head
  mouth: "hmm" | "smile";
};

export const POSES: Record<PoseKey, Pose> = {
  thinking:      { paw: { x: 360, y: 318 }, earTilt: 0,  spark: false, mouth: "hmm" },
  "point-left":  { paw: { x: 120, y: 360 }, earTilt: 0,  spark: false, mouth: "smile" },
  "point-right": { paw: { x: 420, y: 360 }, earTilt: 0,  spark: false, mouth: "smile" },
  idea:          { paw: { x: 360, y: 300 }, earTilt: -8, spark: true,  mouth: "smile" },
};

export const POSE_KEYS = Object.keys(POSES) as PoseKey[];
