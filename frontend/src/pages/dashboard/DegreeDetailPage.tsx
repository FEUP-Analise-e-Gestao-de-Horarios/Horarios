import { Link, useParams } from "react-router-dom";
import { useProject, useProjectDegree } from "@/api/hooks/useDashboard";
import DashboardNavbar from "@/components/dashboard/DashboardNavbar";
import type { ClassWithSessions, SubjectWithSessions, YearDetail } from "@/types/dashboard";

export default function DegreeDetailPage() {
  const { projectId, degreeId } = useParams<{ projectId: string; degreeId: string }>();
  const pid = projectId ?? "";
  const did = degreeId ?? "";

  const project = useProject(pid);
  const { data, isLoading, isError } = useProjectDegree(pid, did);

  const years = data?.years ?? [];
  const subjectsCount = years.reduce((sum, y) => sum + y.subjects.length, 0);
  const classesCount = years.reduce((sum, y) => sum + y.classes.length, 0);

  return (
    <div className="h-screen flex flex-col bg-[#f0eeeb]">
      <DashboardNavbar projectId={pid} isReady={!!project.data?.ingestion_finished_at} />

      <div className="flex-1 overflow-auto">
        <div className="max-w-7xl mx-auto px-6 pt-6 pb-6 flex flex-col gap-5">
          {isLoading ? (
            <div className="bg-white rounded-lg border border-[#e5e4e7] shadow-[0_2px_8px_rgba(0,0,0,0.06)] p-6 h-32 animate-pulse" />
          ) : isError || !data ? (
            <div className="bg-white rounded-lg border border-[#e5e4e7] shadow-[0_2px_8px_rgba(0,0,0,0.06)] p-6 text-sm text-red-600">
              Erro ao carregar curso.
            </div>
          ) : (
            <>
              <div className="bg-white rounded-lg border border-[#e5e4e7] shadow-[0_2px_8px_rgba(0,0,0,0.06)] px-6 py-4 flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <h1 className="text-2xl font-bold text-[#08060d]">{data.name}</h1>
                  <div className="mt-1 text-sm text-[#6b6375]">{data.acronym}</div>
                </div>
                <div className="shrink-0 text-right text-sm text-[#6b6375]">
                  <div>
                    <span className="font-semibold text-[#08060d]">{years.length}</span> anos
                  </div>
                  <div>
                    <span className="font-semibold text-[#08060d]">{subjectsCount}</span> UCs
                  </div>
                  <div>
                    <span className="font-semibold text-[#08060d]">{classesCount}</span> turmas
                  </div>
                </div>
              </div>

              {years.length === 0 ? (
                <div className="bg-white rounded-lg border border-[#e5e4e7] shadow-[0_2px_8px_rgba(0,0,0,0.06)] p-6 text-center text-sm text-[#6b6375]">
                  Este curso ainda não tem anos.
                </div>
              ) : (
                years.map((year) => <YearSection key={year.id} projectId={pid} year={year} />)
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function YearSection({ projectId, year }: { projectId: string; year: YearDetail }) {
  return (
    <section>
      <div className="flex items-baseline justify-between mb-2">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-[#08060d]">
          Ano {year.number}
        </h2>
        <span className="text-xs text-[#6b6375]">
          {year.subjects.length} UCs · {year.classes.length} turmas
        </span>
      </div>
      <div className="grid md:grid-cols-2 gap-3">
        <ListCard title="Unidades curriculares">
          {year.subjects.length === 0 ? (
            <EmptyRow />
          ) : (
            year.subjects.map((s) => <SubjectRow key={s.id} projectId={projectId} subject={s} />)
          )}
        </ListCard>
        <ListCard title="Turmas">
          {year.classes.length === 0 ? (
            <EmptyRow />
          ) : (
            year.classes.map((c) => <ClassRow key={c.id} projectId={projectId} classItem={c} />)
          )}
        </ListCard>
      </div>
    </section>
  );
}

function ListCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-white rounded-lg border border-[#e5e4e7] shadow-[0_2px_8px_rgba(0,0,0,0.06)] overflow-hidden">
      <div className="px-4 py-2 border-b border-[#e5e4e7] text-xs font-semibold uppercase tracking-wider text-[#6b6375]">
        {title}
      </div>
      <ul className="divide-y divide-[#e5e4e7]">{children}</ul>
    </div>
  );
}

function SubjectRow({ projectId, subject }: { projectId: string; subject: SubjectWithSessions }) {
  return (
    <li>
      <Link
        to={`/projects/${projectId}/dashboard/subjects/${subject.id}`}
        className="flex items-baseline justify-between gap-3 px-4 py-2 hover:bg-[#f9f7f4] transition-colors"
      >
        <div className="min-w-0">
          <div className="text-sm font-medium text-[#08060d] truncate">{subject.name}</div>
          <div className="text-xs text-[#6b6375] truncate">
            {subject.acronym} · {subject.code}
          </div>
        </div>
        <div className="shrink-0 text-xs text-[#6b6375]">
          <span className="font-semibold text-[#08060d]">{subject.sessions}</span> aulas
        </div>
      </Link>
    </li>
  );
}

function ClassRow({ projectId, classItem }: { projectId: string; classItem: ClassWithSessions }) {
  return (
    <li>
      <Link
        to={`/projects/${projectId}/dashboard/classes/${classItem.id}`}
        className="flex items-baseline justify-between gap-3 px-4 py-2 hover:bg-[#f9f7f4] transition-colors"
      >
        <div className="min-w-0">
          <div className="text-sm font-medium text-[#08060d] truncate">{classItem.code}</div>
          <div className="text-xs text-[#6b6375]">Turno {classItem.shift}</div>
        </div>
        <div className="shrink-0 text-xs text-[#6b6375]">
          <span className="font-semibold text-[#08060d]">{classItem.sessions}</span> aulas
        </div>
      </Link>
    </li>
  );
}

function EmptyRow() {
  return <li className="px-4 py-3 text-xs text-[#6b6375] italic">—</li>;
}
