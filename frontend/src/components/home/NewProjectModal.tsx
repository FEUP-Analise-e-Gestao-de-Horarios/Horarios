import { useState } from "react";
import { useCreateProject } from "@/api/hooks/useProjects";
import { ApiError } from "@/types/api";

interface NewProjectModalProps {
  onClose: () => void;
}

export default function NewProjectModal({ onClose }: NewProjectModalProps) {
  const [projectName, setProjectName] = useState("");
  const [scheduleLink, setScheduleLink] = useState("");
  const [error, setError] = useState<string | null>(null);
  const createProject = useCreateProject();

  const handleCreate = () => {
    setError(null);
    createProject.mutate(
      { name: projectName, url: scheduleLink },
      {
        onSuccess: () => onClose(),
        onError: (err) => {
          if (err.code === ApiError.PROJECTS_CREATE_DUPLICATED_NAME) {
            setError("Já existe um projeto com esse nome.");
          } else if (err.code === ApiError.INVALID_BODY) {
            setError("Link inválido.");
          } else {
            setError("Ocorreu um erro. Tente novamente.");
          }
        },
      },
    );
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center">
      <button
        type="button"
        onClick={onClose}
        className="absolute inset-0 bg-black/40 border-none cursor-default"
        aria-label="Fechar"
      />
      <div
        role="dialog"
        aria-modal="true"
        className="relative bg-white rounded-lg p-8 w-[460px] flex flex-col gap-4 shadow-[rgba(0,0,0,0.1)_0_10px_15px_-3px,rgba(0,0,0,0.05)_0_4px_6px_-2px]"
      >
        <div className="flex justify-between items-center">
          <h2 className="m-0 text-[#08060d] text-xl">Novo Projeto</h2>
          <button
            type="button"
            onClick={onClose}
            className="cursor-pointer text-xl text-[#6b6375] hover:text-[#08060d] transition-colors bg-transparent border-none p-0"
            aria-label="Fechar"
          >
            ✕
          </button>
        </div>

        <div className="flex flex-col gap-1.5">
          <label htmlFor="project-name" className="text-[#08060d] text-sm">
            Nome:
          </label>
          <input
            id="project-name"
            type="text"
            value={projectName}
            onChange={(e) => setProjectName(e.target.value)}
            className="px-3 py-2.5 rounded border border-[#8c2d19] text-[15px] outline-none bg-white text-[#08060d] focus:ring-1 focus:ring-[rgba(140,45,25,0.5)]"
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <label htmlFor="schedule-link" className="text-[#08060d] text-sm">
            Link:
          </label>
          <input
            id="schedule-link"
            type="text"
            value={scheduleLink}
            onChange={(e) => setScheduleLink(e.target.value)}
            className="px-3 py-2.5 rounded border border-[#8c2d19] text-[15px] outline-none bg-white text-[#08060d] focus:ring-1 focus:ring-[rgba(140,45,25,0.5)]"
          />
        </div>

        {error && <p className="text-red-600 text-sm m-0">{error}</p>}

        <div className="flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-5 py-2 rounded border-none bg-[#6b7280] text-white cursor-pointer text-sm text-center hover:bg-[#555b66] transition-colors"
          >
            Cancelar
          </button>
          <button
            onClick={handleCreate}
            className="px-5 py-2 rounded border-none bg-[#8c2d19] text-white cursor-pointer text-sm text-center font-semibold hover:bg-[#722415] transition-colors"
          >
            Criar
          </button>
        </div>
      </div>
    </div>
  );
}
