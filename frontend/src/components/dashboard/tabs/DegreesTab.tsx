import { useRef } from "react";
import { Link } from "react-router-dom";
import { useVirtualizer } from "@tanstack/react-virtual";
import { useProjectDegrees } from "@/api/hooks/project/degree";
import { ROUTES } from "@/routes";
import type { DegreeStats } from "@/types/project/degree";
import { buildPath } from "@/utils/routes";
import { matchesSequence } from "@/utils/search";
import TableSkeleton from "./TableSkeleton";

interface DegreesTabProps {
  projectId: string;
  search: string;
  pollInterval: number | false;
  processing: boolean;
}

const COLUMNS: { key: keyof DegreeStats; label: string; align?: "right" }[] = [
  { key: "acronym", label: "Sigla" },
  { key: "name", label: "Nome" },
  { key: "years", label: "Anos", align: "right" },
  { key: "subjects", label: "UCs", align: "right" },
  { key: "classes", label: "Turmas", align: "right" },
  { key: "sessions", label: "Aulas", align: "right" },
];

const GRID_COLS = "110px minmax(0, 1fr) 70px 65px 80px 70px";

export default function DegreesTab({
  projectId,
  search,
  pollInterval,
  processing,
}: DegreesTabProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const { data, isLoading, isError } = useProjectDegrees(projectId, pollInterval);

  const filtered =
    data?.filter((d) => matchesSequence(d.acronym, search) || matchesSequence(d.name, search)) ??
    [];

  const showSkeleton = isLoading || (processing && !data?.length);

  // eslint-disable-next-line react-hooks/incompatible-library
  const rowVirtualizer = useVirtualizer({
    count: filtered.length,
    getScrollElement: () => containerRef.current,
    estimateSize: () => 45,
    overscan: 15,
  });

  if (isError) {
    return <div className="py-12 text-center text-sm text-red-600">Erro ao carregar cursos.</div>;
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
      aria-label="Cursos"
      aria-busy={showSkeleton}
      className={`h-full overflow-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden [will-change:scroll-position] text-sm ${showSkeleton ? "[mask-image:linear-gradient(to_bottom,black_50%,transparent_100%)]" : ""}`}
    >
      <div role="rowgroup" className="sticky top-0 z-10 bg-white">
        <div
          role="row"
          className="grid border-b border-[#e5e4e7]"
          style={{ gridTemplateColumns: GRID_COLS }}
        >
          {COLUMNS.map((col) => (
            <div
              key={col.key}
              role="columnheader"
              className={`py-2 px-4 text-xs font-semibold uppercase tracking-wider text-[#08060d] whitespace-nowrap ${col.align === "right" ? "text-right" : "text-left"}`}
            >
              {col.label}
            </div>
          ))}
        </div>
      </div>

      {showSkeleton ? (
        <TableSkeleton cols={COLUMNS.length} gridTemplateColumns={GRID_COLS} />
      ) : (
        <div role="rowgroup">
          {paddingTop > 0 && <div aria-hidden="true" style={{ height: paddingTop }} />}
          {virtualItems.map((virtualRow) => {
            const degree = filtered[virtualRow.index];
            if (!degree) return null;
            return (
              <div
                key={degree.id}
                role="row"
                className="grid items-center border-b border-[#e5e4e7] last:border-0 hover:bg-[#f9f7f4] transition-colors has-[a:focus-visible]:outline-2 has-[a:focus-visible]:outline-[#8c2d19] has-[a:focus-visible]:[outline-offset:-2px]"
                style={{ gridTemplateColumns: GRID_COLS }}
              >
                <Link
                  to={buildPath(ROUTES.DEGREE_DETAIL, { projectId, degreeId: degree.id })}
                  data-copy-id={degree.id}
                  data-copy-label="ID do curso"
                  draggable={false}
                  aria-label={degree.name}
                  className="contents text-inherit no-underline [-webkit-user-drag:none]"
                >
                  <div role="cell" className="py-3 px-4 font-medium text-[#08060d]">
                    {degree.acronym}
                  </div>
                  <div role="cell" className="py-3 px-4 text-[#08060d]">
                    {degree.name}
                  </div>
                  <div role="cell" className="py-3 px-4 text-right text-[#6b6375]">
                    {degree.years}
                  </div>
                  <div role="cell" className="py-3 px-4 text-right text-[#6b6375]">
                    {degree.subjects}
                  </div>
                  <div role="cell" className="py-3 px-4 text-right text-[#6b6375]">
                    {degree.classes}
                  </div>
                  <div role="cell" className="py-3 px-4 text-right text-[#6b6375]">
                    {degree.sessions}
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
