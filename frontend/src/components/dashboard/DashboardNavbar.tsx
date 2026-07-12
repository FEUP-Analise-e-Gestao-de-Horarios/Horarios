import { Eye, EyeOff } from "lucide-react";
import { useLocation, useSearchParams } from "react-router-dom";
import { ROUTES } from "@/routes";
import { buildPath } from "@/utils/routes";
import MainNavMenu, { type MainNavItem } from "@/components/nav/MainNavMenu";
import { useDashboardConflictHighlights } from "./useDashboardConflictHighlights";

interface DashboardNavbarProps {
  projectId: string;
  isReady: boolean;
}

export default function DashboardNavbar({ projectId, isReady }: DashboardNavbarProps) {
  const dashboardPath = buildPath(ROUTES.DASHBOARD, { projectId });
  const exportPath = buildPath(ROUTES.EXPORT, { projectId });
  const { pathname } = useLocation();
  // The detail pages (degree, teacher, room, …) share this navbar, so "Dados"
  // is the way back up to the dashboard from them — but on the dashboard itself
  // it leads nowhere and is only the dropdown handle.
  const isOnDashboard = pathname === dashboardPath;
  // The exporter reuses this navbar, so the trigger has to name whichever of
  // the two pages we are actually on.
  const isOnExporter = pathname === exportPath;
  const isDashboardRoute = pathname === dashboardPath || pathname.startsWith(`${dashboardPath}/`);
  const [searchParams] = useSearchParams();
  const isExporterContext =
    searchParams.has("conflictSessions") ||
    searchParams.has("conflictWeeks") ||
    searchParams.has("exportSession");
  const { enabled: conflictHighlightsEnabled, toggle: toggleConflictHighlights } =
    useDashboardConflictHighlights(projectId);

  const items: MainNavItem[] = [
    {
      key: "dados",
      label: "Dados",
      to: isOnDashboard ? undefined : dashboardPath,
      current: !isOnExporter,
    },
    {
      key: "horario",
      label: "Horário",
      to: buildPath(ROUTES.SCHEDULE, { projectId }),
      disabled: !isReady,
      disabledTitle: "Horário ainda não disponível",
    },
    {
      key: "paralelas",
      label: "Aulas em Paralelo",
      to: buildPath(ROUTES.PARALLEL_SESSIONS, { projectId }),
      disabled: !isReady,
      disabledTitle: "Aulas em paralelo ainda não disponíveis",
    },
    {
      key: "exportar",
      label: "Exportar",
      to: isOnExporter ? undefined : exportPath,
      current: isOnExporter,
      disabled: !isReady,
      disabledTitle: "Exportação ainda não disponível",
    },
    { key: "inicio", label: "Início", to: ROUTES.HOME },
  ];

  return (
    <header className="px-6 py-3 bg-[#1e2028] flex items-center gap-2 border-b border-gray-700">
      <MainNavMenu items={items} />
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
