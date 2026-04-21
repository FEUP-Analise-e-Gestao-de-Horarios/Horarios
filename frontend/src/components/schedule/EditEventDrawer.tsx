import {
  ALL_DOCENTES,
  ALL_SALAS,
  DOCENTES_POR_UC,
  SALAS_POR_UC,
  ALL_CONFLICTS,
} from "@/components/schedule/data";
import { useEffect, useMemo, useRef, useState } from "react";

interface EditEventDrawerProps {
  open: boolean;
  onClose: () => void;
  ucOptions: string[];
  turmaOptions: string[];
  preferredUc?: string;
}

function shiftTimeByMinutes(time: string, deltaMinutes: number): string {
  const [hours, minutes] = time.split(":").map(Number);
  if (hours === undefined || minutes === undefined || Number.isNaN(hours) || Number.isNaN(minutes))
    return time;

  const totalMinutes = Math.max(0, Math.min(23 * 60 + 59, hours * 60 + minutes + deltaMinutes));
  const nextHours = String(Math.floor(totalMinutes / 60)).padStart(2, "0");
  const nextMinutes = String(totalMinutes % 60).padStart(2, "0");
  return `${nextHours}:${nextMinutes}`;
}

function normalizeTimeValue(value: string, fallback: string): string {
  const cleaned = value.trim();
  const match = cleaned.match(/^(\d{1,2}):?(\d{2})$/);
  if (!match) return fallback;

  const hours = Number(match[1]);
  const minutes = Number(match[2]);
  if (Number.isNaN(hours) || Number.isNaN(minutes)) return fallback;
  if (hours < 0 || hours > 23 || minutes < 0 || minutes > 59) return fallback;

  return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}`;
}

function toggleSelection(current: string[], itemId: string): string[] {
  return current.includes(itemId)
    ? current.filter((selectedId) => selectedId !== itemId)
    : [...current, itemId];
}

export default function EditEventDrawer({
  open,
  onClose,
  ucOptions,
  turmaOptions,
  preferredUc,
}: EditEventDrawerProps) {
  const [selectedUcOverride, setSelectedUcOverride] = useState("");
  const [selectedDocenteOverride, setSelectedDocenteOverride] = useState<string>("");
  const [selectedSalaOverride, setSelectedSalaOverride] = useState<string>("");
  const [selectedTurmasOverride, setSelectedTurmasOverride] = useState<string[]>([]);
  const [startTime, setStartTime] = useState("10:30");
  const [endTime, setEndTime] = useState("12:30");
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

    document.addEventListener("mousedown", handleOutsideClick);
    return () => document.removeEventListener("mousedown", handleOutsideClick);
  }, []);

  const selectedUc = useMemo(() => {
    if (selectedUcOverride && ucOptions.includes(selectedUcOverride)) return selectedUcOverride;
    if (preferredUc && ucOptions.includes(preferredUc)) return preferredUc;
    return ucOptions[0] ?? "";
  }, [preferredUc, selectedUcOverride, ucOptions]);

  const preferredDocentes = useMemo(() => {
    const preferredIds = new Set(DOCENTES_POR_UC[selectedUc] ?? []);
    return ALL_DOCENTES.filter((docente) => preferredIds.has(docente.id));
  }, [selectedUc]);

  const otherDocentes = useMemo(() => {
    const preferredIds = new Set(DOCENTES_POR_UC[selectedUc] ?? []);
    return ALL_DOCENTES.filter((docente) => !preferredIds.has(docente.id));
  }, [selectedUc]);

  const { preferredSalas, otherSalas } = useMemo(() => {
    const preferredRoomIds = SALAS_POR_UC[selectedUc] ?? [];
    const roomById = new Map(ALL_SALAS.map((room) => [room.id, room]));
    const preferredTypologies = new Set(
      preferredRoomIds
        .map((roomId) => roomById.get(roomId)?.typology)
        .filter((typology): typology is string => Boolean(typology)),
    );

    const preferred = ALL_SALAS.filter((room) => preferredTypologies.has(room.typology));
    const others = ALL_SALAS.filter((room) => !preferredTypologies.has(room.typology));
    return { preferredSalas: preferred, otherSalas: others };
  }, [selectedUc]);

  const orderedDocentes = useMemo(
    () => [...preferredDocentes, ...otherDocentes],
    [otherDocentes, preferredDocentes],
  );

  const orderedSalas = useMemo(
    () => [...preferredSalas, ...otherSalas],
    [otherSalas, preferredSalas],
  );

  const filteredPreferredDocentes = useMemo(() => {
    const query = docentesSearch.toLowerCase().trim();
    if (!query) return preferredDocentes;
    return preferredDocentes.filter((docente) => docente.label.toLowerCase().includes(query));
  }, [docentesSearch, preferredDocentes]);

  const filteredOtherDocentes = useMemo(() => {
    const query = docentesSearch.toLowerCase().trim();
    if (!query) return otherDocentes;
    return otherDocentes.filter((docente) => docente.label.toLowerCase().includes(query));
  }, [docentesSearch, otherDocentes]);

  const filteredPreferredSalas = useMemo(() => {
    const query = salasSearch.toLowerCase().trim();
    if (!query) return preferredSalas;
    return preferredSalas.filter((room) =>
      `${room.id} ${room.typology}`.toLowerCase().includes(query),
    );
  }, [preferredSalas, salasSearch]);

  const filteredOtherSalas = useMemo(() => {
    const query = salasSearch.toLowerCase().trim();
    if (!query) return otherSalas;
    return otherSalas.filter((room) => `${room.id} ${room.typology}`.toLowerCase().includes(query));
  }, [otherSalas, salasSearch]);

  const filteredTurmas = useMemo(() => {
    const query = turmasSearch.toLowerCase().trim();
    if (!query) return turmaOptions;
    return turmaOptions.filter((turma) => turma.toLowerCase().includes(query));
  }, [turmaOptions, turmasSearch]);

  const effectiveSelectedDocente = useMemo(() => {
    if (selectedDocenteOverride && orderedDocentes.some((d) => d.id === selectedDocenteOverride)) {
      return selectedDocenteOverride;
    }
    return orderedDocentes[0]?.id ?? "";
  }, [orderedDocentes, selectedDocenteOverride]);

  const effectiveSelectedSala = useMemo(() => {
    if (selectedSalaOverride && orderedSalas.some((r) => r.id === selectedSalaOverride)) {
      return selectedSalaOverride;
    }
    return orderedSalas[0]?.id ?? "";
  }, [orderedSalas, selectedSalaOverride]);

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
          "absolute right-0 top-0 h-full w-[min(92vw,430px)] bg-[#1d2128] text-white border-l border-white/15 shadow-[-8px_0_24px_rgba(0,0,0,0.45)] transition-transform overflow-y-auto",
          open ? "translate-x-0" : "translate-x-full",
        ].join(" ")}
      >
        <div className="sticky top-0 bg-[#1d2128] border-b border-white/10 px-5 py-4 flex items-center justify-between">
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

          <div className="flex items-end gap-3">
            <label className="block text-sm flex-1 min-w-0">
              <span className="mb-1.5 block text-white/90">Hora Início</span>
              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  onClick={() => setStartTime((current) => shiftTimeByMinutes(current, -30))}
                  className="h-10 w-10 rounded border border-white/20 bg-[#2a303a] text-white/80 hover:text-white"
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
                  className="w-full min-w-0 bg-[#2a303a] border border-white/20 rounded px-2.5 py-2 text-white"
                />
                <button
                  type="button"
                  onClick={() => setStartTime((current) => shiftTimeByMinutes(current, 30))}
                  className="h-10 w-10 rounded border border-white/20 bg-[#2a303a] text-white/80 hover:text-white"
                  aria-label="Aumentar hora de inicio em 30 minutos"
                >
                  +
                </button>
              </div>
            </label>
            <label className="block text-sm flex-1 min-w-0">
              <span className="mb-1.5 block text-white/90">Hora Fim</span>
              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  onClick={() => setEndTime((current) => shiftTimeByMinutes(current, -30))}
                  className="h-10 w-10 rounded border border-white/20 bg-[#2a303a] text-white/80 hover:text-white"
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
                  className="w-full min-w-0 bg-[#2a303a] border border-white/20 rounded px-2.5 py-2 text-white"
                />
                <button
                  type="button"
                  onClick={() => setEndTime((current) => shiftTimeByMinutes(current, 30))}
                  className="h-10 w-10 rounded border border-white/20 bg-[#2a303a] text-white/80 hover:text-white"
                  aria-label="Aumentar hora de fim em 30 minutos"
                >
                  +
                </button>
              </div>
            </label>
          </div>

          <label className="block text-sm">
            <span className="mb-1.5 block text-white/90">Dia</span>
            <select className="w-full bg-[#2a303a] border border-white/20 rounded px-2.5 py-2">
              <option>Segunda-Feira</option>
              <option>Terça-Feira</option>
              <option>Quarta-Feira</option>
              <option>Quinta-Feira</option>
              <option>Sexta-Feira</option>
            </select>
          </label>

          <div className="space-y-4" ref={dropdownAreaRef}>
            <div className="relative text-sm">
              <span className="mb-1.5 block text-white/90">Docentes</span>
              <button
                onClick={() => setOpenDropdown((prev) => (prev === "docentes" ? null : "docentes"))}
                className="w-full bg-[#2a303a] border border-white/20 rounded px-2.5 py-2 text-left flex items-center justify-between"
              >
                <span>
                  {orderedDocentes.find((d) => d.id === effectiveSelectedDocente)?.label ||
                    "Selecionar..."}
                </span>
                <span className="text-white/70">▾</span>
              </button>

              {openDropdown === "docentes" && (
                <div className="absolute z-30 mt-2 w-full bg-[#222834] border border-white/20 rounded shadow-[0_10px_20px_rgba(0,0,0,0.45)] p-2">
                  <input
                    value={docentesSearch}
                    onChange={(event) => setDocentesSearch(event.target.value)}
                    placeholder="Search..."
                    className="mb-2 w-full bg-[#2a303a] border border-white/20 rounded px-2.5 py-2"
                  />
                  <div className="max-h-52 overflow-y-auto space-y-1">
                    {filteredPreferredDocentes.length > 0 && (
                      <p className="px-2 py-1 text-xs uppercase tracking-wide text-white/60">
                        Docentes da UC
                      </p>
                    )}
                    {filteredPreferredDocentes.map((docente) => (
                      <button
                        key={docente.id}
                        onClick={() => {
                          setSelectedDocenteOverride(docente.id);
                          setOpenDropdown(null);
                        }}
                        className={`w-full px-2 py-1.5 text-left rounded ${
                          effectiveSelectedDocente === docente.id
                            ? "bg-red-900/40 text-white font-semibold"
                            : "text-white hover:bg-white/10"
                        }`}
                      >
                        {docente.label}
                      </button>
                    ))}

                    {filteredOtherDocentes.length > 0 && (
                      <p className="px-2 py-1 text-xs uppercase tracking-wide text-white/60">
                        Outros Docentes
                      </p>
                    )}
                    {filteredOtherDocentes.map((docente) => (
                      <button
                        key={docente.id}
                        onClick={() => {
                          setSelectedDocenteOverride(docente.id);
                          setOpenDropdown(null);
                        }}
                        className={`w-full px-2 py-1.5 text-left rounded ${
                          effectiveSelectedDocente === docente.id
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

            <div className="relative text-sm">
              <span className="mb-1.5 block text-white/90">Salas - Tipologia</span>
              <button
                onClick={() => setOpenDropdown((prev) => (prev === "salas" ? null : "salas"))}
                className="w-full bg-[#2a303a] border border-white/20 rounded px-2.5 py-2 text-left flex items-center justify-between"
              >
                <span>
                  {orderedSalas.find((r) => r.id === effectiveSelectedSala)
                    ? `${orderedSalas.find((r) => r.id === effectiveSelectedSala)?.id} - ${orderedSalas.find((r) => r.id === effectiveSelectedSala)?.typology}`
                    : "Selecionar..."}
                </span>
                <span className="text-white/70">▾</span>
              </button>

              {openDropdown === "salas" && (
                <div className="absolute z-30 mt-2 w-full bg-[#222834] border border-white/20 rounded shadow-[0_10px_20px_rgba(0,0,0,0.45)] p-2">
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
                          setSelectedSalaOverride(room.id);
                          setOpenDropdown(null);
                        }}
                        className={`w-full px-2 py-1.5 text-left rounded ${
                          effectiveSelectedSala === room.id
                            ? "bg-red-900/40 text-white font-semibold"
                            : "text-white hover:bg-white/10"
                        }`}
                      >
                        {room.id} - {room.typology}
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
                          setSelectedSalaOverride(room.id);
                          setOpenDropdown(null);
                        }}
                        className={`w-full px-2 py-1.5 text-left rounded ${
                          effectiveSelectedSala === room.id
                            ? "bg-red-900/40 text-white font-semibold"
                            : "text-white hover:bg-white/10"
                        }`}
                      >
                        {room.id} - {room.typology}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="relative text-sm">
              <span className="mb-1.5 block text-white/90">Turmas</span>
              <button
                onClick={() => setOpenDropdown((prev) => (prev === "turmas" ? null : "turmas"))}
                className="w-full bg-[#2a303a] border border-white/20 rounded px-2.5 py-2 text-left flex items-center justify-between"
              >
                <span>Turmas ({effectiveSelectedTurmas.length})</span>
                <span className="text-white/70">▾</span>
              </button>

              {openDropdown === "turmas" && (
                <div className="absolute z-30 mt-2 w-full bg-[#222834] border border-white/20 rounded shadow-[0_10px_20px_rgba(0,0,0,0.45)] p-2">
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
                          setSelectedTurmasOverride(toggleSelection(effectiveSelectedTurmas, turma))
                        }
                        className="w-full px-2 py-1.5 text-left text-white hover:bg-white/10 rounded flex items-start gap-2"
                      >
                        <span
                          className={`mt-0.5 ${
                            effectiveSelectedTurmas.includes(turma) ? "text-red-400" : "text-white"
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

          <div className="pt-4 border-t border-white/20">
            <h3 className="text-white/90 font-semibold mb-3">Conflitos Detectados</h3>
            {ALL_CONFLICTS.length === 0 ? (
              <p className="text-white/60 text-sm">Nenhum conflito</p>
            ) : (
              <div className="space-y-2 max-h-64 overflow-y-auto">
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

          <button className="w-full bg-[#8c2d19] text-white font-semibold rounded py-2.5 hover:brightness-110 transition mt-4">
            Submit
          </button>
        </div>
      </aside>
    </div>
  );
}
