// Pluggable TTS provider. Default: edge-tts (free, Microsoft Edge neural voice via `python -m edge_tts`).
// Later: ElevenLabs behind TTS=elevenlabs (stubbed). Mirrors the WhichWise content-studio approach.
import { spawnSync } from "node:child_process";

export const VOICE = process.env.TTS_VOICE || "en-IN-NeerjaNeural";
export const RATE = process.env.TTS_RATE || "+6%";

function edgeTts(text, outPath) {
  const r = spawnSync("python", ["-m", "edge_tts", "--voice", VOICE, "--rate", RATE,
                                 "--text", text, "--write-media", outPath], { encoding: "utf-8" });
  if (r.status !== 0) {
    throw new Error(`edge-tts failed (is it installed? pip install edge-tts):\n${r.stderr || r.stdout || r.error}`);
  }
}

// Synthesize `text` to an mp3 at `outPath`. Selected by env TTS (default edge-tts).
export function synthesize(text, outPath) {
  const provider = (process.env.TTS || "edge-tts").toLowerCase();
  if (provider === "elevenlabs") {
    throw new Error("ElevenLabs provider not implemented yet (seam only); unset TTS to use edge-tts");
  }
  edgeTts(text, outPath);
}
