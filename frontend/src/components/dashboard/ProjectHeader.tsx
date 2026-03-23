import type { Project } from "@/types/project";

interface ProjectHeaderProps {
  project: Project;
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("pt-PT", {
    day: "2-digit",
    month: "long",
    year: "numeric",
  });
}

function formatDuration(startIso: string, endIso: string) {
  const ms = new Date(endIso).getTime() - new Date(startIso).getTime();
  const totalSeconds = Math.round(ms / 1000);
  if (totalSeconds < 60) return `${totalSeconds}s`;
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return seconds > 0 ? `${minutes}m ${seconds}s` : `${minutes}m`;
}

function IngestionBadge({ project }: { project: Project }) {
  if (project.ingestion_failed_at) {
    return (
      <span className="inline-flex items-center gap-1.5 text-xs font-medium text-red-700 bg-red-50 border border-red-200 rounded-full px-2.5 py-1">
        <span className="w-1.5 h-1.5 rounded-full bg-red-500" />
        Falha ao carregar
      </span>
    );
  }
  if (project.ingestion_finished_at) {
    return (
      <span className="inline-flex items-center gap-1.5 text-xs font-medium text-green-700 bg-green-50 border border-green-200 rounded-full px-2.5 py-1">
        <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
        Pronto
      </span>
    );
  }
  if (project.ingestion_started_at) {
    return (
      <span className="inline-flex items-center gap-1.5 text-xs font-medium text-amber-700 bg-amber-50 border border-amber-200 rounded-full px-2.5 py-1">
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75" />
          <span className="relative inline-flex h-2 w-2 rounded-full bg-amber-500" />
        </span>
        A processar
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 text-xs font-medium text-gray-600 bg-gray-100 border border-gray-200 rounded-full px-2.5 py-1">
      <span className="w-1.5 h-1.5 rounded-full bg-gray-400" />
      Pendente
    </span>
  );
}

export default function ProjectHeader({ project }: ProjectHeaderProps) {
  return (
    <div className="bg-white rounded-lg border border-[#e5e4e7] shadow-[0_2px_8px_rgba(0,0,0,0.06)] p-6">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-2xl font-bold text-[#08060d] truncate">{project.name}</h1>
          {project.url &&
            (() => {
              try {
                new URL(project.url);
                return (
                  <a
                    href={project.url}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-1 block text-sm text-[#6b6375] truncate hover:text-[#08060d] hover:underline transition-colors"
                  >
                    {project.url}
                  </a>
                );
              } catch {
                return <p className="mt-1 text-sm text-[#6b6375] truncate">{project.url}</p>;
              }
            })()}
        </div>
        <IngestionBadge project={project} />
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-y-1 text-sm text-[#6b6375]">
        <span>Criado a {formatDate(project.created_at)}</span>
        <span className="mx-3 text-[#6b6375]">·</span>
        <span>Atualizado a {formatDate(project.updated_at)}</span>
        {project.ingestion_started_at && project.ingestion_finished_at && (
          <>
            <span className="mx-3 text-[#6b6375]">·</span>
            <span>
              Carregamento em{" "}
              {formatDuration(project.ingestion_started_at, project.ingestion_finished_at)}
            </span>
          </>
        )}
        {project.ingestion_started_at && project.ingestion_failed_at && (
          <>
            <span className="mx-3 text-[#6b6375]">·</span>
            <span>
              Falhou ao fim de{" "}
              {formatDuration(project.ingestion_started_at, project.ingestion_failed_at)}
            </span>
          </>
        )}
      </div>
    </div>
  );
}
