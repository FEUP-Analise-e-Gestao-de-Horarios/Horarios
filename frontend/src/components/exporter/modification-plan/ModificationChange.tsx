import type { ExportFieldModification, ExportModificationStep } from "@/types/exporter";
import { EntityChip } from "@/components/exporter/shared/EntityChip";
import {
  fieldLabel,
  formatFieldValue,
  isColumnChange,
  isRelationChange,
  relationChangeLabel,
} from "@/utils/exporter/formatters";

export default function ModificationChange({
  name,
  change,
  stepType,
}: {
  name: string;
  change: ExportFieldModification;
  stepType?: ExportModificationStep["type"];
}) {
  if (isColumnChange(change)) {
    const oldValue = formatFieldValue(name, change.old);
    const newValue = formatFieldValue(name, change.new);

    return (
      <div className="inline-flex max-w-full flex-wrap items-center gap-1 rounded border border-[#e5e4e7] bg-[#f9f7f4] px-1.5 py-0.5">
        <span className="text-[11px] font-bold uppercase text-[#08060d]">{fieldLabel(name)}</span>
        <span className="min-w-0 text-xs text-[#6b6375]">
          <span>{oldValue}</span>
          <span className="mx-1 text-[#08060d]">→</span>
          <span className="font-medium text-[#08060d]">{newValue}</span>
        </span>
      </div>
    );
  }

  if (isRelationChange(change)) {
    const label = fieldLabel(name);
    const clusterRelations = stepType === "exchange" && label === "Turmas";

    function renderItems(items: unknown[]) {
      return items.map((item, index) => <EntityChip key={index} item={item} />);
    }

    return (
      <div className="inline-flex max-w-full flex-wrap items-center gap-1 rounded border border-[#e5e4e7] bg-[#f9f7f4] px-1.5 py-0.5">
        <span className="text-[11px] font-bold uppercase text-[#08060d]">{label}</span>
        <div className="inline-flex flex-wrap items-center gap-1 text-xs text-[#6b6375]">
          {clusterRelations ? (
            <div className="flex flex-wrap items-center gap-1">
              {change.added.length > 0 && (
                <>
                  <span className="text-xs font-bold text-green-700">+</span>
                  {renderItems(change.added)}
                </>
              )}
              {change.added.length > 0 && change.removed.length > 0 && (
                <span className="text-[11px] font-semibold uppercase text-[#08060d]">↔</span>
              )}
              {change.removed.length > 0 && (
                <>
                  <span className="text-xs font-bold text-red-700">-</span>
                  {renderItems(change.removed)}
                </>
              )}
            </div>
          ) : (
            <>
              {!!change.added.length && (
                <div className="flex flex-wrap items-center gap-1">
                  <span className="text-xs font-bold text-green-700">+</span>
                  <span className="text-[11px] font-semibold uppercase text-[#08060d]">
                    {relationChangeLabel(label, "added")}:
                  </span>
                  {renderItems(change.added)}
                </div>
              )}
              {!!change.removed.length && (
                <div className="flex flex-wrap items-center gap-1">
                  <span className="text-xs font-bold text-red-700">-</span>
                  <span className="text-[11px] font-semibold uppercase text-[#08060d]">
                    {relationChangeLabel(label, "removed")}:
                  </span>
                  {renderItems(change.removed)}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    );
  }

  return null;
}
