import { useRef } from "react";
import { Link } from "react-router-dom";
import { useVirtualizer } from "@tanstack/react-virtual";
import { useProjectTeachers } from "@/api/hooks/useDashboard";
import { ROUTES } from "@/routes";
import { buildPath } from "@/utils/routes";
import { matchesSequence } from "@/utils/search";
import TableSkeleton from "./TableSkeleton";

interface TeachersTabProps {
  projectId: string;
  search: string;
  pollInterval: number | false;
  processing: boolean;
}

const GRID_COLS = "80px 220px minmax(0, 1fr) 65px 80px 70px";

const HEADERS: { label: string; align?: "right" }[] = [
  { label: "Nº" },
  { label: "Sigla" },
  { label: "Nome" },
  { label: "UCs", align: "right" },
  { label: "Turmas", align: "right" },
  { label: "Aulas", align: "right" },
];

export default function TeachersTab({
  projectId,
  search,
  pollInterval,
  processing,
}: TeachersTabProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const { data, isLoading, isError } = useProjectTeachers(projectId, pollInterval);

  const filtered =
    data?.filter(
      (t) =>
        matchesSequence(t.acronym, search) ||
        matchesSequence(t.name, search) ||
        matchesSequence(String(t.number), search),
    ) ?? [];

  const showSkeleton = isLoading || (processing && !data?.length);

  // eslint-disable-next-line react-hooks/incompatible-library
  const rowVirtualizer = useVirtualizer({
    count: filtered.length,
    getScrollElement: () => containerRef.current,
    estimateSize: () => 45,
    overscan: 15,
  });

  if (isError) {
    return <div className="py-12 text-center text-sm text-red-600">Erro ao carregar docentes.</div>;
  }
  if (!showSkeleton && filtered.length === 0) {
    return (
      <div className="py-12 text-center text-sm text-[#6b6375]">Nenhum resultado encontrado.</div>
    );
  }

  const virtualItems = rowVirtualizer.getVirtualItems();
  const totalSize = rowVirtualizer.getTotalSize();
  const paddingTop = virtualItems[0]?.start ?? 0;
  const paddingBottom = totalSize - (virtualItems[virtualItems.length - 1]?.end ?? 0);

  return (
    <div
      ref={containerRef}
      role="table"
      aria-label="Docentes"
      className={`h-full overflow-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden [will-change:scroll-position] text-sm ${showSkeleton ? "[mask-image:linear-gradient(to_bottom,black_50%,transparent_100%)]" : ""}`}
    >
      <div role="rowgroup" className="sticky top-0 z-10 bg-white">
        <div
          role="row"
          className="grid border-b border-[#e5e4e7]"
          style={{ gridTemplateColumns: GRID_COLS }}
        >
          {HEADERS.map((h) => (
            <div
              key={h.label}
              role="columnheader"
              className={`py-2 px-4 text-xs font-semibold uppercase tracking-wider text-[#08060d] whitespace-nowrap ${h.align === "right" ? "text-right" : "text-left"}`}
            >
              {h.label}
            </div>
          ))}
        </div>
      </div>

      {showSkeleton ? (
        <TableSkeleton cols={6} gridTemplateColumns={GRID_COLS} />
      ) : (
        <div role="rowgroup">
          {paddingTop > 0 && <div aria-hidden="true" style={{ height: paddingTop }} />}
          {virtualItems.map((virtualRow) => {
            const teacher = filtered[virtualRow.index];
            if (!teacher) return null;
            return (
              <div
                key={teacher.id}
                role="row"
                className="grid items-center border-b border-[#e5e4e7] last:border-0 hover:bg-[#f9f7f4] transition-colors has-[a:focus-visible]:outline-2 has-[a:focus-visible]:outline-[#8c2d19] has-[a:focus-visible]:[outline-offset:-2px]"
                style={{ gridTemplateColumns: GRID_COLS }}
              >
                <Link
                  to={buildPath(ROUTES.TEACHER_DETAIL, { projectId, teacherId: teacher.id })}
                  draggable={false}
                  aria-label={teacher.name}
                  className="contents text-inherit no-underline [-webkit-user-drag:none]"
                >
                  <div role="cell" className="py-3 px-4 text-[#6b6375]">
                    {teacher.number}
                  </div>
                  <div role="cell" className="py-3 px-4 font-medium text-[#08060d]">
                    {teacher.acronym}
                  </div>
                  <div role="cell" className="py-3 px-4 text-[#08060d]">
                    {teacher.name}
                  </div>
                  <div role="cell" className="py-3 px-4 text-right text-[#6b6375]">
                    {teacher.subjects}
                  </div>
                  <div role="cell" className="py-3 px-4 text-right text-[#6b6375]">
                    {teacher.classes}
                  </div>
                  <div role="cell" className="py-3 px-4 text-right text-[#6b6375]">
                    {teacher.sessions}
                  </div>
                </Link>
              </div>
            );
          })}
          {paddingBottom > 0 && <div aria-hidden="true" style={{ height: paddingBottom }} />}
        </div>
      )}
    </div>
  );
}
