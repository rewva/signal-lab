# daily-gk-quiz render

Remotion project: one approved question (JSON props) -> 1080x1920 MP4.

## Develop
npm install
npm test          # vitest (logic + view components)
npm run studio    # live preview (Remotion Studio)

## Render
node render.mjs <props.json> <out.mp4>   # e.g. node render.mjs sample-props.json out/sample.mp4

Props schema: src/props.ts. Templates: standard (80%) + trick (20%, set props.template).
Design tokens: src/theme.ts. Timeline: src/timeline.ts. Output handed to the publisher.

Note: the first render downloads a headless browser; render.mjs calls ensureBrowser() first.

## Voice-over (edge-tts)
The renderer narrates the question, answer, and explanation using edge-tts (free Microsoft Edge
neural TTS). Install once: `pip install edge-tts` (into the daily-gk-quiz venv or system python on PATH).
ffprobe is bundled via the `ffprobe-static` npm package -- no system install. Render silently with
`node render.mjs <props.json> <out.mp4> --no-voice`. Voice/rate via env `TTS_VOICE` / `TTS_RATE`;
`TTS=elevenlabs` is reserved for a future provider.
