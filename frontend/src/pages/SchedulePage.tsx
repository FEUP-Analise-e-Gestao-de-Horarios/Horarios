import { useState } from "react";
import { useParams } from "react-router-dom";
import ScheduleNavbar from "@/components/schedule/ScheduleNavbar";
import { UCS_POR_CURSO, TURMAS_POR_UC } from "@/components/schedule/data";

export default function SchedulePage() {
  const { projectId } = useParams<{ projectId: string }>();

  const [curso, setCurso] = useState("");
  const [anos, setAnos] = useState<string[]>([]);
  const [ucs, setUcs] = useState<string[]>([]);
  const [turmas, setTurmas] = useState<string[]>([]);
  const [semanas, setSemanas] = useState<string[]>([]);

  const canShowSchedule = curso !== "" && anos.length > 0;

  const ucOptions = UCS_POR_CURSO[curso] ?? [];

  const turmaOptions =
    ucs.length > 0
      ? ucs.flatMap((uc) => TURMAS_POR_UC[uc] ?? []).filter((v, i, a) => a.indexOf(v) === i)
      : Object.values(TURMAS_POR_UC)
          .flat()
          .filter((v, i, a) => a.indexOf(v) === i);

  return (
    <div className="min-h-screen bg-[#f0eeeb]">
      <ScheduleNavbar
        projectId={projectId}
        curso={curso}
        setCurso={setCurso}
        anos={anos}
        setAnos={setAnos}
        ucs={ucs}
        setUcs={setUcs}
        turmas={turmas}
        setTurmas={setTurmas}
        semanas={semanas}
        setSemanas={setSemanas}
        ucOptions={ucOptions}
        turmaOptions={turmaOptions}
        canShowSchedule={canShowSchedule}
      />

      <div className="flex items-center justify-center h-[calc(100vh-60px)] text-gray-500 text-lg">
        {canShowSchedule
          ? `Grelha de horário — projeto ${projectId} (a fazer)`
          : "Seleciona Curso e Ano para ver o horário"}
      </div>
    </div>
  );
}
