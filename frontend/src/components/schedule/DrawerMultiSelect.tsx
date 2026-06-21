import { Fragment, useEffect, useId, useRef } from "react";
import { useDismissable } from "./useDismissable";

export type DrawerSelectOption = { id: string; label: string };
export type DrawerSelectGroup = { heading?: string; options: DrawerSelectOption[] };

interface DrawerMultiSelectProps {
  /** Field label shown above the trigger. */
  label: string;
  /** Text shown inside the closed trigger button. */
  triggerLabel: string;
  open: boolean;
  onToggle: () => void;
  search: string;
  onSearchChange: (value: string) => void;
  /** Option groups; a group's heading is hidden when it has no options. */
  groups: DrawerSelectGroup[];
  selectedIds: string[];
  onToggleOption: (id: string) => void;
  /** Tailwind max-height class for the scrollable option list. */
  listMaxHeightClass?: string;
}

/**
 * Multi-select dropdown used inside the (dark-themed) edit-event drawer:
 * a labelled trigger plus a panel with a search box and a grouped, scrollable
 * option list. Selecting an option toggles it and keeps the panel open.
 *
 * Replaces three near-identical hand-rolled dropdowns (docentes, salas,
 * turmas) that previously lived inline in EditEventDrawer.
 */
export default function DrawerMultiSelect({
  label,
  triggerLabel,
  open,
  onToggle,
  search,
  onSearchChange,
  groups,
  selectedIds,
  onToggleOption,
  listMaxHeightClass = "max-h-52",
}: DrawerMultiSelectProps) {
  const baseId = useId();
  const labelId = `${baseId}-label`;
  const panelId = `${baseId}-panel`;
  const wrapperRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  // Close on outside click (or Escape). The parent drawer also tracks
  // dropdown-area dismissal; this hook handles the panel-open case directly
  // so the component behaves correctly in isolation.
  useDismissable(
    wrapperRef,
    () => {
      if (open) onToggle();
    },
    { escape: true },
  );

  // Move focus into the search field when the panel opens — both as an a11y
  // affordance and so the user can start typing immediately.
  useEffect(() => {
    if (open) searchInputRef.current?.focus();
  }, [open]);

  return (
    <div ref={wrapperRef} className="relative text-sm">
      <span id={labelId} className="mb-1.5 block text-white/90">
        {label}
      </span>
      <button
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={panelId}
        aria-labelledby={`${labelId} ${baseId}-trigger-value`}
        onClick={onToggle}
        className="w-full bg-[#2a303a] border border-white/20 rounded px-2.5 py-2 text-left flex items-center justify-between focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400/60"
      >
        <span id={`${baseId}-trigger-value`}>{triggerLabel}</span>
        <span aria-hidden="true" className="text-white/70">
          ▾
        </span>
      </button>

      {open && (
        <div
          id={panelId}
          role="listbox"
          aria-multiselectable
          aria-labelledby={labelId}
          className="absolute z-10 mt-2 w-full bg-[#222834] border border-white/20 rounded shadow-[0_10px_20px_rgba(0,0,0,0.45)] p-2"
        >
          <input
            ref={searchInputRef}
            value={search}
            onChange={(event) => onSearchChange(event.target.value)}
            placeholder="Pesquisar..."
            aria-label={`Pesquisar em ${label}`}
            className="mb-2 w-full bg-[#2a303a] border border-white/20 rounded px-2.5 py-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400/60"
          />
          <div className={`${listMaxHeightClass} overflow-y-auto space-y-1`}>
            {groups.map((group, groupIndex) => {
              const headingId = `${baseId}-group-${groupIndex}`;
              const hasHeading = !!group.heading && group.options.length > 0;
              return (
                <Fragment key={`group-${groupIndex}`}>
                  {hasHeading ? (
                    <p
                      id={headingId}
                      className="px-2 py-1 text-xs uppercase tracking-wide text-white/60"
                    >
                      {group.heading}
                    </p>
                  ) : null}
                  <div role="group" aria-labelledby={hasHeading ? headingId : undefined}>
                    {group.options.map((option) => {
                      const isSelected = selectedIds.includes(option.id);
                      return (
                        <button
                          key={option.id}
                          type="button"
                          role="option"
                          aria-selected={isSelected}
                          onClick={() => onToggleOption(option.id)}
                          className={`w-full px-2 py-1.5 text-left rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400/60 ${
                            isSelected
                              ? "bg-red-900/40 text-white font-semibold"
                              : "text-white hover:bg-white/10"
                          }`}
                        >
                          {option.label}
                        </button>
                      );
                    })}
                  </div>
                </Fragment>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
