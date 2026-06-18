import { bundle } from "@remotion/bundler";
import { ensureBrowser, renderMedia, selectComposition } from "@remotion/renderer";
import { readFileSync, mkdirSync } from "node:fs";
import path from "node:path";

const propsPath = process.argv[2] ?? "sample-props.json";
const outPath = process.argv[3] ?? "out/sample.mp4";
const inputProps = JSON.parse(readFileSync(propsPath, "utf-8"));

await ensureBrowser();
const serveUrl = await bundle({ entryPoint: path.resolve("src/index.ts") });
const composition = await selectComposition({ serveUrl, id: "Difference", inputProps });
mkdirSync(path.dirname(outPath), { recursive: true });
await renderMedia({ serveUrl, composition, codec: "h264", outputLocation: outPath, inputProps });
console.log("rendered", outPath);
