// Per-UC colours for the schedule grid and the navbar UC dropdown.
//
// Colours are assigned by *index* into a fixed palette (so the same ordered UC
// list always produces the same colours, with no collisions until there are
// more UCs than palette entries) rather than by hashing the name. Each UC gets
// ONE hue; the session *type* then picks a tone along a light→strong ramp, so
// T, TP, P and PL of the same UC are all distinct shades of that hue.
//
// The first 12 hues are colourblind-safe (Okabe-Ito + Paul Tol); a year with
// up to 12 UCs is therefore fully CVD-friendly. Beyond that the palette is
// extended with golden-angle-spread hues to reach PALETTE_SIZE — those keep
// adjacent UCs well separated but can no longer guarantee CVD-distinctness
// (no 30-colour palette can).

export type SubjectStyle = { background: string; border: string; text: string };

type RGB = [number, number, number];

/** Maps each UC name to its assigned base hue (as RGB). */
export type SubjectPalette = Map<string, RGB>;

/** How many distinct hues the palette provides. */
export const PALETTE_SIZE = 30;

/** Neutral ring marking the event currently open in the edit drawer (#11). */
export const SUBJECT_SELECTION_RING = "#1f2937"; // slate-800

export const DEFAULT_SUBJECT_STYLE: SubjectStyle = {
  background: "#f1f5f9", // slate-100
  border: "#cbd5e1", // slate-300
  text: "#0f172a", // slate-900
};

const WHITE: RGB = [255, 255, 255];
const BLACK: RGB = [0, 0, 0];

// The 12 leading colourblind-safe hues (Okabe-Ito + Paul Tol).
const CURATED_HUES = [
  "#0072B2", // blue
  "#E69F00", // orange
  "#009E73", // green
  "#CC79A7", // reddish purple
  "#56B4E9", // sky blue
  "#D55E00", // vermillion
  "#117733", // dark green
  "#882255", // wine
  "#44AA99", // teal
  "#999933", // olive
  "#AA4499", // purple
  "#332288", // indigo
] as const;

// Tone = how far the hue is mixed toward white (higher → lighter). The ramp
// runs theoretical (lightest) to practical-lab (strongest); unlisted types use
// the middle tone, and the navbar dropdown chip uses CHIP_TONE.
// White-mix per type. The light end is capped (T at 0.74, not higher) because
// past ~0.75 the hue washes out and different UCs' light tones become hard to
// tell apart; step prominence comes from spreading the mid/dark range instead.
const TYPE_TONE: Record<string, number> = {
  T: 0.74,
  TP: 0.56,
  TC: 0.48,
  OT: 0.4,
  P: 0.32,
  PL: 0.2,
};
const DEFAULT_TONE = 0.56;
const CHIP_TONE = 0.46;

function hexToRgb(hex: string): RGB {
  const value = hex.replace("#", "");
  return [
    parseInt(value.slice(0, 2), 16),
    parseInt(value.slice(2, 4), 16),
    parseInt(value.slice(4, 6), 16),
  ];
}

function rgbToHex([r, g, b]: RGB): string {
  return `#${[r, g, b].map((c) => c.toString(16).padStart(2, "0")).join("")}`;
}

/** Linear blend from `a` to `b`; `t` in [0,1], 0 = a, 1 = b. */
function mix(a: RGB, b: RGB, t: number): RGB {
  return [
    Math.round(a[0] + (b[0] - a[0]) * t),
    Math.round(a[1] + (b[1] - a[1]) * t),
    Math.round(a[2] + (b[2] - a[2]) * t),
  ];
}

function hslToRgb(h: number, s: number, l: number): RGB {
  const c = (1 - Math.abs(2 * l - 1)) * s;
  const x = c * (1 - Math.abs(((h / 60) % 2) - 1));
  const m = l - c / 2;
  const [r, g, b] =
    h < 60
      ? [c, x, 0]
      : h < 120
        ? [x, c, 0]
        : h < 180
          ? [0, c, x]
          : h < 240
            ? [0, x, c]
            : h < 300
              ? [x, 0, c]
              : [c, 0, x];
  return [Math.round((r + m) * 255), Math.round((g + m) * 255), Math.round((b + m) * 255)];
}

/**
 * The full ordered hue list: the curated colourblind-safe hues first, then
 * evenly spaced fills (with cycled lightness for a second axis of distinction)
 * to reach PALETTE_SIZE.
 */
function buildBaseHues(): RGB[] {
  const hues = CURATED_HUES.map(hexToRgb);
  const fillCount = PALETTE_SIZE - hues.length;
  const step = 360 / fillCount;
  for (let i = 0; i < fillCount; i += 1) {
    // Offset start so fills interleave with, rather than overlap, the curated
    // hues; cycle lightness so neighbours differ in brightness too.
    const angle = (13 + i * step) % 360;
    const lightness = [0.5, 0.58, 0.43][i % 3]!;
    // Fairly saturated so the hue survives being mixed toward white in the
    // lighter tones (otherwise distinct UCs' T cells look alike).
    hues.push(hslToRgb(angle, 0.72, lightness));
  }
  return hues;
}

const BASE_HUES = buildBaseHues();

/**
 * Assigns each UC name a base hue by its position in `orderedUcNames`. Pass the
 * year's full UC list (e.g. `filters.ucOptions`) so colours stay stable across
 * filter changes. UCs beyond PALETTE_SIZE cycle back to the start.
 */
export function createSubjectPalette(orderedUcNames: string[]): SubjectPalette {
  const palette: SubjectPalette = new Map();
  orderedUcNames.forEach((name, index) => {
    if (!palette.has(name)) {
      palette.set(name, BASE_HUES[index % BASE_HUES.length]!);
    }
  });
  return palette;
}

/** Builds the three colours for a base hue at a given tone (white-mix amount). */
function toneStyle(base: RGB, whiteAmount: number): SubjectStyle {
  return {
    background: rgbToHex(mix(base, WHITE, whiteAmount)),
    // Border is one notch stronger than the fill so the cell keeps an outline.
    border: rgbToHex(mix(base, WHITE, Math.max(whiteAmount - 0.3, 0))),
    // Dark, hue-tinted text; every tone is lighter than the base, so it reads.
    text: rgbToHex(mix(base, BLACK, 0.6)),
  };
}

/**
 * The colours for a UC. `type` picks the tone along the T→PL ramp; omit it for
 * the navbar dropdown chip. Falls back to the neutral default when the palette
 * has no entry for the UC.
 */
export function styleForSubject(
  palette: SubjectPalette | undefined,
  subject: string | undefined,
  type?: string,
): SubjectStyle {
  if (!palette || !subject) return DEFAULT_SUBJECT_STYLE;
  const base = palette.get(subject);
  if (!base) return DEFAULT_SUBJECT_STYLE;
  if (type === undefined) return toneStyle(base, CHIP_TONE);
  return toneStyle(base, TYPE_TONE[type.toUpperCase()] ?? DEFAULT_TONE);
}
