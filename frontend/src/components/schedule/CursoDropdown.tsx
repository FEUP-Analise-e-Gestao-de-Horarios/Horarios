import { CURSOS } from "./data";

const DROPDOWN_CLASSES =
  "absolute top-[calc(100%+4px)] left-0 bg-[#1e2028] border border-gray-600 rounded z-[200] min-w-[180px] max-h-64 overflow-y-auto shadow-[0_4px_12px_rgba(0,0,0,0.4)]";

interface CursoDropdownProps {
  value: string;
  onSelect: (curso: string) => void;
  open: boolean;
  onToggle: () => void;
}

export default function CursoDropdown({ value, onSelect, open, onToggle }: CursoDropdownProps) {
  return (
    <div className="relative">
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
        <div className={DROPDOWN_CLASSES}>
          {Object.entries(CURSOS).map(([group, items]) => (
            <div key={group}>
              <div className="px-3 py-1.5 text-[11px] text-gray-400 uppercase tracking-widest border-b border-gray-600">
                {group}
              </div>
              {items.map((c) => (
                <button
                  key={c}
                  onClick={(e) => {
                    e.stopPropagation();
                    onSelect(c);
                  }}
                  className={[
                    "w-full px-3 py-2 text-[13px] cursor-pointer flex items-center gap-2 text-left border-none hover:bg-white/5 transition-colors",
                    value === c ? "text-amber-400 bg-amber-400/10" : "text-white bg-transparent",
                  ].join(" ")}
                >
                  {c}
                </button>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
