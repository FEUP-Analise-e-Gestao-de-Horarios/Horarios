import { useNavigate } from "react-router-dom";
import { ROUTES } from "@/routes";
import { buildPath } from "@/utils/routes";

interface DashboardNavbarProps {
  projectId: string;
  isReady: boolean;
}

export default function DashboardNavbar({ projectId, isReady }: DashboardNavbarProps) {
  const navigate = useNavigate();

  return (
    <header className="px-6 py-3 bg-[#1e2028] flex items-center gap-2 border-b border-gray-700">
      <button
        onClick={() => void navigate(ROUTES.HOME)}
        className="bg-[#8C2C19] text-white font-semibold px-3.5 py-2 rounded text-sm whitespace-nowrap hover:bg-[#A9361E] transition-colors"
      >
        Início
      </button>
      <button
        onClick={() => void navigate(buildPath(ROUTES.DASHBOARD, { projectId }))}
        className="bg-transparent text-white font-semibold px-3.5 py-2 rounded text-sm whitespace-nowrap border border-gray-600 transition-colors hover:border-gray-400 hover:bg-white/5"
      >
        Dashboard
      </button>
      <button
        disabled={!isReady}
        onClick={() => void navigate(buildPath(ROUTES.SCHEDULE, { projectId }))}
        className="bg-transparent text-white font-semibold px-3.5 py-2 rounded text-sm whitespace-nowrap border border-gray-600 transition-colors enabled:hover:border-gray-400 enabled:hover:bg-white/5 disabled:opacity-40 disabled:cursor-not-allowed"
      >
        Horário
      </button>
    </header>
  );
}
