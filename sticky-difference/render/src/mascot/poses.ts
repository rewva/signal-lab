export type PoseKey = "thinking" | "point-left" | "point-right" | "idea";

export type Pose = {
  paw: { x: number; y: number };   // gesture-paw tip in the 540x640 viewBox
  arm?: { x: number; y: number };  // shoulder anchor; when set, a short attached arm is drawn to the paw
  earTilt: number;                 // degrees; ears perk for 'idea'
  spark: boolean;                  // show the idea spark over the head
  mouth: "hmm" | "smile";
};

// The point poses extend a short, attached arm toward the item that sits beside the cat in the
// side-by-side item layout, so the gesture has a real on-screen target. thinking/idea keep a
// small paw near the face.
export const POSES: Record<PoseKey, Pose> = {
  thinking:      { paw: { x: 360, y: 318 },                          earTilt: 0,  spark: false, mouth: "hmm" },
  "point-left":  { paw: { x: 44,  y: 294 }, arm: { x: 178, y: 372 }, earTilt: 0,  spark: false, mouth: "smile" },
  "point-right": { paw: { x: 496, y: 294 }, arm: { x: 362, y: 372 }, earTilt: 0,  spark: false, mouth: "smile" },
  idea:          { paw: { x: 360, y: 300 },                          earTilt: -8, spark: true,  mouth: "smile" },
};

export const POSE_KEYS = Object.keys(POSES) as PoseKey[];
