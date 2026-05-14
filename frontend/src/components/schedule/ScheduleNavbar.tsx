import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ROUTES } from "@/routes";
import { buildPath } from "@/utils/routes";
import CursoDropdown from "./CursoDropdown";
import MultiDropdown from "./MultiDropdown";
import TurnoTurmaDropdown, { type TurnoTurmaGroup } from "./TurnoTurmaDropdown";

type CourseOption = {
  value: string;
  label: string;
  description?: string;
};

type DropdownOption = {
  value: string;
  label: string;
  secondaryText?: string;
};

type CourseGroup = {
  label: string;
  options: CourseOption[];
};

interface ScheduleNavbarProps {
  projectId: string;
  curso: string;
  setCurso: (v: string) => void;
  anos: string[];
  setAnos: (v: string[]) => void;
  ucs: string[];
  setUcs: (v: string[]) => void;
  turnos: string[];
  setTurnos: (v: string[]) => void;
  turmas: string[];
  setTurmas: (v: string[]) => void;
  dias: string[];
  setDias: (v: string[]) => void;
  semanas: string[];
  setSemanas: (v: string[]) => void;
  weekOptions: DropdownOption[];
  dayOptions: DropdownOption[];
  ucOptions: string[];
  turnoTurmaGroups: TurnoTurmaGroup[];
  yearOptions: DropdownOption[];
  courseOptions: CourseGroup[];
  onViewConflicts: () => void;
}

type DropdownId = "curso" | "ano" | "uc" | "turnoTurma" | "dia" | "semana";

export default function ScheduleNavbar({
  projectId,
  curso,
  setCurso,
  anos,
  setAnos,
  ucs,
  setUcs,
  turnos,
  setTurnos,
  turmas,
  setTurmas,
  dias,
  setDias,
  semanas,
  setSemanas,
  weekOptions,
  dayOptions,
  ucOptions,
  turnoTurmaGroups,
  yearOptions,
  courseOptions,
  onViewConflicts,
}: ScheduleNavbarProps) {
  const primaryRedButtonClass =
    "bg-[#8C2C19] text-white font-semibold px-3.5 py-2 rounded text-sm whitespace-nowrap hover:bg-[#A9361E] transition-colors";
  const [openDropdown, setOpenDropdown] = useState<DropdownId | null>(null);
  const navRef = useRef<HTMLElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (navRef.current && !navRef.current.contains(e.target as Node)) {
        setOpenDropdown(null);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  function toggle(id: DropdownId) {
    setOpenDropdown((prev) => (prev === id ? null : id));
  }

  function handleSelectCurso(c: string) {
    setCurso(c);
    setOpenDropdown(null);
  }

  return (
    <header
      ref={navRef}
      className="relative z-50 shrink-0 px-6 py-3 bg-[#1e2028] flex items-center gap-2 w-full flex-wrap overflow-visible border-b border-gray-700"
    >
      <Link to={ROUTES.HOME} className={primaryRedButtonClass}>
        Início
      </Link>

      <Link
        to={buildPath(ROUTES.DASHBOARD, { projectId })}
        className="bg-transparent text-white font-semibold px-3.5 py-2 rounded text-sm whitespace-nowrap border border-gray-600 hover:border-gray-400 hover:bg-white/5 transition-colors"
      >
        Dados
      </Link>
      <button className="bg-transparent text-white font-semibold px-3.5 py-2 rounded text-sm whitespace-nowrap border border-gray-600 hover:border-gray-400 hover:bg-white/5 transition-colors">
        Exportar
      </button>

      <div className="border-l border-gray-600 h-5 mx-1" />

      <CursoDropdown
        value={curso}
        onSelect={handleSelectCurso}
        open={openDropdown === "curso"}
        onToggle={() => toggle("curso")}
        options={courseOptions}
      />

      <MultiDropdown
        label="Ano"
        options={yearOptions}
        selected={anos}
        onSelect={setAnos}
        open={openDropdown === "ano"}
        onToggle={() => toggle("ano")}
        disabled={!curso || yearOptions.length === 0}
        showLabel
        singleSelect
        compact
      />

      <MultiDropdown
        label="UCs"
        options={ucOptions.map((uc) => ({ value: uc, label: uc }))}
        selected={ucs}
        onSelect={setUcs}
        open={openDropdown === "uc"}
        onToggle={() => toggle("uc")}
        disabled={!curso}
        showLabel
        fitContent
      />

      <TurnoTurmaDropdown
        groups={turnoTurmaGroups}
        selectedTurnos={turnos}
        selectedTurmas={turmas}
        onSelectTurnos={setTurnos}
        onSelectTurmas={setTurmas}
        open={openDropdown === "turnoTurma"}
        onToggle={() => toggle("turnoTurma")}
        disabled={!curso}
      />

      <MultiDropdown
        label="Dias"
        options={dayOptions}
        selected={dias}
        onSelect={setDias}
        open={openDropdown === "dia"}
        onToggle={() => toggle("dia")}
        disabled={!curso}
        showLabel
        compact
        minSelected={1}
        hideSelectedCountWhenDisabled
      />

      <MultiDropdown
        label="Semanas"
        options={weekOptions}
        selected={semanas}
        onSelect={setSemanas}
        open={openDropdown === "semana"}
        onToggle={() => toggle("semana")}
        disabled={!curso || weekOptions.length === 0}
        showLabel
      />

      <div className="border-l border-gray-600 h-5 mx-1" />

      <button className="bg-transparent text-white font-semibold px-3.5 py-2 rounded text-sm whitespace-nowrap border border-gray-600 hover:border-gray-400 hover:bg-white/5 transition-colors">
        Editar Aulas em Paralelo
      </button>

      <div className="border-l border-gray-600 h-5 mx-1" />

      <button className="bg-transparent text-white font-semibold px-3.5 py-2 rounded text-sm whitespace-nowrap border border-gray-600 hover:border-gray-400 hover:bg-white/5 transition-colors">
        Distribuição
      </button>

      <button
        onClick={onViewConflicts}
        className="bg-transparent text-[#C73F24] font-semibold px-3.5 py-2 rounded text-sm whitespace-nowrap border border-[#C73F24] hover:bg-[#C73F24]/10 transition-colors"
      >
        Ver Conflitos
      </button>
    </header>
  );
}
