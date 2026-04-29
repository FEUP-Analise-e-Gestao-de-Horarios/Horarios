import { ALL_CONFLICTS } from "@/components/schedule/data";
import { useEffect, useMemo, useRef, useState } from "react";
import { useProjectSubject } from "@/api/hooks/useDashboard";
import type { WeekGridEvent } from "@/components/schedule/WeekGrid";

type TeacherOption = {
  id: string;
  label: string;
};

type RoomOption = {
  id: string;
  label: string;
  type: string;
};

interface SubjectOption {
  id: string;
  name: string;
}

interface EditEventDrawerProps {
  projectId: string;
  open: boolean;
  onClose: () => void;
  ucOptions: string[];
  turmaOptions: string[];
  teacherOptions: TeacherOption[];
  roomOptions: RoomOption[];
  subjectOptions: SubjectOption[];
  preferredUc?: string;
  event?: WeekGridEvent | null;
}

const MIN_TIME_MINUTES = 8 * 60;
const MAX_TIME_MINUTES = 19 * 60 + 30;

function formatMinutesToTime(totalMinutes: number): string {
  const hours = String(Math.floor(totalMinutes / 60)).padStart(2, "0");
  const minutes = String(totalMinutes % 60).padStart(2, "0");
  return `${hours}:${minutes}`;
}

function clampTimeMinutes(totalMinutes: number): number {
  return Math.max(MIN_TIME_MINUTES, Math.min(MAX_TIME_MINUTES, totalMinutes));
}

function shiftTimeByMinutes(time: string, deltaMinutes: number): string {
  const [hours, minutes] = time.split(":").map(Number);
  if (hours === undefined || minutes === undefined || Number.isNaN(hours) || Number.isNaN(minutes))
    return time;

  const totalMinutes = clampTimeMinutes(hours * 60 + minutes + deltaMinutes);
  return formatMinutesToTime(totalMinutes);
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
  return formatMinutesToTime(totalMinutes);
}

function toggleSelection(current: string[], itemId: string): string[] {
  return current.includes(itemId)
    ? current.filter((selectedId) => selectedId !== itemId)
    : [...current, itemId];
}

function formatMinutesToInputValue(totalMinutes: number): string {
  return formatMinutesToTime(totalMinutes);
}

function hhmmToMinutes(hhmm: number): number {
  const hours = Math.floor(hhmm / 100);
  const minutes = hhmm % 100;
  return hours * 60 + minutes;
}

function weekdayLabelToValue(weekday: WeekGridEvent["weekday"]): string {
  const labels: Record<WeekGridEvent["weekday"], string> = {
    monday: "Segunda-Feira",
    tuesday: "Terça-Feira",
    wednesday: "Quarta-Feira",
    thursday: "Quinta-Feira",
    friday: "Sexta-Feira",
    saturday: "Sábado",
  };
  return labels[weekday];
}

function getInitialFormState(event?: WeekGridEvent | null) {
  if (event) {
    return {
      selectedUcOverride: event.uc ?? "",
      selectedDocenteOverride: event.teacherIds ?? [],
      selectedSalaOverride: event.roomIds ?? [],
      selectedTurmasOverride: event.classCodes ?? (event.turma ? [event.turma] : []),
      selectedWeekday: weekdayLabelToValue(event.weekday),
      startTime: formatMinutesToInputValue(hhmmToMinutes(event.startTime)),
      endTime: formatMinutesToInputValue(hhmmToMinutes(event.startTime) + event.duration * 30),
    };
  }
  return {
    selectedUcOverride: "",
    selectedDocenteOverride: [] as string[],
    selectedSalaOverride: [] as string[],
    selectedTurmasOverride: [] as string[],
    selectedWeekday: "Segunda-Feira",
    startTime: "10:30",
    endTime: "12:30",
  };
}

export default function EditEventDrawer({
  projectId,
  open,
  onClose,
  ucOptions,
  turmaOptions,
  teacherOptions,
  roomOptions,
  subjectOptions,
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
  const [openDropdown, setOpenDropdown] = useState<"docentes" | "salas" | "turmas" | null>(null);
  const dropdownAreaRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleOutsideClick(event: MouseEvent) {
      if (dropdownAreaRef.current?.contains(event.target as Node)) return;
      setOpenDropdown(null);
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

  const selectedSubjectId = useMemo(
    () => subjectOptions.find((subject) => subject.name === selectedUc)?.id ?? "",
    [selectedUc, subjectOptions],
  );

  const { data: selectedSubject } = useProjectSubject(projectId, selectedSubjectId);

  const subjectTeacherOptions = useMemo(() => selectedSubject?.teachers ?? [], [selectedSubject]);

  const subjectTeacherIds = useMemo(
    () => new Set(subjectTeacherOptions.map((teacher) => teacher.id)),
    [subjectTeacherOptions],
  );

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
    if (labels.length === 0) return "Selecionar...";
    return labels.length === 1 ? labels[0] : `${labels[0]} (+${labels.length - 1})`;
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

  return (
    <div
      className={[
        "fixed inset-0 z-50 transition-opacity",
        open ? "pointer-events-auto opacity-100" : "pointer-events-none opacity-0",
      ].join(" ")}
      aria-hidden={!open}
    >
      <button
        onClick={onClose}
        className="absolute inset-0 bg-black/45"
        aria-label="Fechar painel de edição"
      />

      <aside
        className={[
          "absolute right-0 top-0 h-full w-[min(92vw,450px)] bg-[#1d2128] text-white border-l border-white/15 shadow-[-8px_0_24px_rgba(0,0,0,0.45)] transition-transform overflow-y-auto",
          open ? "translate-x-0" : "translate-x-full",
        ].join(" ")}
      >
        <div className="sticky top-0 z-20 bg-[#1d2128] border-b border-white/10 px-5 py-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Editar Evento</h2>
          <button
            onClick={onClose}
            className="text-white/80 hover:text-white border border-white/20 rounded px-2 py-1 text-sm"
          >
            Fechar
          </button>
        </div>

        <div className="px-5 py-4 space-y-4">
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
                <option>Segunda-Feira</option>
                <option>Terça-Feira</option>
                <option>Quarta-Feira</option>
                <option>Quinta-Feira</option>
                <option>Sexta-Feira</option>
                <option>Sábado</option>
              </select>
            </label>
          </div>

          <div className="space-y-4" ref={dropdownAreaRef}>
            <div className="relative text-sm">
              <span className="mb-1.5 block text-white/90">Docentes</span>
              <button
                onClick={() => setOpenDropdown((prev) => (prev === "docentes" ? null : "docentes"))}
                className="w-full bg-[#2a303a] border border-white/20 rounded px-2.5 py-2 text-left flex items-center justify-between"
              >
                <span>{selectedDocenteLabel}</span>
                <span className="text-white/70">▾</span>
              </button>

              {openDropdown === "docentes" && (
                <div className="absolute z-10 mt-2 w-full bg-[#222834] border border-white/20 rounded shadow-[0_10px_20px_rgba(0,0,0,0.45)] p-2">
                  <input
                    value={docentesSearch}
                    onChange={(event) => setDocentesSearch(event.target.value)}
                    placeholder="Search..."
                    className="mb-2 w-full bg-[#2a303a] border border-white/20 rounded px-2.5 py-2"
                  />
                  <div className="max-h-52 overflow-y-auto space-y-1">
                    {filteredSelectedClassDocentes.length > 0 && (
                      <p className="px-2 py-1 text-xs uppercase tracking-wide text-white/60">
                        Docentes da turma selecionada
                      </p>
                    )}
                    {filteredSelectedClassDocentes.map((docente) => (
                      <button
                        key={docente.id}
                        onClick={() => {
                          setSelectedDocenteOverride((current) =>
                            toggleSelection(current, docente.id),
                          );
                          setOpenDropdown(null);
                        }}
                        className={`w-full px-2 py-1.5 text-left rounded ${
                          effectiveSelectedDocente.includes(docente.id)
                            ? "bg-red-900/40 text-white font-semibold"
                            : "text-white hover:bg-white/10"
                        }`}
                      >
                        {docente.label}
                      </button>
                    ))}

                    {filteredOtherSubjectDocentes.length > 0 && (
                      <p className="px-2 py-1 text-xs uppercase tracking-wide text-white/60">
                        Outros docentes da UC
                      </p>
                    )}
                    {filteredOtherSubjectDocentes.map((docente) => (
                      <button
                        key={docente.id}
                        onClick={() => {
                          setSelectedDocenteOverride((current) =>
                            toggleSelection(current, docente.id),
                          );
                          setOpenDropdown(null);
                        }}
                        className={`w-full px-2 py-1.5 text-left rounded ${
                          effectiveSelectedDocente.includes(docente.id)
                            ? "bg-red-900/40 text-white font-semibold"
                            : "text-white hover:bg-white/10"
                        }`}
                      >
                        {docente.label}
                      </button>
                    ))}

                    {filteredOtherDocentes.length > 0 && (
                      <p className="px-2 py-1 text-xs uppercase tracking-wide text-white/60">
                        Todos os docentes
                      </p>
                    )}
                    {filteredOtherDocentes.map((docente) => (
                      <button
                        key={docente.id}
                        onClick={() => {
                          setSelectedDocenteOverride((current) =>
                            toggleSelection(current, docente.id),
                          );
                          setOpenDropdown(null);
                        }}
                        className={`w-full px-2 py-1.5 text-left rounded ${
                          effectiveSelectedDocente.includes(docente.id)
                            ? "bg-red-900/40 text-white font-semibold"
                            : "text-white hover:bg-white/10"
                        }`}
                      >
                        {docente.label}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="flex items-end gap-2">
              <div className="relative text-sm flex-[1.05] min-w-0">
                <span className="mb-1.5 block text-white/90">Sala</span>
                <button
                  onClick={() => setOpenDropdown((prev) => (prev === "salas" ? null : "salas"))}
                  className="w-full bg-[#2a303a] border border-white/20 rounded px-2.5 py-2 text-left flex items-center justify-between"
                >
                  <span>{selectedSalaLabel}</span>
                  <span className="text-white/70">▾</span>
                </button>

                {openDropdown === "salas" && (
                  <div className="absolute z-10 mt-2 w-full bg-[#222834] border border-white/20 rounded shadow-[0_10px_20px_rgba(0,0,0,0.45)] p-2">
                    <input
                      value={salasSearch}
                      onChange={(event) => setSalasSearch(event.target.value)}
                      placeholder="Search..."
                      className="mb-2 w-full bg-[#2a303a] border border-white/20 rounded px-2.5 py-2"
                    />
                    <div className="max-h-48 overflow-y-auto space-y-1">
                      {filteredPreferredSalas.length > 0 && (
                        <p className="px-2 py-1 text-xs uppercase tracking-wide text-white/60">
                          Tipologia correspondente
                        </p>
                      )}
                      {filteredPreferredSalas.map((room) => (
                        <button
                          key={room.id}
                          onClick={() => {
                            setSelectedSalaOverride((current) => toggleSelection(current, room.id));
                            setOpenDropdown(null);
                          }}
                          className={`w-full px-2 py-1.5 text-left rounded ${
                            effectiveSelectedSala.includes(room.id)
                              ? "bg-red-900/40 text-white font-semibold"
                              : "text-white hover:bg-white/10"
                          }`}
                        >
                          {room.label} - {room.type}
                        </button>
                      ))}

                      {filteredOtherSalas.length > 0 && (
                        <p className="px-2 py-1 text-xs uppercase tracking-wide text-white/60">
                          Outras Salas
                        </p>
                      )}
                      {filteredOtherSalas.map((room) => (
                        <button
                          key={room.id}
                          onClick={() => {
                            setSelectedSalaOverride((current) => toggleSelection(current, room.id));
                            setOpenDropdown(null);
                          }}
                          className={`w-full px-2 py-1.5 text-left rounded ${
                            effectiveSelectedSala.includes(room.id)
                              ? "bg-red-900/40 text-white font-semibold"
                              : "text-white hover:bg-white/10"
                          }`}
                        >
                          {room.label} - {room.type}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              <div className="relative text-sm flex-[1.15] min-w-0">
                <span className="mb-1.5 block text-white/90">Turmas</span>
                <button
                  onClick={() => setOpenDropdown((prev) => (prev === "turmas" ? null : "turmas"))}
                  className="w-full bg-[#2a303a] border border-white/20 rounded px-2.5 py-2 text-left flex items-center justify-between"
                >
                  <span>Turmas ({effectiveSelectedTurmas.length})</span>
                  <span className="text-white/70">▾</span>
                </button>

                {openDropdown === "turmas" && (
                  <div className="absolute z-10 mt-2 w-full bg-[#222834] border border-white/20 rounded shadow-[0_10px_20px_rgba(0,0,0,0.45)] p-2">
                    <input
                      value={turmasSearch}
                      onChange={(event) => setTurmasSearch(event.target.value)}
                      placeholder="Search..."
                      className="mb-2 w-full bg-[#2a303a] border border-white/20 rounded px-2.5 py-2"
                    />
                    <div className="max-h-44 overflow-y-auto space-y-1">
                      {filteredTurmas.map((turma) => (
                        <button
                          key={turma}
                          onClick={() =>
                            setSelectedTurmasOverride(
                              toggleSelection(effectiveSelectedTurmas, turma),
                            )
                          }
                          className="w-full px-2 py-1.5 text-left text-white hover:bg-white/10 rounded flex items-start gap-2"
                        >
                          <span
                            className={`mt-0.5 ${
                              effectiveSelectedTurmas.includes(turma)
                                ? "text-red-400"
                                : "text-white"
                            }`}
                          >
                            {effectiveSelectedTurmas.includes(turma) ? "☑" : "☐"}
                          </span>
                          <span>{turma}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          <button className="w-full bg-[#8c2d19] text-white font-semibold rounded py-2.5 hover:brightness-110 transition mt-4">
            Submit
          </button>

          <div className="pt-4 border-t border-white/20">
            <h3 className="text-white/90 font-semibold mb-3">Conflitos Detectados</h3>
            {ALL_CONFLICTS.length === 0 ? (
              <p className="text-white/60 text-sm">Nenhum conflito</p>
            ) : (
              <div className="space-y-2">
                {ALL_CONFLICTS.map((conflict) => (
                  <div
                    key={conflict.id}
                    className="text-xs border-l-3 border-white/30 bg-white/5 rounded p-2 space-y-1.5"
                  >
                    <div className="text-white/90 font-semibold space-y-0.5">
                      {conflict.eventNames.map((name, idx) => (
                        <p key={idx} className="line-clamp-1">
                          {name}
                        </p>
                      ))}
                    </div>
                    <p className="text-white/70">
                      {conflict.day} · {conflict.time}
                    </p>
                    <div className="space-y-0.5 pt-1 border-t border-white/10">
                      {conflict.conflictReasons.map((reason, idx) => (
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
      </aside>
    </div>
  );
}
