// Brand typeface: Anek (multi-script Indian; carries Hinglish + a future Hindi cut).
// @remotion/google-fonts registers the font and gates rendering until it loads.
import { loadFont } from "@remotion/google-fonts/AnekLatin";

const { fontFamily } = loadFont("normal", {
  weights: ["400", "500", "600", "700", "800"],
});

export const FONT_FAMILY = `${fontFamily}, system-ui, 'Segoe UI', Arial, sans-serif`;
