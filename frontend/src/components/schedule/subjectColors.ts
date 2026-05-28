export type SubjectStyle = { bg: string; border: string; text: string };

// Palette used to give each subject (UC) its own colour. The subject name is
// hashed into a stable index so the same subject always gets the same colour.
// Each entry pairs the `light` variant (the week grid) with the `dark` variant
// (the navbar dropdown) so the two can never drift out of index sync.
//
// NOTE: with only 12 hues, distinct subjects will collide on a colour once a
// year has more than a handful of UCs — the hash guarantees stability, not
// uniqueness.
type SubjectPaletteEntry = { light: SubjectStyle; dark: SubjectStyle };

const SUBJECT_PALETTE: SubjectPaletteEntry[] = [
  {
    light: { bg: "bg-blue-100", border: "border-blue-300", text: "text-blue-900" },
    dark: { bg: "bg-blue-500/15", border: "border-blue-400/30", text: "text-blue-300" },
  },
  {
    light: { bg: "bg-emerald-100", border: "border-emerald-300", text: "text-emerald-900" },
    dark: { bg: "bg-emerald-500/15", border: "border-emerald-400/30", text: "text-emerald-300" },
  },
  {
    light: { bg: "bg-amber-100", border: "border-amber-300", text: "text-amber-900" },
    dark: { bg: "bg-amber-500/15", border: "border-amber-400/30", text: "text-amber-300" },
  },
  {
    light: { bg: "bg-purple-100", border: "border-purple-300", text: "text-purple-900" },
    dark: { bg: "bg-purple-500/15", border: "border-purple-400/30", text: "text-purple-300" },
  },
  {
    light: { bg: "bg-pink-100", border: "border-pink-300", text: "text-pink-900" },
    dark: { bg: "bg-pink-500/15", border: "border-pink-400/30", text: "text-pink-300" },
  },
  {
    light: { bg: "bg-cyan-100", border: "border-cyan-300", text: "text-cyan-900" },
    dark: { bg: "bg-cyan-500/15", border: "border-cyan-400/30", text: "text-cyan-300" },
  },
  {
    light: { bg: "bg-rose-100", border: "border-rose-300", text: "text-rose-900" },
    dark: { bg: "bg-rose-500/15", border: "border-rose-400/30", text: "text-rose-300" },
  },
  {
    light: { bg: "bg-teal-100", border: "border-teal-300", text: "text-teal-900" },
    dark: { bg: "bg-teal-500/15", border: "border-teal-400/30", text: "text-teal-300" },
  },
  {
    light: { bg: "bg-indigo-100", border: "border-indigo-300", text: "text-indigo-900" },
    dark: { bg: "bg-indigo-500/15", border: "border-indigo-400/30", text: "text-indigo-300" },
  },
  {
    light: { bg: "bg-lime-100", border: "border-lime-300", text: "text-lime-900" },
    dark: { bg: "bg-lime-500/15", border: "border-lime-400/30", text: "text-lime-300" },
  },
  {
    light: { bg: "bg-orange-100", border: "border-orange-300", text: "text-orange-900" },
    dark: { bg: "bg-orange-500/15", border: "border-orange-400/30", text: "text-orange-300" },
  },
  {
    light: { bg: "bg-fuchsia-100", border: "border-fuchsia-300", text: "text-fuchsia-900" },
    dark: { bg: "bg-fuchsia-500/15", border: "border-fuchsia-400/30", text: "text-fuchsia-300" },
  },
];

export const DEFAULT_SUBJECT_STYLE: SubjectStyle = {
  bg: "bg-slate-100",
  border: "border-slate-300",
  text: "text-slate-900",
};

export const DEFAULT_SUBJECT_STYLE_DARK: SubjectStyle = {
  bg: "bg-slate-500/15",
  border: "border-slate-400/30",
  text: "text-slate-300",
};

function subjectIndex(subject: string): number {
  let hash = 0;
  for (let i = 0; i < subject.length; i++) {
    hash = (hash * 31 + subject.charCodeAt(i)) | 0;
  }
  // `hash` is a signed int32, so a plain `% n` can be negative (and
  // `Math.abs(-2**31)` stays negative) — normalise into [0, n).
  const length = SUBJECT_PALETTE.length;
  return ((hash % length) + length) % length;
}

export function styleForSubject(subject: string | undefined): SubjectStyle {
  if (!subject) return DEFAULT_SUBJECT_STYLE;
  return SUBJECT_PALETTE[subjectIndex(subject)]?.light ?? DEFAULT_SUBJECT_STYLE;
}

export function styleForSubjectDark(subject: string | undefined): SubjectStyle {
  if (!subject) return DEFAULT_SUBJECT_STYLE_DARK;
  return SUBJECT_PALETTE[subjectIndex(subject)]?.dark ?? DEFAULT_SUBJECT_STYLE_DARK;
}
