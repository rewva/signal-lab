# Sample comparison illustrations

Original vector illustrations used by the Coffin vs Casket sample render. They are
ours (no licensing), recolorable via the Curious palette (see `src/theme.ts`), and
deliberately diagram-style: this pair's whole payoff is the *shape*, so a clean
top-view silhouette reads the difference better than a stock photo.

- `coffin.svg`  - six-sided body-shaped silhouette, wide at the shoulders, coral cross plate
- `casket.svg`  - rectangular four-sided box with a hinged-lid split line and coral side handles

## Rasterizing to the JPGs the template consumes

The template loads `public/comparisons/<name>.jpg` (900x900). To regenerate those
from these sources, render each SVG at 900x900 and save as JPG, e.g. via a headless
browser screenshot at a 900x900 viewport, then drop the result in
`public/comparisons/`. (The committed `coffin.jpg` / `casket.jpg` were produced this
way.)
