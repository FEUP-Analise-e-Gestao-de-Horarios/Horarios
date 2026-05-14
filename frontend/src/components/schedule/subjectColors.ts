export type SubjectStyle = { bg: string; border: string; text: string };

// Palette used to give each subject (UC) its own colour. The subject name is
// hashed into a stable index so the same subject always gets the same colour.
// `SUBJECT_PALETTE` is for light surfaces (the week grid); `SUBJECT_PALETTE_DARK`
// holds the matching hues tuned for dark surfaces (the navbar dropdown).
const SUBJECT_PALETTE: SubjectStyle[] = [
  { bg: "bg-blue-100", border: "border-blue-300", text: "text-blue-900" },
  { bg: "bg-emerald-100", border: "border-emerald-300", text: "text-emerald-900" },
  { bg: "bg-amber-100", border: "border-amber-300", text: "text-amber-900" },
  { bg: "bg-purple-100", border: "border-purple-300", text: "text-purple-900" },
  { bg: "bg-pink-100", border: "border-pink-300", text: "text-pink-900" },
  { bg: "bg-cyan-100", border: "border-cyan-300", text: "text-cyan-900" },
  { bg: "bg-rose-100", border: "border-rose-300", text: "text-rose-900" },
  { bg: "bg-teal-100", border: "border-teal-300", text: "text-teal-900" },
  { bg: "bg-indigo-100", border: "border-indigo-300", text: "text-indigo-900" },
  { bg: "bg-lime-100", border: "border-lime-300", text: "text-lime-900" },
  { bg: "bg-orange-100", border: "border-orange-300", text: "text-orange-900" },
  { bg: "bg-fuchsia-100", border: "border-fuchsia-300", text: "text-fuchsia-900" },
];

const SUBJECT_PALETTE_DARK: SubjectStyle[] = [
  { bg: "bg-blue-500/15", border: "border-blue-400/30", text: "text-blue-300" },
  { bg: "bg-emerald-500/15", border: "border-emerald-400/30", text: "text-emerald-300" },
  { bg: "bg-amber-500/15", border: "border-amber-400/30", text: "text-amber-300" },
  { bg: "bg-purple-500/15", border: "border-purple-400/30", text: "text-purple-300" },
  { bg: "bg-pink-500/15", border: "border-pink-400/30", text: "text-pink-300" },
  { bg: "bg-cyan-500/15", border: "border-cyan-400/30", text: "text-cyan-300" },
  { bg: "bg-rose-500/15", border: "border-rose-400/30", text: "text-rose-300" },
  { bg: "bg-teal-500/15", border: "border-teal-400/30", text: "text-teal-300" },
  { bg: "bg-indigo-500/15", border: "border-indigo-400/30", text: "text-indigo-300" },
  { bg: "bg-lime-500/15", border: "border-lime-400/30", text: "text-lime-300" },
  { bg: "bg-orange-500/15", border: "border-orange-400/30", text: "text-orange-300" },
  { bg: "bg-fuchsia-500/15", border: "border-fuchsia-400/30", text: "text-fuchsia-300" },
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
  return Math.abs(hash) % SUBJECT_PALETTE.length;
}

export function styleForSubject(subject: string | undefined): SubjectStyle {
  if (!subject) return DEFAULT_SUBJECT_STYLE;
  return SUBJECT_PALETTE[subjectIndex(subject)] ?? DEFAULT_SUBJECT_STYLE;
}

export function styleForSubjectDark(subject: string | undefined): SubjectStyle {
  if (!subject) return DEFAULT_SUBJECT_STYLE_DARK;
  return SUBJECT_PALETTE_DARK[subjectIndex(subject)] ?? DEFAULT_SUBJECT_STYLE_DARK;
}
