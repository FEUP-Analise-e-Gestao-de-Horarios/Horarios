import { api } from "@/api/client";
import type { Project, ProjectsResponse } from "@/types/project";

interface DeleteProjectModalProps {
  project: Project;
  onClose: () => void;
  onProjectsUpdated: (projects: Project[]) => void;
}

export default function DeleteProjectModal({
  project,
  onClose,
  onProjectsUpdated,
}: DeleteProjectModalProps) {
  const handleDelete = () => {
    api
      .delete(`/api/projects/${project.id}/`)
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
        <h2 className="m-0 text-[#08060d] text-xl">Apagar Projeto</h2>
        <p className="text-[#6b6375] text-sm m-0">
          Tens a certeza que queres apagar este projeto? Esta ação não pode ser revertida.
        </p>

        <div className="flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-5 py-2 rounded border-none bg-[#6b7280] text-white cursor-pointer text-sm text-center hover:bg-[#555b66] transition-colors"
          >
            Cancelar
          </button>
          <button
            onClick={handleDelete}
            className="px-5 py-2 rounded border-none bg-[#8c2d19] text-white cursor-pointer text-sm text-center font-semibold hover:bg-[#722415] transition-colors"
          >
            Apagar
          </button>
        </div>
      </div>
    </div>
  );
}
