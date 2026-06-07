import type { Weekday } from "@/types/project/weekday";

/**
 * Canonical weekday order for the schedule feature. Every component that needs
 * a weekday list or label should derive it from here so the representations
 * can't drift apart.
 */
export const WEEKDAYS = [
  "monday",
  "tuesday",
  "wednesday",
  "thursday",
  "friday",
  "saturday",
] as const satisfies readonly Weekday[];

/** Three-letter labels — week grid day headers. */
export const WEEKDAY_LABELS_SHORT: Record<Weekday, string> = {
  monday: "Seg",
  tuesday: "Ter",
  wednesday: "Qua",
  thursday: "Qui",
  friday: "Sex",
  saturday: "Sáb",
};

/** Full pt-PT labels — filter dropdowns and the edit drawer. */
export const WEEKDAY_LABELS_LONG: Record<Weekday, string> = {
  monday: "Segunda-feira",
  tuesday: "Terça-feira",
  wednesday: "Quarta-feira",
  thursday: "Quinta-feira",
  friday: "Sexta-feira",
  saturday: "Sábado",
};

/** Upper-case labels — week grid column headers. */
export const WEEKDAY_LABELS_UPPER: Record<Weekday, string> = {
  monday: "SEGUNDA",
  tuesday: "TERÇA",
  wednesday: "QUARTA",
  thursday: "QUINTA",
  friday: "SEXTA",
  saturday: "SÁBADO",
};
