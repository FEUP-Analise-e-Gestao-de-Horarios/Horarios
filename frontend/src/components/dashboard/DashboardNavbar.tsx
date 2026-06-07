import { Link, useLocation } from "react-router-dom";
import { ROUTES } from "@/routes";
import { buildPath } from "@/utils/routes";

interface DashboardNavbarProps {
  projectId: string;
  isReady: boolean;
}

export default function DashboardNavbar({ projectId, isReady }: DashboardNavbarProps) {
  const dashboardPath = buildPath(ROUTES.DASHBOARD, { projectId });
  const isOnDashboard = useLocation().pathname === dashboardPath;

  return (
    <header className="px-6 py-3 bg-[#1e2028] flex items-center gap-2 border-b border-gray-700">
      <Link
        to={ROUTES.HOME}
        className="bg-[#8C2C19] text-white font-semibold px-3.5 py-2 rounded text-sm whitespace-nowrap hover:bg-[#A9361E] transition-colors"
      >
        Início
      </Link>
      {isOnDashboard ? (
        <button
          disabled
          className="bg-transparent text-white font-semibold px-3.5 py-2 rounded text-sm whitespace-nowrap border border-gray-600 opacity-40 cursor-not-allowed"
        >
          Dados
        </button>
      ) : (
        <Link
          to={dashboardPath}
          className="bg-transparent text-white font-semibold px-3.5 py-2 rounded text-sm whitespace-nowrap border border-gray-600 transition-colors hover:border-gray-400 hover:bg-white/5"
        >
          Dados
        </Link>
      )}
      {isReady ? (
        <Link
          to={buildPath(ROUTES.SCHEDULE, { projectId })}
          className="bg-transparent text-white font-semibold px-3.5 py-2 rounded text-sm whitespace-nowrap border border-gray-600 transition-colors hover:border-gray-400 hover:bg-white/5"
        >
          Horário
        </Link>
      ) : (
        <button
          disabled
          className="bg-transparent text-white font-semibold px-3.5 py-2 rounded text-sm whitespace-nowrap border border-gray-600 opacity-40 cursor-not-allowed"
        >
          Horário
        </button>
      )}
      {isReady ? (
        <Link
          to={buildPath(ROUTES.EXPORT, { projectId })}
          className="bg-transparent text-white font-semibold px-3.5 py-2 rounded text-sm whitespace-nowrap border border-gray-600 transition-colors hover:border-gray-400 hover:bg-white/5"
        >
          Exportar
        </Link>
      ) : (
        <button
          disabled
          className="bg-transparent text-white font-semibold px-3.5 py-2 rounded text-sm whitespace-nowrap border border-gray-600 opacity-40 cursor-not-allowed"
        >
          Exportar
        </button>
      )}
    </header>
  );
}
