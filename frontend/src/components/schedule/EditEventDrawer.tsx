import { useEffect, useMemo, useReducer, useRef, useState } from "react";
import type { ConflictRecord } from "@/types/project/conflicts";
import type { Weekday } from "@/types/project/weekday";
import type { WeekGridEvent } from "@/components/schedule/WeekGrid";
import { hhmmToMinutes, minutesToTime } from "@/utils/time";
import { WEEKDAYS, WEEKDAY_LABELS_LONG } from "@/utils/weekdays";
import DrawerMultiSelect from "./DrawerMultiSelect";
import { useDismissable } from "./useDismissable";

function normalizeText(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
}

function getConflictDay(weekday: Weekday): string {
  return WEEKDAY_LABELS_LONG[weekday].split("-")[0] ?? "";
}

function conflictMatchesEvent(conflict: ConflictRecord, event: WeekGridEvent): boolean {
  if (conflict.event_ids.includes(event.id)) return true;

  const eventDay = normalizeText(getConflictDay(event.weekday));
  const conflictDay = normalizeText(conflict.day);
  if (eventDay !== conflictDay) return false;

  const eventTime = minutesToTime(hhmmToMinutes(event.startTime));
  if (conflict.time !== eventTime) return false;

  const eventTurma = normalizeText(event.turma ?? event.classCodes?.[0] ?? "");
  if (eventTurma && normalizeText(conflict.turma) !== eventTurma) return false;

  const conflictText = normalizeText(conflict.event_names.join(" "));
  const eventTokens = [event.title, event.uc, event.professor, event.sala, event.turma]
    .filter((token): token is string => Boolean(token))
    .map(normalizeText);

  if (eventTokens.length === 0) return true;
  return eventTokens.some((token) => conflictText.includes(token));
}
type TeacherOption = {
  id: string;
  label: string;
};

type RoomOption = {
  id: string;
  label: string;
  type: string;
};

interface EditEventDrawerProps {
  open: boolean;
  onClose: () => void;
  collapsed: boolean;
  onCollapsedChange: (collapsed: boolean) => void;
  conflicts: ConflictRecord[];
  ucOptions: string[];
  turmaOptions: string[];
  teacherOptions: TeacherOption[];
  roomOptions: RoomOption[];
  preferredUc?: string;
  event?: WeekGridEvent | null;
}

const MIN_TIME_MINUTES = 8 * 60;
const MAX_TIME_MINUTES = 19 * 60 + 30;
// Smallest gap between start and end. Mirrors the 30-minute slot grid the
// schedule is drawn against; an event can't be shorter than one slot.
const MIN_DURATION_MINUTES = 30;

function clampTimeMinutes(totalMinutes: number): number {
  return Math.max(MIN_TIME_MINUTES, Math.min(MAX_TIME_MINUTES, totalMinutes));
}

function timeToMinutes(time: string): number | null {
  const [hours, minutes] = time.split(":").map(Number);
  if (hours === undefined || minutes === undefined || Number.isNaN(hours) || Number.isNaN(minutes))
    return null;
  return hours * 60 + minutes;
}

function shiftTimeByMinutes(time: string, deltaMinutes: number): string {
  const totalMinutes = timeToMinutes(time);
  if (totalMinutes === null) return time;
  return minutesToTime(clampTimeMinutes(totalMinutes + deltaMinutes));
}

function normalizeTimeValue(value: string, fallback: string): string {
  const cleaned = value.trim();
  const match = cleaned.match(/^(\d{1,2}):?(\d{2})$/);
  if (!match) return fallback;

  const hours = Number(match[1]);
  const minutes = Number(match[2]);
  if (Number.isNaN(hours) || Number.isNaN(minutes)) return fallback;
  if (minutes < 0 || minutes > 59) return fallback;

  const totalMinutes = clampTimeMinutes(hours * 60 + minutes);
  return minutesToTime(totalMinutes);
}

/**
 * Adjusts `state` so `endTime` is at least one slot after `startTime`. Both
 * inputs are independently editable, but the form-state invariant is that
 * the start always precedes the end by at least one slot. The pinned field
 * stays put; the other is nudged into range.
 */
function enforceTimeOrdering(state: FormState, pinned: TimeField): FormState {
  const startMin = timeToMinutes(state.startTime);
  const endMin = timeToMinutes(state.endTime);
  if (startMin === null || endMin === null) return state;
  if (endMin - startMin >= MIN_DURATION_MINUTES) return state;

  if (pinned === "startTime") {
    const nextEnd = clampTimeMinutes(startMin + MIN_DURATION_MINUTES);
    return { ...state, endTime: minutesToTime(nextEnd) };
  }
  const nextStart = clampTimeMinutes(endMin - MIN_DURATION_MINUTES);
  return { ...state, startTime: minutesToTime(nextStart) };
}

function toggleSelection(current: string[], itemId: string): string[] {
  return current.includes(itemId)
    ? current.filter((selectedId) => selectedId !== itemId)
    : [...current, itemId];
}

type FormState = {
  selectedUcOverride: string;
  selectedDocenteOverride: string[];
  selectedSalaOverride: string[];
  selectedTurmasOverride: string[];
  selectedWeekday: Weekday;
  startTime: string;
  endTime: string;
};

type TimeField = "startTime" | "endTime";

type FormAction =
  | { type: "reset"; event: WeekGridEvent | null | undefined }
  | { type: "setUc"; value: string }
  | { type: "setWeekday"; value: Weekday }
  | { type: "setTime"; field: TimeField; value: string }
  | { type: "shiftTime"; field: TimeField; delta: number }
  | { type: "normalizeTime"; field: TimeField; raw: string }
  | { type: "toggleDocente"; id: string }
  | { type: "toggleSala"; id: string }
  | { type: "setTurmas"; value: string[] };

function getInitialFormState(event?: WeekGridEvent | null): FormState {
  if (event) {
    return {
      selectedUcOverride: event.uc ?? "",
      selectedDocenteOverride: event.teacherIds ?? [],
      selectedSalaOverride: event.roomIds ?? [],
      selectedTurmasOverride: event.classCodes ?? (event.turma ? [event.turma] : []),
      selectedWeekday: event.weekday,
      startTime: minutesToTime(hhmmToMinutes(event.startTime)),
      endTime: minutesToTime(hhmmToMinutes(event.startTime) + event.duration * 30),
    };
  }
  return {
    selectedUcOverride: "",
    selectedDocenteOverride: [],
    selectedSalaOverride: [],
    selectedTurmasOverride: [],
    selectedWeekday: "monday",
    startTime: "10:30",
    endTime: "12:30",
  };
}

function formReducer(state: FormState, action: FormAction): FormState {
  switch (action.type) {
    case "reset":
      return getInitialFormState(action.event);
    case "setUc":
      return { ...state, selectedUcOverride: action.value };
    case "setWeekday":
      return { ...state, selectedWeekday: action.value };
    case "setTime":
      // Free-text edits skip the ordering invariant — the user is mid-type;
      // ordering is enforced on blur via `normalizeTime`.
      return { ...state, [action.field]: action.value };
    case "shiftTime":
      return enforceTimeOrdering(
        { ...state, [action.field]: shiftTimeByMinutes(state[action.field], action.delta) },
        action.field,
      );
    case "normalizeTime":
      return enforceTimeOrdering(
        { ...state, [action.field]: normalizeTimeValue(action.raw, state[action.field]) },
        action.field,
      );
    case "toggleDocente":
      return {
        ...state,
        selectedDocenteOverride: toggleSelection(state.selectedDocenteOverride, action.id),
      };
    case "toggleSala":
      return {
        ...state,
        selectedSalaOverride: toggleSelection(state.selectedSalaOverride, action.id),
      };
    case "setTurmas":
      return { ...state, selectedTurmasOverride: action.value };
  }
}

export default function EditEventDrawer({
  open,
  onClose,
  collapsed,
  onCollapsedChange,
  conflicts,
  ucOptions,
  turmaOptions,
  teacherOptions,
  roomOptions,
  preferredUc,
  event,
}: EditEventDrawerProps) {
  const [formState, dispatch] = useReducer(formReducer, event, getInitialFormState);
  const {
    selectedUcOverride,
    selectedDocenteOverride,
    selectedSalaOverride,
    selectedTurmasOverride,
    selectedWeekday,
    startTime,
    endTime,
  } = formState;

  // The form is seeded lazily from `event` on mount; re-seed whenever the
  // parent swaps in a different event (or any of its time-shape fields
  // change) so the inputs don't get stuck displaying the previous event.
  const lastEventRef = useRef(event);
  useEffect(() => {
    if (lastEventRef.current !== event) {
      lastEventRef.current = event;
      dispatch({ type: "reset", event });
    }
  }, [event]);

  const [docentesSearch, setDocentesSearch] = useState("");
  const [salasSearch, setSalasSearch] = useState("");
  const [turmasSearch, setTurmasSearch] = useState("");
  const eventConflicts = useMemo(
    () => (event ? conflicts.filter((conflict) => conflictMatchesEvent(conflict, event)) : []),
    [conflicts, event],
  );
  const [openDropdown, setOpenDropdown] = useState<"docentes" | "salas" | "turmas" | null>(null);
  const dropdownAreaRef = useRef<HTMLDivElement>(null);
  const asideRef = useRef<HTMLElement>(null);

  // A click outside the inner dropdown area collapses any open dropdown; a
  // click outside the whole drawer (or Escape) closes it — except clicks on a
  // grid event or the navbar, which open/retarget the drawer instead.
  useDismissable(dropdownAreaRef, () => setOpenDropdown(null));
  useDismissable(asideRef, onClose, {
    escape: true,
    ignoreSelector: "[data-schedule-event],[data-schedule-navbar]",
  });

  const selectedUc = useMemo(() => {
    if (selectedUcOverride && ucOptions.includes(selectedUcOverride)) return selectedUcOverride;
    if (preferredUc && ucOptions.includes(preferredUc)) return preferredUc;
    return ucOptions[0] ?? "";
  }, [preferredUc, selectedUcOverride, ucOptions]);

  const preferredRoomTypes = useMemo(() => {
    if (!event?.roomIds || event.roomIds.length === 0) return new Set<string>();
    const roomTypes = roomOptions
      .filter((room) => event.roomIds?.includes(room.id))
      .map((room) => room.type)
      .filter((type) => type.length > 0);
    return new Set(roomTypes);
  }, [event, roomOptions]);

  const selectedEventTeacherIds = useMemo(
    () => new Set(event?.teacherIds ?? []),
    [event?.teacherIds],
  );

  const selectedClassDocentes = useMemo(
    () => teacherOptions.filter((docente) => selectedEventTeacherIds.has(docente.id)),
    [selectedEventTeacherIds, teacherOptions],
  );

  // Everyone not already shown under "the event's own teachers".
  const otherDocentes = useMemo(
    () => teacherOptions.filter((docente) => !selectedEventTeacherIds.has(docente.id)),
    [selectedEventTeacherIds, teacherOptions],
  );

  const preferredSalas = useMemo(
    () => roomOptions.filter((room) => preferredRoomTypes.has(room.type)),
    [preferredRoomTypes, roomOptions],
  );

  const otherSalas = useMemo(
    () => roomOptions.filter((room) => !preferredRoomTypes.has(room.type)),
    [preferredRoomTypes, roomOptions],
  );

  const filteredSelectedClassDocentes = useMemo(() => {
    const query = docentesSearch.toLowerCase().trim();
    if (!query) return selectedClassDocentes;
    return selectedClassDocentes.filter((docente) => docente.label.toLowerCase().includes(query));
  }, [docentesSearch, selectedClassDocentes]);

  const filteredOtherDocentes = useMemo(() => {
    const query = docentesSearch.toLowerCase().trim();
    if (!query) return otherDocentes;
    return otherDocentes.filter((docente) => docente.label.toLowerCase().includes(query));
  }, [docentesSearch, otherDocentes]);

  const filteredPreferredSalas = useMemo(() => {
    const query = salasSearch.toLowerCase().trim();
    if (!query) return preferredSalas;
    return preferredSalas.filter((room) => `${room.id} ${room.type}`.toLowerCase().includes(query));
  }, [preferredSalas, salasSearch]);

  const filteredOtherSalas = useMemo(() => {
    const query = salasSearch.toLowerCase().trim();
    if (!query) return otherSalas;
    return otherSalas.filter((room) => `${room.id} ${room.type}`.toLowerCase().includes(query));
  }, [otherSalas, salasSearch]);

  const filteredTurmas = useMemo(() => {
    const query = turmasSearch.toLowerCase().trim();
    if (!query) return turmaOptions;
    return turmaOptions.filter((turma) => turma.toLowerCase().includes(query));
  }, [turmaOptions, turmasSearch]);

  // The "effective" selections are simply the user's overrides, narrowed to
  // ids that still exist in the option list. Previously they fell back to a
  // default (the first ordered docente/sala, or every visible turma) when the
  // override was empty, which made it impossible to deselect down to nothing
  // and caused the turma selection to flip to "all visible" the moment the
  // user typed in the search box.
  const effectiveSelectedDocente = useMemo(
    () => selectedDocenteOverride.filter((id) => teacherOptions.some((d) => d.id === id)),
    [selectedDocenteOverride, teacherOptions],
  );

  const effectiveSelectedSala = useMemo(
    () => selectedSalaOverride.filter((id) => roomOptions.some((room) => room.id === id)),
    [roomOptions, selectedSalaOverride],
  );

  const selectedDocenteLabel = useMemo(() => {
    if (effectiveSelectedDocente.length === 0) return "Selecionar...";
    const labels = effectiveSelectedDocente
      .map((id) => teacherOptions.find((docente) => docente.id === id)?.label)
      .filter((label): label is string => Boolean(label));
    const first = labels[0];
    if (!first) return "Selecionar...";
    return labels.length === 1 ? first : `${first} (+${labels.length - 1})`;
  }, [effectiveSelectedDocente, teacherOptions]);

  const selectedSalaLabel = useMemo(() => {
    if (effectiveSelectedSala.length === 0) return "Selecionar...";
    const labels = effectiveSelectedSala
      .map((id) => roomOptions.find((room) => room.id === id))
      .filter((room): room is RoomOption => Boolean(room));
    if (labels.length === 0) return "Selecionar...";
    const first = labels[0];
    if (!first) return "Selecionar...";
    const firstLabel = first.label;
    return labels.length === 1 ? firstLabel : `${firstLabel} (+${labels.length - 1})`;
  }, [effectiveSelectedSala, roomOptions]);

  // Validate against the full turma list, not the search-filtered one — the
  // search box should only narrow what's *displayed* in the dropdown, never
  // drop selections the user already made.
  const effectiveSelectedTurmas = useMemo(
    () => selectedTurmasOverride.filter((id) => turmaOptions.includes(id)),
    [selectedTurmasOverride, turmaOptions],
  );

  if (!open) return null;

  return (
    <aside
      ref={asideRef}
      // The drawer is intentionally non-modal: the grid behind it stays
      // interactive so the user can click another event to retarget the
      // drawer. `<aside>`'s implicit role="complementary" carries the
      // "non-modal side panel" meaning more accurately than role="dialog".
      aria-labelledby="edit-event-drawer-title"
      className={[
        "fixed left-0 top-[15vh] h-[70vh] w-[min(92vw,420px)] z-40 transition-transform duration-200",
        collapsed ? "-translate-x-full" : "translate-x-0",
      ].join(" ")}
    >
      <button
        type="button"
        onClick={() => onCollapsedChange(!collapsed)}
        onMouseEnter={() => {
          if (collapsed) onCollapsedChange(false);
        }}
        aria-label={collapsed ? "Expandir painel de edição" : "Colapsar painel de edição"}
        className="absolute left-full top-1/2 -translate-y-1/2 flex h-24 w-6 items-center justify-center rounded-r-md border border-l-0 border-white/15 bg-[#1d2128] text-lg leading-none text-white/70 shadow-[4px_0_12px_rgba(0,0,0,0.35)] hover:text-white"
      >
        {collapsed ? "›" : "‹"}
      </button>

      <div className="flex h-full flex-col overflow-hidden rounded-r-lg border border-l-0 border-white/15 bg-[#1d2128] text-white shadow-[6px_0_24px_rgba(0,0,0,0.45)]">
        <div className="bg-[#1d2128] border-b border-white/10 px-5 py-4 flex items-center justify-between shrink-0">
          <h2 id="edit-event-drawer-title" className="text-lg font-semibold">
            Editar Evento
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="text-white/80 hover:text-white border border-white/20 rounded px-2 py-1 text-sm"
          >
            Fechar
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
          <label className="block text-sm">
            <span className="mb-1.5 block text-white/90">UC Selecionada</span>
            <select
              value={selectedUc}
              onChange={(event) => dispatch({ type: "setUc", value: event.target.value })}
              className="w-full bg-[#2a303a] border border-white/20 rounded px-2.5 py-2"
            >
              {ucOptions.map((uc) => (
                <option key={uc} value={uc}>
                  {uc}
                </option>
              ))}
            </select>
          </label>

          <div className="flex items-end gap-2">
            {/* `<label>` would wrap three interactive controls (the `-`/`+`
                buttons and the `<input>`); native label-click would focus the
                first button instead of the input. Use a `<span>` + an explicit
                `aria-labelledby` on the input so the association is correct. */}
            <div className="block text-sm flex-1 min-w-0">
              <span id="edit-event-start-time-label" className="mb-1.5 block text-white/90">
                Hora Início
              </span>
              <div className="flex items-center gap-1">
                <button
                  type="button"
                  onClick={() => dispatch({ type: "shiftTime", field: "startTime", delta: -30 })}
                  className="h-8 w-8 rounded border border-white/20 bg-[#2a303a] text-white/80 hover:text-white text-sm"
                  aria-label="Diminuir hora de início em 30 minutos"
                >
                  -
                </button>
                <input
                  type="text"
                  inputMode="numeric"
                  placeholder="HH:MM"
                  value={startTime}
                  aria-labelledby="edit-event-start-time-label"
                  onChange={(event) =>
                    dispatch({ type: "setTime", field: "startTime", value: event.target.value })
                  }
                  onBlur={(event) =>
                    dispatch({ type: "normalizeTime", field: "startTime", raw: event.target.value })
                  }
                  className="w-14 bg-[#2a303a] border border-white/20 rounded px-1.5 py-1.5 text-white text-center text-sm"
                />
                <button
                  type="button"
                  onClick={() => dispatch({ type: "shiftTime", field: "startTime", delta: 30 })}
                  className="h-8 w-8 rounded border border-white/20 bg-[#2a303a] text-white/80 hover:text-white text-sm"
                  aria-label="Aumentar hora de início em 30 minutos"
                >
                  +
                </button>
              </div>
            </div>
            <div className="block text-sm flex-1 min-w-0">
              <span id="edit-event-end-time-label" className="mb-1.5 block text-white/90">
                Hora Fim
              </span>
              <div className="flex items-center gap-1">
                <button
                  type="button"
                  onClick={() => dispatch({ type: "shiftTime", field: "endTime", delta: -30 })}
                  className="h-8 w-8 rounded border border-white/20 bg-[#2a303a] text-white/80 hover:text-white text-sm"
                  aria-label="Diminuir hora de fim em 30 minutos"
                >
                  -
                </button>
                <input
                  type="text"
                  inputMode="numeric"
                  placeholder="HH:MM"
                  value={endTime}
                  aria-labelledby="edit-event-end-time-label"
                  onChange={(event) =>
                    dispatch({ type: "setTime", field: "endTime", value: event.target.value })
                  }
                  onBlur={(event) =>
                    dispatch({ type: "normalizeTime", field: "endTime", raw: event.target.value })
                  }
                  className="w-14 bg-[#2a303a] border border-white/20 rounded px-1.5 py-1.5 text-white text-center text-sm"
                />
                <button
                  type="button"
                  onClick={() => dispatch({ type: "shiftTime", field: "endTime", delta: 30 })}
                  className="h-8 w-8 rounded border border-white/20 bg-[#2a303a] text-white/80 hover:text-white text-sm"
                  aria-label="Aumentar hora de fim em 30 minutos"
                >
                  +
                </button>
              </div>
            </div>
            <div className="border-l border-white/20 h-10 ml-1 mr-0.5" />
            <label className="block text-sm flex-1 min-w-0">
              <span className="mb-1.5 block text-white/90">Dia</span>
              <select
                value={selectedWeekday}
                onChange={(event) =>
                  dispatch({ type: "setWeekday", value: event.target.value as Weekday })
                }
                className="w-full bg-[#2a303a] border border-white/20 rounded px-2 py-1.5 text-sm"
              >
                {WEEKDAYS.map((weekday) => (
                  <option key={weekday} value={weekday}>
                    {WEEKDAY_LABELS_LONG[weekday]}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="space-y-4" ref={dropdownAreaRef}>
            <DrawerMultiSelect
              label="Docentes"
              triggerLabel={selectedDocenteLabel}
              open={openDropdown === "docentes"}
              onToggle={() => setOpenDropdown((prev) => (prev === "docentes" ? null : "docentes"))}
              search={docentesSearch}
              onSearchChange={setDocentesSearch}
              listMaxHeightClass="max-h-52"
              groups={[
                {
                  heading: "Docentes da turma selecionada",
                  options: filteredSelectedClassDocentes,
                },
                { heading: "Todos os docentes", options: filteredOtherDocentes },
              ]}
              selectedIds={effectiveSelectedDocente}
              onToggleOption={(id) => dispatch({ type: "toggleDocente", id })}
            />

            <div className="flex items-end gap-2">
              <div className="flex-[1.05] min-w-0">
                <DrawerMultiSelect
                  label="Sala"
                  triggerLabel={selectedSalaLabel}
                  open={openDropdown === "salas"}
                  onToggle={() => setOpenDropdown((prev) => (prev === "salas" ? null : "salas"))}
                  search={salasSearch}
                  onSearchChange={setSalasSearch}
                  listMaxHeightClass="max-h-48"
                  groups={[
                    {
                      heading: "Tipologia correspondente",
                      options: filteredPreferredSalas.map((room) => ({
                        id: room.id,
                        label: `${room.label} - ${room.type}`,
                      })),
                    },
                    {
                      heading: "Outras Salas",
                      options: filteredOtherSalas.map((room) => ({
                        id: room.id,
                        label: `${room.label} - ${room.type}`,
                      })),
                    },
                  ]}
                  selectedIds={effectiveSelectedSala}
                  onToggleOption={(id) => dispatch({ type: "toggleSala", id })}
                />
              </div>

              <div className="flex-[1.15] min-w-0">
                <DrawerMultiSelect
                  label="Turmas"
                  triggerLabel={`Turmas (${effectiveSelectedTurmas.length})`}
                  open={openDropdown === "turmas"}
                  onToggle={() => setOpenDropdown((prev) => (prev === "turmas" ? null : "turmas"))}
                  search={turmasSearch}
                  onSearchChange={setTurmasSearch}
                  listMaxHeightClass="max-h-44"
                  groups={[
                    { options: filteredTurmas.map((turma) => ({ id: turma, label: turma })) },
                  ]}
                  selectedIds={effectiveSelectedTurmas}
                  onToggleOption={(id) =>
                    dispatch({
                      type: "setTurmas",
                      value: toggleSelection(effectiveSelectedTurmas, id),
                    })
                  }
                />
              </div>
            </div>
          </div>

          {/*
            The drawer is still read-only: there is no save endpoint or onSave
            prop yet, so the form edits live only in local state. Keep the
            button visibly disabled until the persistence path is wired up
            rather than shipping a button that silently does nothing.
          */}
          <button
            type="button"
            disabled
            title="Edição ainda não disponível"
            className="w-full bg-[#8c2d19]/40 text-white/50 font-semibold rounded py-2.5 mt-4 cursor-not-allowed"
          >
            Guardar
          </button>

          <div className="pt-4 border-t border-white/20">
            <h3 className="text-white/90 font-semibold mb-3">Conflitos Detectados</h3>
            {eventConflicts.length === 0 ? (
              <p className="text-white/60 text-sm">Sem conflitos</p>
            ) : (
              <div className="space-y-2">
                {eventConflicts.map((conflict) => (
                  <div
                    key={conflict.id}
                    className="text-xs border-l-3 border-white/30 bg-white/5 rounded p-2 space-y-1.5"
                  >
                    <div className="text-white/90 font-semibold space-y-0.5">
                      {conflict.event_names.map((name, idx) => (
                        <p key={idx} className="line-clamp-1">
                          {name}
                        </p>
                      ))}
                    </div>
                    <p className="text-white/70">
                      {conflict.day} · {conflict.time}
                    </p>
                    <div className="space-y-0.5 pt-1 border-t border-white/10">
                      {conflict.conflict_reasons.map((reason, idx) => (
                        <p key={idx} className="text-white/80 flex items-start gap-1">
                          <span className="text-white/60 flex-shrink-0">•</span>
                          <span>{reason}</span>
                        </p>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </aside>
  );
}
