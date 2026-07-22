import { useMemo, useRef, useState, type Dispatch } from "react";
import type { ConflictRecord } from "@/types/project/conflicts";
import type { Weekday } from "@/types/project/weekday";
import type { WeekGridEvent } from "@/components/schedule/WeekGrid";
import { formatDurationSlots } from "@/utils/time";
import { WEEKDAYS, WEEKDAY_LABELS_LONG } from "@/utils/weekdays";
import ConflictCard from "./ConflictCard";
import { DRAWER_DISMISS_IGNORE_SELECTOR } from "./dismissable";
import DrawerMultiSelect from "./DrawerMultiSelect";
import { useDismissable } from "./useDismissable";
import { useDrawerSearch } from "./useDrawerSearch";
import {
  toggleSelection,
  type EventDrawerFormAction,
  type EventDrawerFormState,
} from "./useEventDrawerForm";

type TeacherOption = {
  id: string;
  acronym: string;
  label: string;
};

type RoomOption = {
  id: string;
  label: string;
  type: string;
  seats: string | null;
};

/** Sala dropdown option: name, capacity in front, then tipologia (PI ToDo #8a). */
function salaToOption(room: RoomOption) {
  const capacity = room.seats ? ` (${room.seats})` : "";
  const type = room.type ? ` - ${room.type}` : "";
  return { id: room.id, label: `${room.label}${capacity}${type}` };
}

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
  /**
   * Lifted to the page so the grid can preview edits live and a placement
   * click can write straight into it. Field edits made here (UC, docente,
   * sala, turma, duration, day/time typed or stepped in the drawer) stay a
   * draft until Guardar; only a grid placement click commits on its own.
   */
  formState: EventDrawerFormState;
  dispatch: Dispatch<EventDrawerFormAction>;
  placementMode: boolean;
  onTogglePlacement: () => void;
  /** Commits the current draft into the local session edit. */
  onSave: () => void;
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
  formState,
  dispatch,
  placementMode,
  onTogglePlacement,
  onSave,
}: EditEventDrawerProps) {
  const {
    selectedUcOverride,
    selectedDocenteOverride,
    selectedSalaOverride,
    selectedTurmasOverride,
    selectedWeekday,
    startTime,
    durationSlots,
  } = formState;

  const docentesSearch = useDrawerSearch();
  const salasSearch = useDrawerSearch();
  const turmasSearch = useDrawerSearch();

  // Conflicts reference bare session ids (contract C2), so matching on
  // `sessionId` works for every event expanded from the session regardless of
  // which turma's card the user clicked.
  const eventConflicts = useMemo(
    () =>
      event ? conflicts.filter((conflict) => conflict.event_ids.includes(event.sessionId)) : [],
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
    ignoreSelector: DRAWER_DISMISS_IGNORE_SELECTOR,
  });

  const selectedUc = useMemo(() => {
    if (selectedUcOverride && ucOptions.includes(selectedUcOverride)) return selectedUcOverride;
    if (preferredUc && ucOptions.includes(preferredUc)) return preferredUc;
    return ucOptions[0] ?? "";
  }, [preferredUc, selectedUcOverride, ucOptions]);

  const preferredRoomTypes = useMemo(() => {
    if (!event?.rooms || event.rooms.length === 0) return new Set<string>();
    const eventRoomIds = new Set(event.rooms.map((room) => room.id));
    const roomTypes = roomOptions
      .filter((room) => eventRoomIds.has(room.id))
      .map((room) => room.type)
      .filter((type) => type.length > 0);
    return new Set(roomTypes);
  }, [event, roomOptions]);

  const selectedEventTeacherIds = useMemo(
    () => new Set((event?.teachers ?? []).map((teacher) => teacher.id)),
    [event?.teachers],
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

  // Capacities of the event's current room(s); rooms matching one of these sort
  // to the top of their type group (PI ToDo #8a follow-up).
  const preferredSeats = useMemo(() => {
    if (!event?.rooms || event.rooms.length === 0) return new Set<string>();
    const eventRoomIds = new Set(event.rooms.map((room) => room.id));
    return new Set(
      roomOptions
        .filter((room) => eventRoomIds.has(room.id))
        .map((room) => room.seats)
        .filter((seats): seats is string => Boolean(seats)),
    );
  }, [event, roomOptions]);

  // Same capacity first, then the rest (stable, so name order is preserved).
  const bySeatsMatch = (a: RoomOption, b: RoomOption) =>
    Number(preferredSeats.has(b.seats ?? "")) - Number(preferredSeats.has(a.seats ?? ""));

  // Selected rooms head the list in their own group, so they're pulled out of
  // the type groups below to avoid showing twice.
  const selectedSalaIds = useMemo(() => new Set(selectedSalaOverride), [selectedSalaOverride]);

  const selectedSalas = useMemo(
    () => roomOptions.filter((room) => selectedSalaIds.has(room.id)),
    [roomOptions, selectedSalaIds],
  );

  const preferredSalas = useMemo(
    () =>
      roomOptions
        .filter((room) => !selectedSalaIds.has(room.id) && preferredRoomTypes.has(room.type))
        .sort(bySeatsMatch),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [preferredRoomTypes, preferredSeats, roomOptions, selectedSalaIds],
  );

  const otherSalas = useMemo(
    () =>
      roomOptions
        .filter((room) => !selectedSalaIds.has(room.id) && !preferredRoomTypes.has(room.type))
        .sort(bySeatsMatch),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [preferredRoomTypes, preferredSeats, roomOptions, selectedSalaIds],
  );

  const docenteMatches = docentesSearch.matches;
  const salaMatches = salasSearch.matches;
  const turmaMatches = turmasSearch.matches;

  const filteredSelectedClassDocentes = useMemo(
    () => selectedClassDocentes.filter((docente) => docenteMatches(docente.label)),
    [docenteMatches, selectedClassDocentes],
  );

  const filteredOtherDocentes = useMemo(
    () => otherDocentes.filter((docente) => docenteMatches(docente.label)),
    [docenteMatches, otherDocentes],
  );

  const filteredSelectedSalas = useMemo(
    () => selectedSalas.filter((room) => salaMatches(`${room.id} ${room.type}`)),
    [selectedSalas, salaMatches],
  );

  const filteredPreferredSalas = useMemo(
    () => preferredSalas.filter((room) => salaMatches(`${room.id} ${room.type}`)),
    [preferredSalas, salaMatches],
  );

  const filteredOtherSalas = useMemo(
    () => otherSalas.filter((room) => salaMatches(`${room.id} ${room.type}`)),
    [otherSalas, salaMatches],
  );

  const eventTurmas = useMemo(() => new Set(event?.classCodes ?? []), [event?.classCodes]);

  // A shared event carries turmas from another course that aren't in this
  // course's list — append them so they're visible and selectable.
  const turmaDropdownOptions = useMemo(() => {
    const extra = (event?.classCodes ?? []).filter((code) => !turmaOptions.includes(code));
    return extra.length ? [...turmaOptions, ...extra] : turmaOptions;
  }, [event, turmaOptions]);

  // The event's own turmas float to the top of the list; everything else keeps
  // its incoming (numeric) order since Array.sort is stable (PI ToDo #8d).
  const filteredTurmas = useMemo(
    () =>
      turmaDropdownOptions
        .filter((turma) => turmaMatches(turma))
        .sort((a, b) => Number(eventTurmas.has(b)) - Number(eventTurmas.has(a))),
    [turmaDropdownOptions, turmaMatches, eventTurmas],
  );

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
    const docentes = effectiveSelectedDocente
      .map((id) => teacherOptions.find((docente) => docente.id === id))
      .filter((docente): docente is TeacherOption => Boolean(docente));
    const first = docentes[0];
    if (!first) return "Selecionar...";
    // One docente keeps the full "acronym - name"; multiple show every acronym
    // so both professors are visible in the trigger (PI ToDo #8b).
    return docentes.length === 1 ? first.label : docentes.map((d) => d.acronym).join(", ");
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
    () => selectedTurmasOverride.filter((id) => turmaDropdownOptions.includes(id)),
    [selectedTurmasOverride, turmaDropdownOptions],
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
        // Positioned by the page: fills the schedule content area, which
        // starts exactly where the (height-variable) navbar ends.
        "absolute left-0 top-0 h-full w-[min(92vw,420px)] z-40 transition-transform duration-200",
        collapsed ? "-translate-x-full" : "translate-x-0",
      ].join(" ")}
    >
      <button
        type="button"
        onClick={() => onCollapsedChange(!collapsed)}
        onMouseEnter={() => onCollapsedChange(!collapsed)}
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
                  onClick={() => dispatch({ type: "shiftStartTime", delta: -30 })}
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
                    dispatch({ type: "setStartTime", value: event.target.value })
                  }
                  onBlur={(event) =>
                    dispatch({ type: "normalizeStartTime", raw: event.target.value })
                  }
                  className="w-14 bg-[#2a303a] border border-white/20 rounded px-1.5 py-1.5 text-white text-center text-sm"
                />
                <button
                  type="button"
                  onClick={() => dispatch({ type: "shiftStartTime", delta: 30 })}
                  className="h-8 w-8 rounded border border-white/20 bg-[#2a303a] text-white/80 hover:text-white text-sm"
                  aria-label="Aumentar hora de início em 30 minutos"
                >
                  +
                </button>
              </div>
            </div>
            <div className="block text-sm flex-1 min-w-0">
              <span id="edit-event-duration-label" className="mb-1.5 block text-white/90">
                Duração
              </span>
              <div className="flex items-center gap-1">
                <button
                  type="button"
                  onClick={() => dispatch({ type: "shiftDuration", delta: -1 })}
                  className="h-8 w-8 rounded border border-white/20 bg-[#2a303a] text-white/80 hover:text-white text-sm"
                  aria-label="Diminuir duração em 30 minutos"
                >
                  -
                </button>
                <span
                  aria-labelledby="edit-event-duration-label"
                  className="w-14 bg-[#2a303a] border border-white/20 rounded px-1.5 py-1.5 text-white text-center text-sm tabular-nums"
                >
                  {formatDurationSlots(durationSlots)}
                </span>
                <button
                  type="button"
                  onClick={() => dispatch({ type: "shiftDuration", delta: 1 })}
                  className="h-8 w-8 rounded border border-white/20 bg-[#2a303a] text-white/80 hover:text-white text-sm"
                  aria-label="Aumentar duração em 30 minutos"
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

          <button
            type="button"
            onClick={onTogglePlacement}
            aria-pressed={placementMode}
            className={`w-full rounded py-2 text-sm font-medium border transition-colors ${
              placementMode
                ? "border-[#c73f24] bg-[#c73f24]/20 text-white"
                : "border-white/20 bg-[#2a303a] text-white/80 hover:text-white"
            }`}
          >
            {placementMode ? "A mover — clique num espaço…" : "Mover no horário"}
          </button>

          <div className="space-y-4" ref={dropdownAreaRef}>
            <DrawerMultiSelect
              label="Docentes"
              triggerLabel={selectedDocenteLabel}
              open={openDropdown === "docentes"}
              onToggle={() => setOpenDropdown((prev) => (prev === "docentes" ? null : "docentes"))}
              search={docentesSearch.query}
              onSearchChange={docentesSearch.setQuery}
              listMaxHeightClass="max-h-48"
              groups={[
                {
                  heading: "Docentes desta aula",
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
                  search={salasSearch.query}
                  onSearchChange={salasSearch.setQuery}
                  listMaxHeightClass="max-h-32"
                  groups={[
                    {
                      heading: "Selecionada",
                      options: filteredSelectedSalas.map(salaToOption),
                    },
                    {
                      heading: "Tipologia correspondente",
                      options: filteredPreferredSalas.map(salaToOption),
                    },
                    {
                      heading: "Outras Salas",
                      options: filteredOtherSalas.map(salaToOption),
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
                  search={turmasSearch.query}
                  onSearchChange={turmasSearch.setQuery}
                  listMaxHeightClass="max-h-32"
                  groups={[
                    {
                      options: filteredTurmas.map((turma) => ({
                        id: turma,
                        // Flag the event's own turma(s) so the original is clear (#17).
                        label: eventTurmas.has(turma) ? `${turma} · original` : turma,
                      })),
                    },
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

          <button
            type="button"
            onClick={onSave}
            className="w-full bg-[#c73f24] hover:bg-[#b3361f] text-white font-semibold rounded py-2.5 mt-4 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#c73f24]"
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
                  <ConflictCard key={conflict.id} conflict={conflict} variant="compact" />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </aside>
  );
}
