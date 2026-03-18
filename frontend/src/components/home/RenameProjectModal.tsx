import { useState } from "react";
import { api } from "@/api/client";
import type { Project, ProjectsResponse } from "@/types/project";

interface RenameProjectModalProps {
  project: Project;
  onClose: () => void;
  onProjectsUpdated: (projects: Project[]) => void;
}

export default function RenameProjectModal({
  project,
  onClose,
  onProjectsUpdated,
}: RenameProjectModalProps) {
  const [name, setName] = useState(project.name);

  const handleRename = () => {
    api
      .patch(`/api/projects/${project.id}/`, { name })
      .then(() => api.get<ProjectsResponse>("/api/projects/"))
      .then((res) => {
        onProjectsUpdated(res.data.projects);
        onClose();
      })
      .catch(() => {});
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
        className="relative bg-white rounded-lg p-8 w-[400px] flex flex-col gap-4 shadow-[rgba(0,0,0,0.1)_0_10px_15px_-3px,rgba(0,0,0,0.05)_0_4px_6px_-2px]"
      >
        <div className="flex justify-between items-center">
          <h2 className="m-0 text-[#08060d] text-xl">Renomear Projeto</h2>
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
          <label htmlFor="rename-input" className="text-[#08060d] text-sm">
            Novo nome:
          </label>
          <input
            id="rename-input"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="px-3 py-2.5 rounded border border-[#8c2d19] text-[15px] outline-none bg-white text-[#08060d] focus:ring-1 focus:ring-[rgba(140,45,25,0.5)]"
          />
        </div>

        <div className="flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-5 py-2 rounded border-none bg-[#6b7280] text-white cursor-pointer text-sm text-center hover:bg-[#555b66] transition-colors"
          >
            Cancelar
          </button>
          <button
            onClick={handleRename}
            className="px-5 py-2 rounded border-none bg-[#8c2d19] text-white cursor-pointer text-sm text-center font-semibold hover:bg-[#722415] transition-colors"
          >
            Guardar
          </button>
        </div>
      </div>
    </div>
  );
}
