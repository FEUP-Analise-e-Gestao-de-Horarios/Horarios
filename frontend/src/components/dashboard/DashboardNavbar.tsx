import { ROUTES } from "@/routes";
import { buildPath } from "@/utils/routes";
import MainNavMenu, { type MainNavItem } from "@/components/nav/MainNavMenu";

interface DashboardNavbarProps {
  projectId: string;
  isReady: boolean;
}

export default function DashboardNavbar({ projectId, isReady }: DashboardNavbarProps) {
  const items: MainNavItem[] = [
    {
      key: "dados",
      label: "Dados",
      to: buildPath(ROUTES.DASHBOARD, { projectId }),
      current: true,
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
    { key: "inicio", label: "Início", to: ROUTES.HOME },
  ];

  return (
    <header className="px-6 py-3 bg-[#1e2028] flex items-center gap-2 border-b border-gray-700">
      <MainNavMenu items={items} />
    </header>
  );
}
