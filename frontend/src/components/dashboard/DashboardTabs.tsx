import { useLayoutEffect, useRef, useState } from "react";
import { Search } from "lucide-react";
import DegreesTab from "./tabs/DegreesTab";
import TeachersTab from "./tabs/TeachersTab";
import RoomsTab from "./tabs/RoomsTab";
import { useProjectDegrees, useProjectTeachers, useProjectRooms } from "@/api/hooks/useDashboard";

type Tab = "degrees" | "teachers" | "rooms";

const TABS: { id: Tab; label: string }[] = [
  { id: "degrees", label: "Cursos" },
  { id: "teachers", label: "Docentes" },
  { id: "rooms", label: "Salas" },
];

interface DashboardTabsProps {
  projectId: string;
  pollInterval: number | false;
  processing: boolean;
}

export default function DashboardTabs({ projectId, pollInterval, processing }: DashboardTabsProps) {
  const [activeTab, setActiveTab] = useState<Tab>("degrees");
  const [search, setSearch] = useState("");
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const [indicator, setIndicator] = useState({ left: 0, width: 0 });

  const { data: degreesData } = useProjectDegrees(projectId, pollInterval);
  const { data: teachersData } = useProjectTeachers(projectId, pollInterval);
  const { data: roomsData } = useProjectRooms(projectId, pollInterval);

  const tabPending: Record<Tab, boolean> = {
    degrees: processing && !degreesData?.length,
    teachers: processing && !teachersData?.length,
    rooms: processing && !roomsData?.length,
  };

  useLayoutEffect(() => {
    const idx = TABS.findIndex((t) => t.id === activeTab);
    const el = tabRefs.current[idx];
    if (el) setIndicator({ left: el.offsetLeft, width: el.offsetWidth });
  }, [activeTab]);

  function handleTabChange(tab: Tab) {
    setActiveTab(tab);
    setSearch("");
  }

  return (
    <div className="flex-1 min-h-0 flex flex-col bg-white rounded-lg border border-[#e5e4e7] shadow-[0_2px_8px_rgba(0,0,0,0.06)] overflow-hidden">
      <div className="relative flex items-center border-b border-[#e5e4e7] shrink-0">
        {TABS.map((tab, i) => (
          <button
            key={tab.id}
            ref={(el) => {
              tabRefs.current[i] = el;
            }}
            onClick={() => handleTabChange(tab.id)}
            className={`px-6 py-3.5 text-sm font-semibold transition-colors flex items-center gap-2 ${
              activeTab === tab.id ? "text-[#8c2d19]" : "text-[#6b6375] hover:text-[#08060d]"
            }`}
          >
            {tab.label}
            {tabPending[tab.id] && (
              <span className="relative flex h-1.5 w-1.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75" />
                <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-amber-500" />
              </span>
            )}
          </button>
        ))}

        <div
          className="absolute bottom-0 h-0.5 bg-[#8c2d19] transition-all duration-200 ease-in-out"
          style={{ left: indicator.left, width: indicator.width }}
        />

        <div className="ml-auto px-4">
          <div className="flex items-center gap-2 bg-[#f9f7f4] border border-[#e5e4e7] rounded-md px-3 py-1.5">
            <Search size={13} className="text-[#6b6375] shrink-0" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Pesquisar..."
              className="text-sm bg-transparent outline-none text-[#08060d] placeholder:text-[#6b6375] w-44"
            />
          </div>
        </div>
      </div>

      <div className="flex-1 min-h-0 relative">
        <div className={`h-full ${activeTab === "degrees" ? "" : "hidden"}`}>
          <DegreesTab
            projectId={projectId}
            search={search}
            pollInterval={pollInterval}
            processing={processing}
          />
        </div>
        <div className={`h-full ${activeTab === "teachers" ? "" : "hidden"}`}>
          <TeachersTab
            projectId={projectId}
            search={search}
            pollInterval={pollInterval}
            processing={processing}
          />
        </div>
        <div className={`h-full ${activeTab === "rooms" ? "" : "hidden"}`}>
          <RoomsTab
            projectId={projectId}
            search={search}
            pollInterval={pollInterval}
            processing={processing}
          />
        </div>
      </div>
    </div>
  );
}
