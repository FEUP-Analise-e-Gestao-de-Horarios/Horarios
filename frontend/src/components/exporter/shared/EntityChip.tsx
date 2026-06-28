import StyledTooltip from "@/components/exporter/shared/StyledTooltip";
import { relationRecord } from "@/utils/exporter/relations";

export function EntityChip({ item }: { item: unknown }) {
  const relation = relationRecord(item);

  return (
    <StyledTooltip content={relation.title}>
      <span className="inline-flex max-w-full items-center rounded border border-[#d8d3cf] bg-white px-1 py-0 text-xs font-medium text-[#08060d]">
        <span className="truncate">{relation.label}</span>
      </span>
    </StyledTooltip>
  );
}
