import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { useRenameProject, useDeleteProject } from "@/api/hooks/useProjects";
import { ApiError } from "@/types/api";
import type { Project } from "@/types/project/project";
import { ROUTES } from "@/routes";
import { buildPath } from "@/utils/routes";
import { PROJECT_NAME_MAX_LENGTH, validateProjectName } from "@/utils/projectName";
import { Pencil, Trash2, Check, X, Loader2 } from "lucide-react";

interface ProjectCardProps {
  project: Project;
}

function useElapsedSeconds(since: string | null | undefined): number {
  const [seconds, setSeconds] = useState(() =>
    since ? Math.floor((Date.now() - new Date(since).getTime()) / 1000) : 0,
  );

  useEffect(() => {
    if (!since) return;
    const id = setInterval(() => {
      setSeconds(Math.floor((Date.now() - new Date(since).getTime()) / 1000));
    }, 1000);
    return () => clearInterval(id);
  }, [since]);

  return seconds;
}

function formatElapsed(totalSeconds: number): string {
  if (totalSeconds < 60) return `${totalSeconds}s`;
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  if (minutes < 60) return `${minutes}m ${seconds}s`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ${minutes % 60}m ${seconds}s`;
}

function IngestionStatus({ project }: { project: Project }) {
  const elapsed = useElapsedSeconds(project.ingestion_started_at);

  if (project.ingestion_failed_at) {
    return (
      <div className="flex items-center gap-1.5 text-xs text-red-600">
        <span className="inline-block w-2 h-2 rounded-full bg-red-500" />
        Falha ao carregar
      </div>
    );
  }

  if (project.ingestion_finished_at) {
    return (
      <div className="flex items-center gap-1.5 text-xs text-green-700">
        <span className="inline-block w-2 h-2 rounded-full bg-green-500" />
        Pronto
      </div>
    );
  }

  if (project.ingestion_started_at) {
    return (
      <div className="flex items-center gap-1.5 text-xs text-amber-600">
        <Loader2 className="w-3 h-3 animate-spin" />A processar — {formatElapsed(elapsed)}
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

  const [isEditing, setIsEditing] = useState(false);
  const [editName, setEditName] = useState(project.name);
  const [renameError, setRenameError] = useState<string | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const inputRef = useRef<HTMLInputElement>(null);

  const renameProject = useRenameProject();
  const deleteProject = useDeleteProject();
  const isReady = !!project.ingestion_finished_at;
  const isProcessing =
    !!project.ingestion_started_at &&
    !project.ingestion_finished_at &&
    !project.ingestion_failed_at;

  function handleCardClick() {
    if (isReady) {
      if (!project.has_selected_parallel_sessions) {
        void navigate(buildPath(ROUTES.PARALLEL_SESSIONS, { projectId: String(project.id) }));
      } else {
        void navigate(buildPath(ROUTES.SCHEDULE, { projectId: String(project.id) }));
      }
    } else if (isProcessing)
      void navigate(buildPath(ROUTES.DASHBOARD, { projectId: String(project.id) }));
  }

  useEffect(() => {
    if (isEditing) inputRef.current?.focus();
  }, [isEditing]);

  const handleRename = () => {
    if (!editName.trim() || editName === project.name) {
      setIsEditing(false);
      setEditName(project.name);
      return;
    }
    setRenameError(null);
    const nameError = validateProjectName(editName);
    if (nameError) {
      setRenameError(nameError);
      return;
    }
    renameProject.mutate(
      { id: project.id, name: editName },
      {
        onSuccess: () => setIsEditing(false),
        onError: (err) => {
          if (err.code === ApiError.PROJECTS_RENAME_DUPLICATED_NAME) {
            setRenameError("Nome já existe.");
          } else if (err.code === ApiError.INVALID_BODY) {
            setRenameError("Nome inválido.");
          } else {
            setRenameError("Erro ao renomear.");
          }
        },
      },
    );
  };

  const handleDelete = () => {
    setDeleteError(null);
    deleteProject.mutate(project.id, {
      onSuccess: () => setShowDeleteConfirm(false),
      onError: (err) => {
        if (err.code === ApiError.PROJECTS_NOT_FOUND) {
          setDeleteError("Projeto não encontrado.");
        } else {
          setDeleteError("Erro ao apagar. Tente novamente.");
        }
      },
    });
  };

  return (
    <div className="relative w-[220px] h-[220px]">
      {showDeleteConfirm && (
        <div className="absolute inset-0 z-10 bg-white rounded-lg border border-[#e5e4e7] flex flex-col items-center justify-center gap-3 p-5 shadow-[0_4px_12px_rgba(0,0,0,0.12)]">
          <p className="text-[#08060d] text-sm text-center m-0">
            Tens a certeza que queres apagar este projeto?
          </p>
          {deleteError && <p className="text-red-600 text-xs text-center m-0">{deleteError}</p>}
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setShowDeleteConfirm(false)}
              disabled={deleteProject.isPending}
              className="px-4 py-1.5 rounded border-none bg-[#6b7280] text-white cursor-pointer text-sm hover:bg-[#555b66] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Cancelar
            </button>
            <button
              type="button"
              onClick={handleDelete}
              disabled={deleteProject.isPending}
              className="px-4 py-1.5 rounded border-none bg-[#8c2d19] text-white cursor-pointer text-sm font-semibold hover:bg-[#722415] transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5"
            >
              {deleteProject.isPending && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              Apagar
            </button>
          </div>
        </div>
      )}

      <div className="w-full h-full bg-white border border-[#e5e4e7] rounded-lg flex flex-col shadow-[0_2px_8px_rgba(0,0,0,0.08)] overflow-hidden hover:shadow-[0_4px_12px_rgba(0,0,0,0.12)] transition-shadow">
        <button
          type="button"
          disabled={!isReady && !isProcessing}
          onClick={handleCardClick}
          className={`w-full flex-1 flex items-center justify-center bg-[#f9f7f4] rounded-t-lg text-[64px] border-none bg-none ${isReady || isProcessing ? "cursor-pointer" : "cursor-default"}`}
        >
          🗄️
        </button>

        <div className="w-full px-3.5 py-2 flex flex-col gap-1 box-border">
          {isEditing ? (
            <div className="flex flex-col gap-0.5">
              <div className="flex items-center gap-1">
                <input
                  ref={inputRef}
                  type="text"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  maxLength={PROJECT_NAME_MAX_LENGTH}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handleRename();
                    if (e.key === "Escape") {
                      setIsEditing(false);
                      setEditName(project.name);
                    }
                  }}
                  disabled={renameProject.isPending}
                  className="flex-1 text-sm px-1.5 py-0.5 border border-[#8c2d19] rounded outline-none text-[#08060d] min-w-0 focus:ring-1 focus:ring-[rgba(140,45,25,0.5)] disabled:opacity-50 disabled:cursor-not-allowed"
                />
                {renameProject.isPending ? (
                  <Loader2 className="w-4 h-4 animate-spin text-[#6b6375] flex-shrink-0" />
                ) : (
                  <button
                    type="button"
                    onClick={handleRename}
                    className="text-green-600 hover:text-green-800 transition-colors bg-transparent border-none cursor-pointer p-0 flex-shrink-0"
                    title="Guardar"
                  >
                    <Check className="w-4 h-4" />
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => {
                    setIsEditing(false);
                    setEditName(project.name);
                    setRenameError(null);
                  }}
                  disabled={renameProject.isPending}
                  className="text-[#6b6375] hover:text-[#08060d] transition-colors bg-transparent border-none cursor-pointer p-0 flex-shrink-0 disabled:opacity-50 disabled:cursor-not-allowed"
                  title="Cancelar"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
              {renameError && <p className="text-red-600 text-xs m-0">{renameError}</p>}
            </div>
          ) : (
            <div className="flex items-center justify-between group">
              <div className="flex items-center gap-1 min-w-0">
                <span className="text-[#08060d] font-medium text-sm truncate">{project.name}</span>
                <button
                  type="button"
                  onClick={() => setIsEditing(true)}
                  className="opacity-0 group-hover:opacity-100 transition-opacity text-[#6b6375] hover:text-[#08060d] bg-transparent border-none cursor-pointer p-0 flex-shrink-0"
                  title="Renomear"
                >
                  <Pencil className="w-3 h-3" />
                </button>
              </div>
              <button
                type="button"
                onClick={() => setShowDeleteConfirm(true)}
                className="text-[#6b6375] hover:text-[#8c2d19] transition-colors bg-transparent border-none cursor-pointer p-0 flex-shrink-0 ml-1"
                title="Apagar"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          )}
          <IngestionStatus project={project} />
        </div>
      </div>
    </div>
  );
}
