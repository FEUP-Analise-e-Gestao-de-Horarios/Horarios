import { useNavigate } from "react-router-dom";
import type { Project } from "@/types/project";

interface ProjectCardProps {
  project: Project;
}

function getElapsedTime(since: string): string {
  const diff = Date.now() - new Date(since).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "< 1 min";
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ${minutes % 60}m`;
}

function IngestionStatus({ project }: { project: Project }) {
  if (project.failed_ingestion_at) {
    return (
      <div className="flex items-center gap-1.5 text-xs text-red-600">
        <span className="inline-block w-2 h-2 rounded-full bg-red-500" />
        Falha ao carregar
      </div>
    );
  }

  if (project.finished_ingestion_at) {
    return (
      <div className="flex items-center gap-1.5 text-xs text-green-700">
        <span className="inline-block w-2 h-2 rounded-full bg-green-500" />
        Pronto
      </div>
    );
  }

  const startedAt = project.started_ingestion_at;
  if (startedAt) {
    const elapsed = getElapsedTime(startedAt);
    return (
      <div className="flex items-center gap-1.5 text-xs text-amber-600">
        <span className="inline-block w-2 h-2 rounded-full bg-amber-500 animate-pulse" />A processar
        — {elapsed}
      </div>
    );
  }

  return (
    <div className="flex items-center gap-1.5 text-xs text-gray-500">
      <span className="inline-block w-2 h-2 rounded-full bg-gray-400" />
      Pendente
    </div>
  );
}

export default function ProjectCard({ project }: ProjectCardProps) {
  const navigate = useNavigate();
  const isReady = !!project.finished_ingestion_at;

  return (
    <button
      type="button"
      disabled={!isReady}
      onClick={() => void navigate(`/editturnos/${project.id}`)}
      className={`w-[220px] h-[220px] bg-white border border-[#e5e4e7] rounded-lg flex flex-col items-center justify-center shadow-[0_2px_8px_rgba(0,0,0,0.08)] overflow-hidden p-0 text-left ${isReady ? "cursor-pointer hover:shadow-[0_4px_12px_rgba(0,0,0,0.12)] transition-shadow" : "cursor-default"}`}
    >
      <div className="w-full flex-1 flex items-center justify-center bg-[#f9f7f4] rounded-t-lg text-[64px]">
        🗄️
      </div>
      <div className="w-full px-3.5 py-2 flex flex-col gap-1 box-border">
        <div className="flex justify-between items-center">
          <span className="text-[#08060d] font-medium max-w-[150px] break-words text-sm">
            {project.name}
          </span>
          <span className="text-xl cursor-pointer text-[#6b6375] tracking-[2px]">···</span>
        </div>
        <IngestionStatus project={project} />
      </div>
    </button>
  );
}
