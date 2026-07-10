import { Eye, EyeOff } from "lucide-react";
import { Link, useLocation, useSearchParams } from "react-router-dom";
import { ROUTES } from "@/routes";
import { buildPath } from "@/utils/routes";
import { useDashboardConflictHighlights } from "./useDashboardConflictHighlights";

interface DashboardNavbarProps {
  projectId: string;
  isReady: boolean;
}

export default function DashboardNavbar({ projectId, isReady }: DashboardNavbarProps) {
  const dashboardPath = buildPath(ROUTES.DASHBOARD, { projectId });
  const { pathname } = useLocation();
  const isOnDashboard = pathname === dashboardPath;
  const [searchParams] = useSearchParams();
  const isDashboardRoute = pathname === dashboardPath || pathname.startsWith(`${dashboardPath}/`);
  const isExporterContext =
    searchParams.has("conflictSessions") ||
    searchParams.has("conflictWeeks") ||
    searchParams.has("exportSession");
  const { enabled: conflictHighlightsEnabled, toggle: toggleConflictHighlights } =
    useDashboardConflictHighlights(projectId);

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
      {isDashboardRoute && !isExporterContext && (
        <button
          type="button"
          onClick={toggleConflictHighlights}
          aria-pressed={conflictHighlightsEnabled}
          title={
            conflictHighlightsEnabled
              ? "Ocultar destaque de conflitos"
              : "Mostrar destaque de conflitos"
          }
          className={
            "ml-auto flex items-center gap-2 px-3.5 py-2 rounded text-sm font-semibold whitespace-nowrap border transition-colors " +
            (conflictHighlightsEnabled
              ? "border-red-400 bg-red-950/40 text-red-100 hover:bg-red-950/60"
              : "border-gray-600 bg-transparent text-gray-300 hover:border-gray-400 hover:bg-white/5")
          }
        >
          {conflictHighlightsEnabled ? <Eye size={16} /> : <EyeOff size={16} />}
          Conflitos
        </button>
      )}
    </header>
  );
}
