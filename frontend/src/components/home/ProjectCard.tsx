import { useNavigate } from "react-router-dom";
import type { Project } from "@/types/project";

interface ProjectCardProps {
  project: Project;
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
      <div className="w-full px-3.5 py-2.5 flex justify-between items-center box-border">
        <span className="text-[#08060d] font-medium max-w-[150px] break-words text-sm">
          {project.name}
        </span>
        <span className="text-xl cursor-pointer text-[#6b6375] tracking-[2px]">···</span>
      </div>
    </button>
  );
}
