import { useRef } from "react";
import { Link } from "react-router-dom";
import { useVirtualizer } from "@tanstack/react-virtual";
import { useProjectRooms } from "@/api/hooks/useDashboard";
import { ROUTES } from "@/routes";
import { buildPath } from "@/utils/routes";
import { matchesSequence } from "@/utils/search";
import TableSkeleton from "./TableSkeleton";

interface RoomsTabProps {
  projectId: string;
  search: string;
  pollInterval: number | false;
  processing: boolean;
}

const GRID_COLS =
  "minmax(90px, 9fr) minmax(110px, 11fr) minmax(110px, 11fr) minmax(80px, 8fr) minmax(70px, 7fr) minmax(140px, 14fr)";

const HEADERS: { label: string; align?: "right" }[] = [
  { label: "Nome" },
  { label: "Tipo" },
  { label: "Dimensão" },
  { label: "Lugares", align: "right" },
  { label: "Aulas", align: "right" },
  { label: "Blocos Vermelhos", align: "right" },
];

export default function RoomsTab({ projectId, search, pollInterval, processing }: RoomsTabProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const { data, isLoading, isError } = useProjectRooms(projectId, pollInterval);

  const filtered = data?.filter((r) => matchesSequence(r.name, search)) ?? [];

  const showSkeleton = isLoading || (processing && !data?.length);

  // eslint-disable-next-line react-hooks/incompatible-library
  const rowVirtualizer = useVirtualizer({
    count: filtered.length,
    getScrollElement: () => containerRef.current,
    estimateSize: () => 45,
    overscan: 15,
  });

  if (isError) {
    return <div className="py-12 text-center text-sm text-red-600">Erro ao carregar salas.</div>;
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
      aria-label="Salas"
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
          {paddingTop > 0 && <div style={{ height: paddingTop }} />}
          {virtualItems.map((virtualRow) => {
            const room = filtered[virtualRow.index];
            if (!room) return null;
            return (
              <Link
                key={room.id}
                role="row"
                to={buildPath(ROUTES.ROOM_DETAIL, { projectId, roomId: room.id })}
                draggable={false}
                className="grid items-center border-b border-[#e5e4e7] last:border-0 hover:bg-[#f9f7f4] transition-colors text-inherit no-underline [-webkit-user-drag:none]"
                style={{ gridTemplateColumns: GRID_COLS }}
              >
                <div role="cell" className="py-3 px-4 font-medium text-[#08060d]">
                  {room.name}
                </div>
                <div role="cell" className="py-3 px-4 text-[#6b6375]">
                  {room.type}
                </div>
                <div role="cell" className="py-3 px-4 text-[#6b6375]">
                  {room.size}
                </div>
                <div role="cell" className="py-3 px-4 text-right text-[#6b6375]">
                  {room.seats}
                </div>
                <div role="cell" className="py-3 px-4 text-right text-[#6b6375]">
                  {room.sessions}
                </div>
                <div role="cell" className="py-3 px-4 text-right text-[#6b6375]">
                  {room.red_blocks}
                </div>
              </Link>
            );
          })}
          {paddingBottom > 0 && <div style={{ height: paddingBottom }} />}
        </div>
      )}
    </div>
  );
}
