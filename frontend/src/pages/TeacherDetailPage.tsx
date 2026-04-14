import { useParams } from "react-router-dom";
import { useProject, useProjectTeacher } from "@/api/hooks/useDashboard";
import DashboardNavbar from "@/components/dashboard/DashboardNavbar";

export default function TeacherDetailPage() {
  const { projectId, teacherId } = useParams<{ projectId: string; teacherId: string }>();
  const pid = projectId ?? "";
  const tid = teacherId ?? "";

  const project = useProject(pid);
  const { data, isLoading, isError } = useProjectTeacher(pid, tid);

  return (
    <div className="h-screen flex flex-col bg-[#f0eeeb]">
      <DashboardNavbar projectId={pid} isReady={!!project.data?.ingestion_finished_at} />

      <div className="flex-1 overflow-auto">
        <div className="max-w-7xl mx-auto px-6 pt-6 pb-6 flex flex-col gap-5">
          {isLoading ? (
            <div className="bg-white rounded-lg border border-[#e5e4e7] shadow-[0_2px_8px_rgba(0,0,0,0.06)] p-6 h-32 animate-pulse" />
          ) : isError || !data ? (
            <div className="bg-white rounded-lg border border-[#e5e4e7] shadow-[0_2px_8px_rgba(0,0,0,0.06)] p-6 text-sm text-red-600">
              Erro ao carregar docente.
            </div>
          ) : (
            <>
              <div className="bg-white rounded-lg border border-[#e5e4e7] shadow-[0_2px_8px_rgba(0,0,0,0.06)] p-6">
                <div className="text-xs font-semibold uppercase tracking-wider text-[#6b6375]">
                  Nº {data.number} · {data.acronym}
                </div>
                <h1 className="mt-1 text-2xl font-bold text-[#08060d]">{data.name}</h1>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <StatCard label="UCs" value={data.subjects.length} />
                <StatCard label="Turmas" value={data.classes.length} />
                <StatCard label="Aulas" value={data.sessions.length} />
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
