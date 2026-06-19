# Mascot images (AI-generated cat)

Drop the AI-generated cat here to switch the template from the procedural SVG cat to the
image cat. **No code changes needed** beyond one flag (see step 3).

## Files required (exactly 3)

Transparent-background PNGs, cat centered, roughly square crop, upright:

| File             | Pose                                                        |
|------------------|------------------------------------------------------------|
| `thinking.png`   | paw to chin / curious (Hook beat)                          |
| `point-left.png` | one paw clearly extended OUT TO THE SIDE (the item beats)  |
| `idea.png`       | excited "aha", ears up, spark above the head (Difference)  |

`point-right` is generated automatically by mirroring `point-left.png` -- do not add a
separate right-pointing file.

## Requirements

- **Transparent background** (the scene background is lavender; a white box would show).
- Same cat in all 3 (consistent fur / belly / ears).
- `point-left.png`: paw extended sideways, not up -- it points across at the picture beside it.
- Reasonable resolution (>= ~600 px tall).

## Switching on

1. Save the 3 PNGs in this folder with the exact names above.
2. In `src/mascot/asset.ts` set `MASCOT_MODE = "image"`.
3. Re-render: `npm run render`. Tune the cat size in `src/scenes/*.tsx` if the new art's
   proportions differ from the placeholder.
