import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ROUTES } from "@/routes";
import CursoDropdown from "./CursoDropdown";
import MultiDropdown from "./MultiDropdown";
import { ANOS } from "./data";

interface ScheduleNavbarProps {
  projectId: string | undefined;
  curso: string;
  setCurso: (v: string) => void;
  anos: string[];
  setAnos: (v: string[]) => void;
  ucs: string[];
  setUcs: (v: string[]) => void;
  turmas: string[];
  setTurmas: (v: string[]) => void;
  semanas: string[];
  setSemanas: (v: string[]) => void;
  ucOptions: string[];
  turmaOptions: string[];
  canShowSchedule: boolean;
}

type DropdownId = "curso" | "ano" | "uc" | "turma" | "semana";

export default function ScheduleNavbar({
  projectId,
  curso,
  setCurso,
  anos,
  setAnos,
  ucs,
  setUcs,
  turmas,
  setTurmas,
  semanas,
  setSemanas,
  ucOptions,
  turmaOptions,
  canShowSchedule,
}: ScheduleNavbarProps) {
  const navigate = useNavigate();
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
    setAnos([]);
    setUcs([]);
    setTurmas([]);
    setOpenDropdown(null);
  }

  return (
    <header
      ref={navRef}
      className="px-6 py-3 bg-[#1e2028] flex items-center gap-2 w-full flex-wrap border-b border-gray-700"
    >
      <button
        onClick={() => void navigate(ROUTES.HOME)}
        className="bg-[#8c2d19] text-white font-semibold px-3.5 py-2 rounded text-sm whitespace-nowrap hover:bg-[#a33520] transition-colors"
      >
        Início
      </button>
      <button
        onClick={() => void navigate(ROUTES.DASHBOARD.replace(":projectId", projectId ?? ""))}
        className="bg-transparent text-white font-semibold px-3.5 py-2 rounded text-sm whitespace-nowrap border border-gray-600 hover:border-gray-400 hover:bg-white/5 transition-colors"
      >
        Dashboard
      </button>
      <button className="bg-transparent text-red-400 font-semibold px-3.5 py-2 rounded text-sm whitespace-nowrap border border-red-400 hover:bg-red-400/10 transition-colors">
        ⚠ Ver Conflitos
      </button>
      <button className="bg-transparent text-white font-semibold px-3.5 py-2 rounded text-sm whitespace-nowrap border border-gray-600 hover:border-gray-400 hover:bg-white/5 transition-colors">
        Exportar
      </button>
      <button className="bg-transparent text-white font-semibold px-3.5 py-2 rounded text-sm whitespace-nowrap border border-gray-600 hover:border-gray-400 hover:bg-white/5 transition-colors">
        Editar Aulas em Paralelo
      </button>

      <div className="w-px h-6 bg-gray-600 mx-1" />

      <CursoDropdown
        value={curso}
        onSelect={handleSelectCurso}
        open={openDropdown === "curso"}
        onToggle={() => toggle("curso")}
      />

      <MultiDropdown
        label="Ano"
        options={ANOS}
        selected={anos}
        onSelect={setAnos}
        open={openDropdown === "ano"}
        onToggle={() => toggle("ano")}
        required
      />

      <div className="w-px h-6 bg-gray-600 mx-1" />

      <MultiDropdown
        label="Unidade Curricular"
        options={ucOptions}
        selected={ucs}
        onSelect={setUcs}
        open={openDropdown === "uc"}
        onToggle={() => toggle("uc")}
        disabled={!canShowSchedule}
      />

      <MultiDropdown
        label="Turma"
        options={turmaOptions}
        selected={turmas}
        onSelect={setTurmas}
        open={openDropdown === "turma"}
        onToggle={() => toggle("turma")}
        disabled={!canShowSchedule}
      />

      <MultiDropdown
        label="Semanas"
        options={["S1", "S2", "S3", "S4", "S5"]}
        selected={semanas}
        onSelect={setSemanas}
        open={openDropdown === "semana"}
        onToggle={() => toggle("semana")}
        disabled={!canShowSchedule}
      />

      <button className="bg-transparent text-white font-semibold px-3.5 py-2 rounded text-sm whitespace-nowrap border border-gray-600 hover:border-gray-400 hover:bg-white/5 transition-colors">
        Distribuição
      </button>
      <button className="ml-auto bg-transparent text-white font-semibold px-3.5 py-2 rounded text-sm whitespace-nowrap border border-gray-600 hover:border-gray-400 hover:bg-white/5 transition-colors">
        ▶
      </button>
    </header>
  );
}
