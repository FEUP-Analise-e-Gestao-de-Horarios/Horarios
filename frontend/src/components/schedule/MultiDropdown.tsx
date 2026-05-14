import DropdownShell from "./DropdownShell";
import type { SubjectStyle } from "./subjectColors";

const PANEL_CLASS_DEFAULT =
  "w-[min(calc(100vw-1rem),18rem)] max-w-[min(calc(100vw-1rem),18rem)] max-h-64 overflow-x-hidden overflow-y-auto";
const PANEL_CLASS_FIT_CONTENT =
  "w-[min(calc(100vw-1rem),18rem)] max-w-[min(calc(100vw-1rem),18rem)] overflow-visible";
const PANEL_CLASS_COMPACT =
  "w-[min(calc(100vw-1rem),10rem)] max-w-[min(calc(100vw-1rem),10rem)] max-h-64 overflow-x-hidden overflow-y-auto";

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
  // When provided, a selected option is tinted with this style instead of the
  // default amber highlight (used to mirror the week grid's per-subject colours).
  getOptionStyle?: (value: string) => SubjectStyle | null;
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
  getOptionStyle,
}: MultiDropdownProps) {
  const isEmpty = required && selected.length === 0;
  const isOpen = open && !disabled;
  const panelClassName = fitContent
    ? PANEL_CLASS_FIT_CONTENT
    : compact
      ? PANEL_CLASS_COMPACT
      : PANEL_CLASS_DEFAULT;

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

  function getTriggerLabel(): string {
    if (selected.length === 0) return label;
    const firstLabel =
      options.find((option) => option.value === selected[0])?.label ?? selected[0] ?? label;
    if (singleSelect) return firstLabel;
    if (hideSelectedCountWhenDisabled && disabled) return label;
    if (showLabel) return `${label} (${selected.length}/${options.length})`;
    if (selected.length === 1) return firstLabel;
    return `${selected.length} selecionados`;
  }
  const triggerLabel = getTriggerLabel();

  return (
    <DropdownShell
      open={isOpen}
      panelClassName={panelClassName}
      trigger={
        <button
          type="button"
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
      }
    >
      <div className="flex flex-col gap-2.5 p-2">
        {options.map((opt) => {
          const isSelected = selected.includes(opt.value);
          const optionStyle = getOptionStyle?.(opt.value) ?? null;
          return (
            <button
              key={opt.value}
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                toggle(opt.value);
              }}
              className={[
                "w-full rounded px-2 py-1 text-[13px] cursor-pointer text-left border hover:bg-white/5 transition-colors",
                isSelected
                  ? optionStyle
                    ? `${optionStyle.bg} ${optionStyle.border} ${optionStyle.text}`
                    : "text-amber-400 bg-amber-400/10 border-amber-500/20"
                  : "text-white bg-transparent border-transparent",
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
          );
        })}
      </div>
    </DropdownShell>
  );
}
