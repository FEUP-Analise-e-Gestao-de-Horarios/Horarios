import { useLocation } from "react-router-dom";
import { ROUTES } from "@/routes";
import { buildPath } from "@/utils/routes";
import MainNavMenu, { type MainNavItem } from "@/components/nav/MainNavMenu";

interface DashboardNavbarProps {
  projectId: string;
  isReady: boolean;
}

export default function DashboardNavbar({ projectId, isReady }: DashboardNavbarProps) {
  const dashboardPath = buildPath(ROUTES.DASHBOARD, { projectId });
  // The detail pages (degree, teacher, room, …) share this navbar, so "Dados"
  // is still shown there as the way back up to the dashboard — only on the
  // dashboard's own root page is it the current page and omitted.
  const isOnDashboard = useLocation().pathname === dashboardPath;

  const items: MainNavItem[] = [
    {
      key: "dados",
      label: "Dados",
      to: dashboardPath,
      current: isOnDashboard,
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
    { key: "inicio", label: "Início", to: ROUTES.HOME, primary: true },
  ];

  return (
    <header className="px-6 py-3 bg-[#1e2028] flex items-center gap-2 border-b border-gray-700">
      <MainNavMenu items={items} />
    </header>
  );
}
