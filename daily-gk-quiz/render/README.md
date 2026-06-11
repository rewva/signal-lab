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
