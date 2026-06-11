import { bundle } from "@remotion/bundler";
import { ensureBrowser, renderMedia, selectComposition } from "@remotion/renderer";
import { readFileSync } from "node:fs";
import path from "node:path";

const propsPath = process.argv[2] ?? "sample-props.json";
const outPath = process.argv[3] ?? "out/sample.mp4";
const inputProps = JSON.parse(readFileSync(propsPath, "utf-8"));

// Download + verify the headless browser before rendering (avoids a race where
// selectComposition runs before the auto-download finishes).
await ensureBrowser();

const serveUrl = await bundle({ entryPoint: path.resolve("src/index.ts") });
const composition = await selectComposition({ serveUrl, id: "Quiz", inputProps });
await renderMedia({ serveUrl, composition, codec: "h264", outputLocation: outPath, inputProps });
console.log("rendered", outPath);
