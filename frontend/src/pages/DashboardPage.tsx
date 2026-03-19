import { useState } from "react";
import { useNavigate } from "react-router-dom";

interface Project {
  id: number;
  nome: string;
  finished: boolean;
}

export default function DashboardPage() {
  const navigate = useNavigate();
  const [showNewProject, setShowNewProject] = useState(false);
  const [projectName, setProjectName] = useState("");
  const [scheduleLink, setScheduleLink] = useState("");

  const projects: Project[] = [];

  return (
    <div className="min-h-svh bg-[#f0eeeb] font-[system-ui,'Segoe_UI',Roboto,sans-serif]">
      {/* Navbar */}
      <header className="px-6 py-3 bg-[#1e2028] flex items-center justify-between w-full box-border">
        <div className="flex gap-2">
          <button
            onClick={() => navigate(0)}
            className="bg-[#8c2d19] text-white font-semibold px-3.5 py-2 rounded border-none cursor-pointer text-sm hover:bg-[#722415] transition-colors"
          >
            Início
          </button>
          <button className="bg-transparent text-white font-semibold px-3.5 py-2 rounded border border-[#8c2d19] cursor-pointer text-sm hover:bg-[#8c2d19] transition-colors">
            Grupos
          </button>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => navigate("/react-change-password")}
            className="bg-[#8c2d19] text-white font-semibold px-3.5 py-2 rounded border-none cursor-pointer text-sm hover:bg-[#722415] transition-colors"
          >
            Mudar palavra-passe
          </button>
          <button
            onClick={() => navigate("/react-login")}
            className="bg-[#8c2d19] text-white font-semibold px-3.5 py-2 rounded border-none cursor-pointer text-sm hover:bg-[#722415] transition-colors"
          >
            Terminar sessão
          </button>
        </div>
      </header>

      {/* Content */}
      <div className="flex flex-wrap p-6 pt-8 gap-4">
        {/* New Project Card */}
        <div
          className="w-[220px] h-[220px] bg-white border border-[#e5e4e7] rounded-lg flex flex-col items-center justify-center cursor-pointer shadow-[0_2px_8px_rgba(0,0,0,0.08)] overflow-hidden hover:shadow-[0_4px_12px_rgba(0,0,0,0.12)] transition-shadow"
          onClick={() => setShowNewProject(true)}
        >
          <span className="text-[90px] text-[#8c2d19] leading-none">+</span>
          <span className="text-[#08060d] font-medium mt-2">Novo Projeto</span>
        </div>

        {/* Project Cards */}
        {projects.map((project) => (
          <div
            key={project.id}
            className={`w-[220px] h-[220px] bg-white border border-[#e5e4e7] rounded-lg flex flex-col items-center justify-center shadow-[0_2px_8px_rgba(0,0,0,0.08)] overflow-hidden ${project.finished ? "cursor-pointer hover:shadow-[0_4px_12px_rgba(0,0,0,0.12)] transition-shadow" : "cursor-default"}`}
            onClick={() => project.finished && navigate(`/editturnos/${project.id}`)}
          >
            <div className="w-full flex-1 flex items-center justify-center bg-[#f9f7f4] rounded-t-lg text-[64px]">
              🗄️
            </div>
            <div className="w-full px-3.5 py-2.5 flex justify-between items-center box-border">
              <span className="text-[#08060d] font-medium max-w-[150px] break-words text-sm">
                {project.nome}
              </span>
              <span className="text-xl cursor-pointer text-[#6b6375] tracking-[2px]">···</span>
            </div>
          </div>
        ))}
      </div>

      {/* New Project Popup */}
      {showNewProject && (
        <div
          onClick={() => setShowNewProject(false)}
          className="fixed inset-0 bg-black/40 flex items-center justify-center z-[100]"
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="bg-white rounded-lg p-8 w-[460px] flex flex-col gap-4 shadow-[rgba(0,0,0,0.1)_0_10px_15px_-3px,rgba(0,0,0,0.05)_0_4px_6px_-2px]"
          >
            <div className="flex justify-between items-center">
              <h2 className="m-0 text-[#08060d] text-xl">Novo Projeto</h2>
              <span
                onClick={() => setShowNewProject(false)}
                className="cursor-pointer text-xl text-[#6b6375] hover:text-[#08060d] transition-colors"
              >
                ✕
              </span>
            </div>

            <div className="flex flex-col gap-1.5">
              <label htmlFor="project-name" className="text-[#08060d] text-sm">
                Nome do Projeto:
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
                Link do Horário:
              </label>
              <input
                id="schedule-link"
                type="text"
                value={scheduleLink}
                onChange={(e) => setScheduleLink(e.target.value)}
                className="px-3 py-2.5 rounded border border-[#8c2d19] text-[15px] outline-none bg-white text-[#08060d] focus:ring-1 focus:ring-[rgba(140,45,25,0.5)]"
              />
            </div>

            <div className="flex justify-end gap-2">
              <button
                onClick={() => setShowNewProject(false)}
                className="px-5 py-2 rounded border-none bg-[#6b7280] text-white cursor-pointer text-sm hover:bg-[#555b66] transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={() => {
                  // TODO: ligar à API
                  setShowNewProject(false);
                  setProjectName("");
                  setScheduleLink("");
                }}
                className="px-5 py-2 rounded border-none bg-[#8c2d19] text-white cursor-pointer text-sm font-semibold hover:bg-[#722415] transition-colors"
              >
                Criar Projeto
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
