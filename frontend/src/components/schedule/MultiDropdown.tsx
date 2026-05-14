import { useDropdownPosition } from "./useDropdownPosition";

const DROPDOWN_CLASSES =
  "absolute bg-[#1e2028] border border-gray-600 rounded z-[200] w-[min(calc(100vw-1rem),18rem)] max-w-[min(calc(100vw-1rem),18rem)] max-h-64 overflow-x-hidden overflow-y-auto shadow-[0_4px_12px_rgba(0,0,0,0.4)]";

type DropdownOption = {
  value: string;
  label: string;
  secondaryText?: string;
};

interface MultiDropdownProps {
  label: string;
  options: DropdownOption[];
  selected: string[];
  onSelect: (value: string[]) => void;
  open: boolean;
  onToggle: () => void;
  required?: boolean;
  disabled?: boolean;
  showLabel?: boolean;
  singleSelect?: boolean;
  fitContent?: boolean;
  compact?: boolean;
  minSelected?: number;
  hideSelectedCountWhenDisabled?: boolean;
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
  showLabel,
  singleSelect,
  fitContent,
  compact,
  minSelected = 0,
  hideSelectedCountWhenDisabled = false,
}: MultiDropdownProps) {
  const isEmpty = required && selected.length === 0;
  const { wrapperRef, panelRef, openUpward, horizontalOffset } = useDropdownPosition(
    open && !disabled,
  );

  function toggle(item: string) {
    if (singleSelect) {
      onSelect([item]);
      onToggle();
      return;
    }

    const newSelection = selected.includes(item)
      ? selected.filter((x) => x !== item)
      : [...selected, item];

    // Prevent deselection if it would go below minSelected
    if (newSelection.length >= minSelected) {
      onSelect(newSelection);
    }
  }

  const triggerLabel =
    selected.length === 0
      ? label
      : singleSelect
        ? `${options.find((option) => option.value === selected[0])?.label ?? selected[0]}`
        : hideSelectedCountWhenDisabled && disabled
          ? label
          : showLabel
            ? `${label} (${selected.length}/${options.length})`
            : selected.length === 1
              ? (options.find((option) => option.value === selected[0])?.label ?? selected[0])
              : `${selected.length} selecionados`;

  return (
    <div ref={wrapperRef} className="relative">
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
        <div
          ref={panelRef}
          className={[
            fitContent
              ? "absolute bg-[#1e2028] border border-gray-600 rounded z-[200] w-[min(calc(100vw-1rem),18rem)] max-w-[min(calc(100vw-1rem),18rem)] overflow-visible shadow-[0_4px_12px_rgba(0,0,0,0.4)]"
              : compact
                ? "absolute bg-[#1e2028] border border-gray-600 rounded z-[200] w-[min(calc(100vw-1rem),10rem)] max-w-[min(calc(100vw-1rem),10rem)] max-h-64 overflow-x-hidden overflow-y-auto shadow-[0_4px_12px_rgba(0,0,0,0.4)]"
                : DROPDOWN_CLASSES,
            openUpward ? "bottom-[calc(100%+4px)]" : "top-[calc(100%+4px)]",
          ].join(" ")}
          style={{ left: horizontalOffset }}
        >
          <div className="flex flex-col gap-2.5 p-2">
            {options.map((opt) => (
              <button
                key={opt.value}
                onClick={(e) => {
                  e.stopPropagation();
                  toggle(opt.value);
                }}
                className={[
                  "w-full rounded px-2 py-1 text-[13px] cursor-pointer text-left border border-transparent hover:bg-white/5 transition-colors",
                  selected.includes(opt.value)
                    ? "text-amber-400 bg-amber-400/10 border-amber-500/20"
                    : "text-white bg-transparent",
                ].join(" ")}
              >
                <div className="flex flex-col">
                  <span className="font-semibold shrink-0 leading-tight">
                    {opt.label || opt.value}
                  </span>
                  {opt.secondaryText ? (
                    <span className="min-w-0 text-[11px] text-gray-400 leading-tight break-words whitespace-normal">
                      {opt.secondaryText}
                    </span>
                  ) : null}
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
