import { useId } from "react";
import DropdownShell from "./DropdownShell";

const CURSO_PANEL_CLASS =
  "w-[min(calc(100vw-1rem),48rem)] max-h-[min(60vh,24rem)] overflow-x-hidden overflow-y-auto";

type CursoOption = {
  value: string;
  label: string;
  description?: string;
};

type CursoGroup = {
  label: string;
  options: CursoOption[];
};

interface CursoDropdownProps {
  value: string;
  onSelect: (curso: string) => void;
  open: boolean;
  onToggle: () => void;
  options: CursoGroup[];
}

export default function CursoDropdown({
  value,
  onSelect,
  open,
  onToggle,
  options,
}: CursoDropdownProps) {
  const baseId = useId();
  const panelId = `${baseId}-panel`;

  return (
    <DropdownShell
      open={open}
      panelClassName={CURSO_PANEL_CLASS}
      panelId={panelId}
      trigger={
        <button
          type="button"
          aria-haspopup="listbox"
          aria-expanded={open}
          aria-controls={panelId}
          aria-label={`Curso${value ? `: ${value}` : ""}`}
          onClick={(e) => {
            e.stopPropagation();
            onToggle();
          }}
          className={[
            "bg-[#1e2028] rounded px-3.5 py-2 text-sm whitespace-nowrap text-left border cursor-pointer transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400/60",
            value === ""
              ? "text-red-400 border-red-900"
              : "text-white border-gray-600 hover:border-gray-400",
          ].join(" ")}
        >
          {value === "" ? "Curso" : value}
        </button>
      }
    >
      {options.length === 0 ? (
        <div className="px-3 py-3 text-[13px] text-gray-400">Sem cursos disponíveis.</div>
      ) : (
        <div className="flex flex-row items-stretch">
          {options.map((group, groupIndex) => {
            const headingId = `${baseId}-group-${groupIndex}`;
            return (
              <div
                key={group.label}
                role="group"
                aria-labelledby={headingId}
                className="flex-1 min-w-0 border-r border-gray-700 last:border-r-0"
              >
                <div
                  id={headingId}
                  className="px-3 py-1.5 text-[11px] text-gray-400 uppercase tracking-widest border-b border-gray-700"
                >
                  {group.label}
                </div>
                <div className="flex flex-col gap-2.5 p-2">
                  {group.options.map((option) => {
                    const isSelected = value === option.value;
                    return (
                      <button
                        key={option.value}
                        type="button"
                        role="option"
                        aria-selected={isSelected}
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelect(option.value);
                        }}
                        className={[
                          "w-full rounded px-2 py-1 text-[13px] cursor-pointer text-left border border-transparent hover:bg-white/5 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400/60",
                          isSelected
                            ? "text-amber-400 bg-amber-400/10 border-amber-500/20"
                            : "text-white bg-transparent",
                        ].join(" ")}
                        title={
                          option.description
                            ? `${option.label} · ${option.description}`
                            : option.label
                        }
                      >
                        <div className="flex flex-col">
                          <span className="font-semibold shrink-0 leading-tight">
                            {option.label}
                          </span>
                          {option.description ? (
                            <span className="min-w-0 text-[11px] text-gray-400 leading-tight break-words whitespace-normal">
                              {option.description}
                            </span>
                          ) : null}
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </DropdownShell>
  );
}
