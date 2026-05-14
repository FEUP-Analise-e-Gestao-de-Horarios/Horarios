import { useEffect, useMemo, useRef, useState } from "react";
import type { ConflictRecord } from "@/types/project/conflicts";
import type { WeekGridEvent } from "@/components/schedule/WeekGrid";
import { hhmmToMinutes, minutesToTime } from "@/utils/time";
import { WEEKDAYS, WEEKDAY_LABELS_LONG } from "@/utils/weekdays";
import DrawerMultiSelect from "./DrawerMultiSelect";

function normalizeText(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
}

function getConflictDay(weekday: WeekGridEvent["weekday"]): string {
  return weekdayLabelToValue(weekday).split("-")[0] ?? "";
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

function clampTimeMinutes(totalMinutes: number): number {
  return Math.max(MIN_TIME_MINUTES, Math.min(MAX_TIME_MINUTES, totalMinutes));
}

function shiftTimeByMinutes(time: string, deltaMinutes: number): string {
  const [hours, minutes] = time.split(":").map(Number);
  if (hours === undefined || minutes === undefined || Number.isNaN(hours) || Number.isNaN(minutes))
    return time;

  const totalMinutes = clampTimeMinutes(hours * 60 + minutes + deltaMinutes);
  return minutesToTime(totalMinutes);
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

function toggleSelection(current: string[], itemId: string): string[] {
  return current.includes(itemId)
    ? current.filter((selectedId) => selectedId !== itemId)
    : [...current, itemId];
}

function weekdayLabelToValue(weekday: WeekGridEvent["weekday"]): string {
  return WEEKDAY_LABELS_LONG[weekday];
}

function getInitialFormState(event?: WeekGridEvent | null) {
  if (event) {
    return {
      selectedUcOverride: event.uc ?? "",
      selectedDocenteOverride: event.teacherIds ?? [],
      selectedSalaOverride: event.roomIds ?? [],
      selectedTurmasOverride: event.classCodes ?? (event.turma ? [event.turma] : []),
      selectedWeekday: weekdayLabelToValue(event.weekday),
      startTime: minutesToTime(hhmmToMinutes(event.startTime)),
      endTime: minutesToTime(hhmmToMinutes(event.startTime) + event.duration * 30),
    };
  }
  return {
    selectedUcOverride: "",
    selectedDocenteOverride: [] as string[],
    selectedSalaOverride: [] as string[],
    selectedTurmasOverride: [] as string[],
    selectedWeekday: WEEKDAY_LABELS_LONG.monday,
    startTime: "10:30",
    endTime: "12:30",
  };
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
  const [formState, setFormState] = useState(() => getInitialFormState(event));
  const {
    selectedUcOverride,
    selectedDocenteOverride,
    selectedSalaOverride,
    selectedTurmasOverride,
    selectedWeekday,
    startTime,
    endTime,
  } = formState;

  function setSelectedUcOverride(val: string) {
    setFormState((prev) => ({ ...prev, selectedUcOverride: val }));
  }
  function setSelectedDocenteOverride(val: string[] | ((prev: string[]) => string[])) {
    setFormState((prev) => ({
      ...prev,
      selectedDocenteOverride: typeof val === "function" ? val(prev.selectedDocenteOverride) : val,
    }));
  }
  function setSelectedSalaOverride(val: string[] | ((prev: string[]) => string[])) {
    setFormState((prev) => ({
      ...prev,
      selectedSalaOverride: typeof val === "function" ? val(prev.selectedSalaOverride) : val,
    }));
  }
  function setSelectedTurmasOverride(val: string[]) {
    setFormState((prev) => ({ ...prev, selectedTurmasOverride: val }));
  }
  function setSelectedWeekday(val: string) {
    setFormState((prev) => ({ ...prev, selectedWeekday: val }));
  }
  function setStartTime(val: string | ((prev: string) => string)) {
    setFormState((prev) => ({
      ...prev,
      startTime: typeof val === "function" ? val(prev.startTime) : val,
    }));
  }
  function setEndTime(val: string | ((prev: string) => string)) {
    setFormState((prev) => ({
      ...prev,
      endTime: typeof val === "function" ? val(prev.endTime) : val,
    }));
  }
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

  useEffect(() => {
    function handleOutsideClick(event: MouseEvent) {
      const target = event.target as Node | null;
      if (dropdownAreaRef.current?.contains(target)) return;
      setOpenDropdown(null);
      if (!asideRef.current || asideRef.current.contains(target)) return;
      if (
        target instanceof Element &&
        target.closest("[data-schedule-event],[data-schedule-navbar]")
      ) {
        return;
      }
      onClose();
    }

    function handleEscapeKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onClose();
      }
    }

    document.addEventListener("mousedown", handleOutsideClick);
    document.addEventListener("keydown", handleEscapeKey);
    return () => {
      document.removeEventListener("mousedown", handleOutsideClick);
      document.removeEventListener("keydown", handleEscapeKey);
    };
  }, [onClose]);

  const selectedUc = useMemo(() => {
    if (selectedUcOverride && ucOptions.includes(selectedUcOverride)) return selectedUcOverride;
    if (preferredUc && ucOptions.includes(preferredUc)) return preferredUc;
    return ucOptions[0] ?? "";
  }, [preferredUc, selectedUcOverride, ucOptions]);

  const subjectTeacherOptions = useMemo<{ id: string }[]>(() => [], []);
  const subjectTeacherIds = useMemo(() => new Set<string>(), []);

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

  const otherSubjectDocentes = useMemo(
    () =>
      teacherOptions.filter(
        (docente) => subjectTeacherIds.has(docente.id) && !selectedEventTeacherIds.has(docente.id),
      ),
    [selectedEventTeacherIds, subjectTeacherIds, teacherOptions],
  );

  const otherDocentes = useMemo(
    () => teacherOptions.filter((docente) => !subjectTeacherIds.has(docente.id)),
    [subjectTeacherIds, teacherOptions],
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
    () => [...selectedClassDocentes, ...otherSubjectDocentes, ...otherDocentes],
    [otherDocentes, otherSubjectDocentes, selectedClassDocentes],
  );

  const orderedSalas = useMemo(
    () => [...preferredSalas, ...otherSalas],
    [otherSalas, preferredSalas],
  );

  const filteredSelectedClassDocentes = useMemo(() => {
    const query = docentesSearch.toLowerCase().trim();
    if (!query) return selectedClassDocentes;
    return selectedClassDocentes.filter((docente) => docente.label.toLowerCase().includes(query));
  }, [docentesSearch, selectedClassDocentes]);

  const filteredOtherSubjectDocentes = useMemo(() => {
    const query = docentesSearch.toLowerCase().trim();
    if (!query) return otherSubjectDocentes;
    return otherSubjectDocentes.filter((docente) => docente.label.toLowerCase().includes(query));
  }, [docentesSearch, otherSubjectDocentes]);

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

  const effectiveSelectedDocente = useMemo(() => {
    const valid = selectedDocenteOverride.filter((id) => teacherOptions.some((d) => d.id === id));
    if (valid.length > 0) return valid;
    if (selectedClassDocentes.length > 0) return [selectedClassDocentes[0]!.id];
    if (subjectTeacherOptions.length > 0) return [subjectTeacherOptions[0]!.id];
    return orderedDocentes.slice(0, 1).map((docente) => docente.id);
  }, [
    orderedDocentes,
    selectedClassDocentes,
    selectedDocenteOverride,
    teacherOptions,
    subjectTeacherOptions,
  ]);

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
              onChange={(event) => setSelectedUcOverride(event.target.value)}
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
                  onClick={() => setStartTime((current) => shiftTimeByMinutes(current, -30))}
                  className="h-8 w-8 rounded border border-white/20 bg-[#2a303a] text-white/80 hover:text-white text-sm"
                  aria-label="Diminuir hora de inicio em 30 minutos"
                >
                  -
                </button>
                <input
                  type="text"
                  inputMode="numeric"
                  placeholder="HH:MM"
                  value={startTime}
                  onChange={(event) => setStartTime(event.target.value)}
                  onBlur={(event) =>
                    setStartTime((previous) => normalizeTimeValue(event.target.value, previous))
                  }
                  className="w-14 bg-[#2a303a] border border-white/20 rounded px-1.5 py-1.5 text-white text-center text-sm"
                />
                <button
                  type="button"
                  onClick={() => setStartTime((current) => shiftTimeByMinutes(current, 30))}
                  className="h-8 w-8 rounded border border-white/20 bg-[#2a303a] text-white/80 hover:text-white text-sm"
                  aria-label="Aumentar hora de inicio em 30 minutos"
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
                  onClick={() => setEndTime((current) => shiftTimeByMinutes(current, -30))}
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
                  onChange={(event) => setEndTime(event.target.value)}
                  onBlur={(event) =>
                    setEndTime((previous) => normalizeTimeValue(event.target.value, previous))
                  }
                  className="w-14 bg-[#2a303a] border border-white/20 rounded px-1.5 py-1.5 text-white text-center text-sm"
                />
                <button
                  type="button"
                  onClick={() => setEndTime((current) => shiftTimeByMinutes(current, 30))}
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
                onChange={(event) => setSelectedWeekday(event.target.value)}
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
              search={docentesSearch}
              onSearchChange={setDocentesSearch}
              listMaxHeightClass="max-h-52"
              groups={[
                {
                  heading: "Docentes da turma selecionada",
                  options: filteredSelectedClassDocentes,
                },
                { heading: "Outros docentes da UC", options: filteredOtherSubjectDocentes },
                { heading: "Todos os docentes", options: filteredOtherDocentes },
              ]}
              selectedIds={effectiveSelectedDocente}
              onToggleOption={(id) =>
                setSelectedDocenteOverride((current) => toggleSelection(current, id))
              }
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
                  onToggleOption={(id) =>
                    setSelectedSalaOverride((current) => toggleSelection(current, id))
                  }
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
                    setSelectedTurmasOverride(toggleSelection(effectiveSelectedTurmas, id))
                  }
                />
              </div>
            </div>
          </div>

          <button
            type="button"
            className="w-full bg-[#8c2d19] text-white font-semibold rounded py-2.5 hover:brightness-110 transition mt-4"
          >
            Submit
          </button>

          <div className="pt-4 border-t border-white/20">
            <h3 className="text-white/90 font-semibold mb-3">Conflitos Detectados</h3>
            {eventConflicts.length === 0 ? (
              <p className="text-white/60 text-sm">Nenhum conflito</p>
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
