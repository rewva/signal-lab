import { bundle } from "@remotion/bundler";
import { ensureBrowser, renderMedia, selectComposition } from "@remotion/renderer";
import { readFileSync, mkdirSync, rmSync, existsSync } from "node:fs";
import { spawnSync } from "node:child_process";
import path from "node:path";
import { createRequire } from "node:module";
import { synthesize } from "./voiceover.mjs";

const require = createRequire(import.meta.url);
const FFPROBE = require("ffprobe-static").path;

// Narration script (kept in sync with the unit-tested src/vo.ts; inlined here because this
// plain-Node ESM file cannot import the .ts module at runtime). Pure, ~6 lines.
function voLines(props) {
  const correct = (props.options || []).find((o) => o.letter === props.correctLetter);
  const answerText = correct ? correct.text : "";
  return {
    question: props.question,
    reveal: `The correct answer is ${props.correctLetter}. ${answerText}.`,
    why: props.explanation || "",
  };
}

const propsPath = process.argv[2] ?? "sample-props.json";
const outPath = process.argv[3] ?? "out/sample.mp4";
const noVoice = process.argv.includes("--no-voice"); // escape hatch: silent render
const inputProps = JSON.parse(readFileSync(propsPath, "utf-8"));

const probeDur = (f) => {
  const r = spawnSync(FFPROBE, ["-v", "error", "-show_entries", "format=duration",
                                "-of", "csv=p=0", f], { encoding: "utf-8" });
  if (r.status !== 0) throw new Error(`ffprobe failed on ${f}: ${r.stderr || r.error}`);
  return parseFloat(r.stdout.trim());
};

// --- Voice-over pre-step: synthesize -> measure -> inject vo+audio into inputProps ----------
const PUBLIC_DIR = path.resolve("public", "vo");
if (!noVoice) {
  const lines = voLines(inputProps);
  mkdirSync(PUBLIC_DIR, { recursive: true });
  const vo = {}; const audio = {};
  for (const key of ["question", "reveal", "why"]) {
    const text = (lines[key] || "").trim();
    if (!text) { vo[key] = 0; continue; }
    const abs = path.join(PUBLIC_DIR, `${key}.mp3`);
    synthesize(text, abs);
    vo[key] = probeDur(abs);
    audio[key] = `vo/${key}.mp3`;
  }
  inputProps.vo = vo;
  inputProps.audio = audio;
}

// --- Render -------------------------------------------------------------------------------
try {
  await ensureBrowser();
  const serveUrl = await bundle({ entryPoint: path.resolve("src/index.ts") });
  const composition = await selectComposition({ serveUrl, id: "Quiz", inputProps });
  await renderMedia({ serveUrl, composition, codec: "h264", outputLocation: outPath, inputProps });
} finally {
  // Clean the temp VO mp3s even if the render throws, so public/vo never lingers.
  if (!noVoice && existsSync(PUBLIC_DIR)) rmSync(PUBLIC_DIR, { recursive: true, force: true });
}
console.log("rendered", outPath);
