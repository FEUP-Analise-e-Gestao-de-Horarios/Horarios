import { useEffect, useRef, useState } from "react";

const DROPDOWN_CLASSES =
  "absolute left-0 bg-[#1e2028] border border-gray-600 rounded z-[200] w-[min(calc(100vw-1rem),22rem)] max-h-[min(60vh,24rem)] overflow-x-hidden overflow-y-auto shadow-[0_4px_12px_rgba(0,0,0,0.4)]";

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
  const wrapperRef = useRef<HTMLDivElement>(null);
  const [openUpward, setOpenUpward] = useState(false);
  const [openLeftward, setOpenLeftward] = useState(false);

  useEffect(() => {
    if (!open) return;

    const updateDirection = () => {
      const wrapper = wrapperRef.current;
      const trigger = wrapper?.querySelector("button");
      if (!wrapper || !trigger) return;

      const rect = trigger.getBoundingClientRect();
      const spaceBelow = window.innerHeight - rect.bottom;
      const spaceAbove = rect.top;
      const dropdownWidth = Math.min(window.innerWidth - 16, 352);
      const spaceRight = window.innerWidth - rect.left;
      const spaceLeft = rect.right;
      setOpenUpward(spaceBelow < 280 && spaceAbove > spaceBelow);
      setOpenLeftward(spaceRight < dropdownWidth && spaceLeft > spaceRight);
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
          onToggle();
        }}
        className={[
          "bg-[#1e2028] rounded px-3.5 py-2 text-sm whitespace-nowrap text-left border cursor-pointer transition-colors",
          value === ""
            ? "text-red-400 border-red-900"
            : "text-white border-gray-600 hover:border-gray-400",
        ].join(" ")}
      >
        {value === "" ? "Curso" : value}
      </button>

      {open && (
        <div
          className={[
            DROPDOWN_CLASSES,
            openLeftward ? "right-0 left-auto" : "left-0 right-auto",
            openUpward ? "bottom-[calc(100%+4px)]" : "top-[calc(100%+4px)]",
          ].join(" ")}
        >
          {options.length === 0 ? (
            <div className="px-3 py-3 text-[13px] text-gray-400">Sem cursos disponíveis.</div>
          ) : (
            options.map((group) => (
              <div key={group.label} className="border-b border-gray-700 last:border-b-0">
                <div className="px-3 py-1.5 text-[11px] text-gray-400 uppercase tracking-widest border-b border-gray-700">
                  {group.label}
                </div>
                <div className="flex flex-col gap-1 p-2">
                  {group.options.map((option) => (
                    <button
                      key={option.value}
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelect(option.value);
                      }}
                      className={[
                        "w-full rounded px-3 py-2 text-[13px] cursor-pointer text-left border border-transparent hover:bg-white/5 transition-colors",
                        value === option.value
                          ? "text-amber-400 bg-amber-400/10 border-amber-500/20"
                          : "text-white bg-transparent",
                      ].join(" ")}
                      title={
                        option.description
                          ? `${option.label} · ${option.description}`
                          : option.label
                      }
                    >
                      <div className="flex flex-col gap-0.5 sm:flex-row sm:items-baseline sm:gap-2">
                        <span className="font-semibold shrink-0">{option.label}</span>
                        {option.description ? (
                          <span className="min-w-0 text-[12px] text-gray-400 leading-snug break-words whitespace-normal">
                            {option.description}
                          </span>
                        ) : null}
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
