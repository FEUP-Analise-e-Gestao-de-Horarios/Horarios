import { useRef } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import { useProjectDegrees } from "@/api/hooks/useDashboard";
import type { DegreeStats } from "@/types/dashboard";
import { matchesSequence } from "@/utils/search";
import TableSkeleton from "./TableSkeleton";

interface DegreesTabProps {
  projectId: string;
  search: string;
  pollInterval: number | false;
  processing: boolean;
}

const COLUMNS: { key: keyof DegreeStats; label: string; align?: "right"; width?: string }[] = [
  { key: "acronym", label: "Sigla", width: "110px" },
  { key: "name", label: "Nome" },
  { key: "years", label: "Anos", align: "right", width: "70px" },
  { key: "subjects", label: "UCs", align: "right", width: "65px" },
  { key: "classes", label: "Turmas", align: "right", width: "80px" },
  { key: "sessions", label: "Aulas", align: "right", width: "70px" },
];

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
      className={`h-full overflow-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden [will-change:scroll-position] ${showSkeleton ? "[mask-image:linear-gradient(to_bottom,black_50%,transparent_100%)]" : ""}`}
    >
      <table className="w-full text-sm" style={{ tableLayout: "fixed" }}>
        <colgroup>
          {COLUMNS.map((col) => (
            <col key={col.key} style={col.width ? { width: col.width } : undefined} />
          ))}
        </colgroup>
        <thead className="sticky top-0 bg-white z-10">
          <tr className="border-b border-[#e5e4e7]">
            {COLUMNS.map((col) => (
              <th
                key={col.key}
                className={`py-2 px-4 text-xs font-semibold uppercase tracking-wider text-[#08060d] whitespace-nowrap ${col.align === "right" ? "text-right" : "text-left"}`}
              >
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {showSkeleton ? (
            <TableSkeleton cols={COLUMNS.length} />
          ) : (
            <>
              {paddingTop > 0 && (
                <tr>
                  <td style={{ height: paddingTop }} colSpan={COLUMNS.length} />
                </tr>
              )}
              {virtualItems.map((virtualRow) => {
                const degree = filtered[virtualRow.index];
                if (!degree) return null;
                return (
                  <tr
                    key={degree.id}
                    className="border-b border-[#e5e4e7] last:border-0 hover:bg-[#f9f7f4] transition-colors"
                  >
                    <td className="py-3 px-4 font-medium text-[#08060d]">{degree.acronym}</td>
                    <td className="py-3 px-4 text-[#08060d]">{degree.name}</td>
                    <td className="py-3 px-4 text-right text-[#6b6375]">{degree.years}</td>
                    <td className="py-3 px-4 text-right text-[#6b6375]">{degree.subjects}</td>
                    <td className="py-3 px-4 text-right text-[#6b6375]">{degree.classes}</td>
                    <td className="py-3 px-4 text-right text-[#6b6375]">{degree.sessions}</td>
                  </tr>
                );
              })}
              {paddingBottom > 0 && (
                <tr>
                  <td style={{ height: paddingBottom }} colSpan={COLUMNS.length} />
                </tr>
              )}
            </>
          )}
        </tbody>
      </table>
    </div>
  );
}
