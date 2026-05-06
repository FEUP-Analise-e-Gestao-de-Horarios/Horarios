import { useRef } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import { useProjectTeachers } from "@/api/hooks/useDashboard";
import { ROUTES } from "@/routes";
import { buildPath } from "@/utils/routes";
import { matchesSequence } from "@/utils/search";
import RowLinkCell from "./RowLinkCell";
import TableSkeleton from "./TableSkeleton";

interface TeachersTabProps {
  projectId: string;
  search: string;
  pollInterval: number | false;
  processing: boolean;
}

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
      className={`h-full overflow-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden [will-change:scroll-position] ${showSkeleton ? "[mask-image:linear-gradient(to_bottom,black_50%,transparent_100%)]" : ""}`}
    >
      <table className="w-full text-sm" style={{ tableLayout: "fixed" }}>
        <colgroup>
          <col style={{ width: "80px" }} />
          <col style={{ width: "220px" }} />
          <col />
          <col style={{ width: "65px" }} />
          <col style={{ width: "80px" }} />
          <col style={{ width: "70px" }} />
        </colgroup>
        <thead className="sticky top-0 bg-white z-10">
          <tr className="border-b border-[#e5e4e7]">
            <th className="py-2 px-4 text-xs font-semibold uppercase tracking-wider text-[#08060d] text-left">
              Nº
            </th>
            <th className="py-2 px-4 text-xs font-semibold uppercase tracking-wider text-[#08060d] text-left">
              Sigla
            </th>
            <th className="py-2 px-4 text-xs font-semibold uppercase tracking-wider text-[#08060d] text-left">
              Nome
            </th>
            <th className="py-2 px-4 text-xs font-semibold uppercase tracking-wider text-[#08060d] text-right whitespace-nowrap">
              UCs
            </th>
            <th className="py-2 px-4 text-xs font-semibold uppercase tracking-wider text-[#08060d] text-right whitespace-nowrap">
              Turmas
            </th>
            <th className="py-2 px-4 text-xs font-semibold uppercase tracking-wider text-[#08060d] text-right whitespace-nowrap">
              Aulas
            </th>
          </tr>
        </thead>
        <tbody>
          {showSkeleton ? (
            <TableSkeleton cols={6} />
          ) : (
            <>
              {paddingTop > 0 && (
                <tr>
                  <td style={{ height: paddingTop }} colSpan={6} />
                </tr>
              )}
              {virtualItems.map((virtualRow) => {
                const teacher = filtered[virtualRow.index];
                if (!teacher) return null;
                const to = buildPath(ROUTES.TEACHER_DETAIL, { projectId, teacherId: teacher.id });
                return (
                  <tr
                    key={teacher.id}
                    className="border-b border-[#e5e4e7] last:border-0 hover:bg-[#f9f7f4] transition-colors"
                  >
                    <RowLinkCell to={to} className="text-[#6b6375]">
                      {teacher.number}
                    </RowLinkCell>
                    <RowLinkCell to={to} className="font-medium text-[#08060d]">
                      {teacher.acronym}
                    </RowLinkCell>
                    <RowLinkCell to={to} primary className="text-[#08060d]">
                      {teacher.name}
                    </RowLinkCell>
                    <RowLinkCell to={to} className="text-right text-[#6b6375]">
                      {teacher.subjects}
                    </RowLinkCell>
                    <RowLinkCell to={to} className="text-right text-[#6b6375]">
                      {teacher.classes}
                    </RowLinkCell>
                    <RowLinkCell to={to} className="text-right text-[#6b6375]">
                      {teacher.sessions}
                    </RowLinkCell>
                  </tr>
                );
              })}
              {paddingBottom > 0 && (
                <tr>
                  <td style={{ height: paddingBottom }} colSpan={6} />
                </tr>
              )}
            </>
          )}
        </tbody>
      </table>
    </div>
  );
}
