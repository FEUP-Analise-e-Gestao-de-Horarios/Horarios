import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { useProject, useProjectDegree } from "@/api/hooks/useDashboard";
import { ROUTES } from "@/routes";
import DashboardNavbar from "@/components/dashboard/DashboardNavbar";

export default function DegreeDetailPage() {
  const { projectId, degreeId } = useParams<{ projectId: string; degreeId: string }>();
  const pid = projectId ?? "";
  const did = degreeId ?? "";
  const navigate = useNavigate();

  const project = useProject(pid);
  const { data, isLoading, isError } = useProjectDegree(pid, did);

  return (
    <div className="h-screen flex flex-col bg-[#f0eeeb]">
      <DashboardNavbar projectId={pid} isReady={!!project.data?.ingestion_finished_at} />

      <div className="flex-1 overflow-auto">
        <div className="max-w-7xl mx-auto px-6 pt-6 pb-6 flex flex-col gap-5">
          <button
            onClick={() => void navigate(ROUTES.DASHBOARD.replace(":projectId", pid))}
            className="self-start inline-flex items-center gap-1.5 text-sm text-[#6b6375] hover:text-[#08060d] transition-colors"
          >
            <ArrowLeft size={14} />
            Voltar ao dashboard
          </button>

          {isLoading ? (
            <div className="bg-white rounded-lg border border-[#e5e4e7] shadow-[0_2px_8px_rgba(0,0,0,0.06)] p-6 h-32 animate-pulse" />
          ) : isError || !data ? (
            <div className="bg-white rounded-lg border border-[#e5e4e7] shadow-[0_2px_8px_rgba(0,0,0,0.06)] p-6 text-sm text-red-600">
              Erro ao carregar curso.
            </div>
          ) : (
            <>
              <div className="bg-white rounded-lg border border-[#e5e4e7] shadow-[0_2px_8px_rgba(0,0,0,0.06)] p-6">
                <div className="text-xs font-semibold uppercase tracking-wider text-[#6b6375]">
                  {data.acronym}
                </div>
                <h1 className="mt-1 text-2xl font-bold text-[#08060d]">{data.name}</h1>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <StatCard label="Anos" value={data.years} />
                <StatCard label="UCs" value={data.subjects} />
                <StatCard label="Turmas" value={data.classes} />
                <StatCard label="Aulas" value={data.sessions} />
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-white rounded-lg border border-[#e5e4e7] shadow-[0_2px_8px_rgba(0,0,0,0.06)] p-4">
      <div className="text-xs font-semibold uppercase tracking-wider text-[#6b6375]">{label}</div>
      <div className="mt-1 text-2xl font-bold text-[#08060d]">{value}</div>
    </div>
  );
}
