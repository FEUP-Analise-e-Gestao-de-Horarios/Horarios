const DROPDOWN_CLASSES =
  "absolute top-[calc(100%+4px)] left-0 bg-[#1e2028] border border-gray-600 rounded z-[200] min-w-[180px] max-h-64 overflow-y-auto shadow-[0_4px_12px_rgba(0,0,0,0.4)]";

interface MultiDropdownProps {
  label: string;
  options: string[];
  selected: string[];
  onSelect: (value: string[]) => void;
  open: boolean;
  onToggle: () => void;
  required?: boolean;
  disabled?: boolean;
}

export default function MultiDropdown({
  label,
  options,
  selected,
  onSelect,
  open,
  onToggle,
  required,
  disabled,
}: MultiDropdownProps) {
  const isEmpty = required && selected.length === 0;

  function toggle(item: string) {
    onSelect(selected.includes(item) ? selected.filter((x) => x !== item) : [...selected, item]);
  }

  function toggleAll() {
    onSelect(selected.length === options.length ? [] : [...options]);
  }

  const triggerLabel =
    selected.length === 0
      ? label
      : selected.length === 1
        ? selected[0]
        : `${selected.length} selecionados`;

  return (
    <div className="relative">
      <button
        onClick={(e) => {
          e.stopPropagation();
          if (!disabled) onToggle();
        }}
        className={[
          "bg-[#1e2028] rounded px-3.5 py-2 text-sm whitespace-nowrap text-left border transition-colors",
          disabled
            ? "text-gray-500 cursor-not-allowed border-gray-600"
            : isEmpty
              ? "text-red-400 border-red-900 cursor-pointer"
              : "text-white border-gray-600 cursor-pointer hover:border-gray-400",
        ].join(" ")}
      >
        {triggerLabel}
      </button>

      {open && !disabled && (
        <div className={DROPDOWN_CLASSES}>
          <button
            onClick={(e) => {
              e.stopPropagation();
              toggleAll();
            }}
            className="w-full px-3 py-2 text-[13px] cursor-pointer text-amber-400 border-b border-gray-600 bg-transparent flex items-center gap-2 text-left hover:bg-white/5 transition-colors"
          >
            <span>{selected.length === options.length ? "☑" : "☐"}</span>
            Selecionar todos
          </button>
          {options.map((opt) => (
            <button
              key={opt}
              onClick={(e) => {
                e.stopPropagation();
                toggle(opt);
              }}
              className={[
                "w-full px-3 py-2 text-[13px] cursor-pointer flex items-center gap-2 text-left border-none hover:bg-white/5 transition-colors",
                selected.includes(opt)
                  ? "text-amber-400 bg-amber-400/10"
                  : "text-white bg-transparent",
              ].join(" ")}
            >
              <span>{selected.includes(opt) ? "☑" : "☐"}</span>
              {opt}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
