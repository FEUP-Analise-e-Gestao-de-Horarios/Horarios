import { useRef } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import { useProjectRooms } from "@/api/hooks/useDashboard";
import { ROUTES } from "@/routes";
import { buildPath } from "@/utils/routes";
import { matchesSequence } from "@/utils/search";
import RowLinkCell from "./RowLinkCell";
import TableSkeleton from "./TableSkeleton";

interface RoomsTabProps {
  projectId: string;
  search: string;
  pollInterval: number | false;
  processing: boolean;
}

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
      className={`h-full overflow-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden [will-change:scroll-position] ${showSkeleton ? "[mask-image:linear-gradient(to_bottom,black_50%,transparent_100%)]" : ""}`}
    >
      <table className="w-full text-sm" style={{ tableLayout: "fixed" }}>
        <colgroup>
          <col style={{ width: "90px" }} />
          <col style={{ width: "110px" }} />
          <col style={{ width: "110px" }} />
          <col style={{ width: "80px" }} />
          <col style={{ width: "70px" }} />
          <col style={{ width: "140px" }} />
        </colgroup>
        <thead className="sticky top-0 bg-white z-10">
          <tr className="border-b border-[#e5e4e7]">
            <th className="py-2 px-4 text-xs font-semibold uppercase tracking-wider text-[#08060d] text-left">
              Nome
            </th>
            <th className="py-2 px-4 text-xs font-semibold uppercase tracking-wider text-[#08060d] text-left">
              Tipo
            </th>
            <th className="py-2 px-4 text-xs font-semibold uppercase tracking-wider text-[#08060d] text-left">
              Dimensão
            </th>
            <th className="py-2 px-4 text-xs font-semibold uppercase tracking-wider text-[#08060d] text-right whitespace-nowrap">
              Lugares
            </th>
            <th className="py-2 px-4 text-xs font-semibold uppercase tracking-wider text-[#08060d] text-right whitespace-nowrap">
              Aulas
            </th>
            <th className="py-2 px-4 text-xs font-semibold uppercase tracking-wider text-[#08060d] text-right whitespace-nowrap">
              Blocos Vermelhos
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
                const room = filtered[virtualRow.index];
                if (!room) return null;
                const to = buildPath(ROUTES.ROOM_DETAIL, { projectId, roomId: room.id });
                return (
                  <tr
                    key={room.id}
                    className="border-b border-[#e5e4e7] last:border-0 hover:bg-[#f9f7f4] transition-colors"
                  >
                    <RowLinkCell to={to} primary className="font-medium text-[#08060d]">
                      {room.name}
                    </RowLinkCell>
                    <RowLinkCell to={to} className="text-[#6b6375]">
                      {room.type}
                    </RowLinkCell>
                    <RowLinkCell to={to} className="text-[#6b6375]">
                      {room.size}
                    </RowLinkCell>
                    <RowLinkCell to={to} className="text-right text-[#6b6375]">
                      {room.seats}
                    </RowLinkCell>
                    <RowLinkCell to={to} className="text-right text-[#6b6375]">
                      {room.sessions}
                    </RowLinkCell>
                    <RowLinkCell to={to} className="text-right text-[#6b6375]">
                      {room.red_blocks}
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
