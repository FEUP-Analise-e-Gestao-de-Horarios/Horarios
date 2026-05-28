import { useEffect, useMemo, useRef, useState } from "react";
import type { DegreeOption } from "@/types/parallelSessions";

const DROPDOWN_CLASSES =
  "absolute left-0 bg-[#1e2028] border border-gray-600 rounded z-[200] min-w-[180px] max-h-64 overflow-y-auto shadow-[0_4px_12px_rgba(0,0,0,0.4)]";

const PRIORITY_ACRONYMS = [
  "L.EIC",
  "CINF",
  "M.EIC",
  "M.IA",
  "M.ESW",
  "M.ECD",
  "M.CI",
  "MM",
  "PRODEI",
];

interface DegreeDropdownProps {
  degrees: DegreeOption[];
  selected: DegreeOption | null;
  onSelect: (degree: DegreeOption) => void;
  open: boolean;
  onToggle: () => void;
  loading?: boolean;
}

function DegreeItem({
  degree,
  selected,
  onSelect,
  onToggle,
}: {
  degree: DegreeOption;
  selected: DegreeOption | null;
  onSelect: (d: DegreeOption) => void;
  onToggle: () => void;
}) {
  return (
    <button
      onClick={(e) => {
        e.stopPropagation();
        onSelect(degree);
        onToggle();
      }}
      className={[
        "w-full px-3 py-2 text-[13px] cursor-pointer flex items-center gap-2 text-left border-none hover:bg-white/5 transition-colors",
        selected?.id === degree.id ? "text-amber-400 bg-amber-400/10" : "text-white bg-transparent",
      ].join(" ")}
    >
      {degree.acronym}
    </button>
  );
}

export default function DegreeDropdown({
  degrees,
  selected,
  onSelect,
  open,
  onToggle,
  loading,
}: DegreeDropdownProps) {
  const wrapperRef = useRef<HTMLDivElement>(null);
  const [openUpward, setOpenUpward] = useState(false);

  const priorityDegrees = useMemo(
    () => PRIORITY_ACRONYMS.flatMap((a) => degrees.filter((d) => d.acronym === a)),
    [degrees],
  );
  const otherGroups = useMemo(() => {
    const others = degrees.filter((d) => !PRIORITY_ACRONYMS.includes(d.acronym));
    return {
      Licenciaturas: others.filter((d) => d.acronym.startsWith("L.")),
      Mestrados: others.filter((d) => d.acronym.startsWith("M.")),
      Outros: others.filter((d) => !d.acronym.startsWith("L.") && !d.acronym.startsWith("M.")),
    };
  }, [degrees]);

  useEffect(() => {
    if (!open) return;

    const updateDirection = () => {
      const wrapper = wrapperRef.current;
      const trigger = wrapper?.querySelector("button");
      if (!wrapper || !trigger) return;

      const rect = trigger.getBoundingClientRect();
      const spaceBelow = window.innerHeight - rect.bottom;
      const spaceAbove = rect.top;
      setOpenUpward(spaceBelow < 280 && spaceAbove > spaceBelow);
    };

    updateDirection();
    window.addEventListener("resize", updateDirection);
    window.addEventListener("scroll", updateDirection, true);
    return () => {
      window.removeEventListener("resize", updateDirection);
      window.removeEventListener("scroll", updateDirection, true);
    };
  }, [open]);

  return (
    <div ref={wrapperRef} className="relative">
      <button
        onClick={(e) => {
          e.stopPropagation();
          if (!loading) onToggle();
        }}
        className={[
          "bg-[#1e2028] rounded px-3.5 py-2 text-sm whitespace-nowrap text-left border transition-colors",
          loading
            ? "text-gray-500 cursor-not-allowed border-gray-600"
            : selected
              ? "text-white border-gray-600 cursor-pointer hover:border-gray-400"
              : "text-red-400 border-red-900 cursor-pointer",
        ].join(" ")}
      >
        {loading ? "A carregar…" : (selected?.acronym ?? "Curso")}
      </button>

      {open && !loading && (
        <div
          className={[
            DROPDOWN_CLASSES,
            openUpward ? "bottom-[calc(100%+4px)]" : "top-[calc(100%+4px)]",
          ].join(" ")}
        >
          {priorityDegrees.map((d) => (
            <DegreeItem
              key={d.id}
              degree={d}
              selected={selected}
              onSelect={onSelect}
              onToggle={onToggle}
            />
          ))}
          {priorityDegrees.length > 0 && Object.values(otherGroups).some((g) => g.length > 0) && (
            <div className="border-t border-gray-600 my-1" />
          )}
          {Object.entries(otherGroups)
            .filter(([, items]) => items.length > 0)
            .map(([group, items]) => (
              <div key={group}>
                <div className="px-3 py-1.5 text-[11px] text-gray-400 uppercase tracking-widest border-b border-gray-600">
                  {group}
                </div>
                {items.map((d) => (
                  <DegreeItem
                    key={d.id}
                    degree={d}
                    selected={selected}
                    onSelect={onSelect}
                    onToggle={onToggle}
                  />
                ))}
              </div>
            ))}
        </div>
      )}
    </div>
  );
}
