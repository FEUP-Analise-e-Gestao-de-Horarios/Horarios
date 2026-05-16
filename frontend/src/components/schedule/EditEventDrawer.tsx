import { useMemo, useRef, useState } from "react";
import type { ConflictRecord } from "@/types/project/conflicts";
import type { WeekGridEvent } from "@/components/schedule/WeekGrid";
import { WEEKDAYS, WEEKDAY_LABELS_LONG } from "@/utils/weekdays";
import ConflictCard from "./ConflictCard";
import { DRAWER_DISMISS_IGNORE_SELECTOR } from "./dismissable";
import DrawerMultiSelect from "./DrawerMultiSelect";
import { useDismissable } from "./useDismissable";
import { useDrawerSearch } from "./useDrawerSearch";
import { toggleSelection, useEventDrawerForm } from "./useEventDrawerForm";

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
  const [formState, dispatch] = useEventDrawerForm(event);
  const {
    selectedUcOverride,
    selectedDocenteOverride,
    selectedSalaOverride,
    selectedTurmasOverride,
    selectedWeekday,
    startTime,
    endTime,
  } = formState;

  const docentesSearch = useDrawerSearch();
  const salasSearch = useDrawerSearch();
  const turmasSearch = useDrawerSearch();
  const eventConflicts = useMemo(
    () => (event ? conflicts.filter((conflict) => conflict.event_ids.includes(event.id)) : []),
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

  const orderedDocentes = useMemo(
    () => [...selectedClassDocentes, ...otherDocentes],
    [otherDocentes, selectedClassDocentes],
  );

  const orderedSalas = useMemo(
    () => [...preferredSalas, ...otherSalas],
    [otherSalas, preferredSalas],
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

  const filteredPreferredSalas = useMemo(
    () => preferredSalas.filter((room) => salaMatches(`${room.id} ${room.type}`)),
    [preferredSalas, salaMatches],
  );

  const filteredOtherSalas = useMemo(
    () => otherSalas.filter((room) => salaMatches(`${room.id} ${room.type}`)),
    [otherSalas, salaMatches],
  );

  const filteredTurmas = useMemo(
    () => turmaOptions.filter((turma) => turmaMatches(turma)),
    [turmaOptions, turmaMatches],
  );

  const effectiveSelectedDocente = useMemo(() => {
    const valid = selectedDocenteOverride.filter((id) => teacherOptions.some((d) => d.id === id));
    if (valid.length > 0) return valid;
    if (selectedClassDocentes.length > 0) return [selectedClassDocentes[0]!.id];
    return orderedDocentes.slice(0, 1).map((docente) => docente.id);
  }, [orderedDocentes, selectedClassDocentes, selectedDocenteOverride, teacherOptions]);

  const effectiveSelectedSala = useMemo(() => {
    const valid = selectedSalaOverride.filter((id) => roomOptions.some((room) => room.id === id));
    return valid.length > 0 ? valid : orderedSalas.slice(0, 1).map((room) => room.id);
  }, [orderedSalas, roomOptions, selectedSalaOverride]);

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
      .filter((room): room is (typeof orderedSalas)[number] => Boolean(room));
    if (labels.length === 0) return "Selecionar...";
    const first = labels[0];
    if (!first) return "Selecionar...";
    const firstLabel = first.label;
    return labels.length === 1 ? firstLabel : `${firstLabel} (+${labels.length - 1})`;
  }, [effectiveSelectedSala, roomOptions]);

  const effectiveSelectedTurmas = useMemo(() => {
    const valid = selectedTurmasOverride.filter((id) => filteredTurmas.includes(id));
    return valid.length > 0 ? valid : [...filteredTurmas];
  }, [filteredTurmas, selectedTurmasOverride]);

  if (!open) return null;

  return (
    <aside
      ref={asideRef}
      role="dialog"
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
            <label className="block text-sm flex-1 min-w-0">
              <span className="mb-1.5 block text-white/90">Hora Início</span>
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
            </label>
            <label className="block text-sm flex-1 min-w-0">
              <span className="mb-1.5 block text-white/90">Hora Fim</span>
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
            </label>
            <div className="border-l border-white/20 h-10 ml-1 mr-0.5" />
            <label className="block text-sm flex-1 min-w-0">
              <span className="mb-1.5 block text-white/90">Dia</span>
              <select
                value={selectedWeekday}
                onChange={(event) => dispatch({ type: "setWeekday", value: event.target.value })}
                className="w-full bg-[#2a303a] border border-white/20 rounded px-2 py-1.5 text-sm"
              >
                {WEEKDAYS.map((weekday) => (
                  <option key={weekday} value={WEEKDAY_LABELS_LONG[weekday]}>
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
              search={docentesSearch.query}
              onSearchChange={docentesSearch.setQuery}
              listMaxHeightClass="max-h-52"
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
                  search={turmasSearch.query}
                  onSearchChange={turmasSearch.setQuery}
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
