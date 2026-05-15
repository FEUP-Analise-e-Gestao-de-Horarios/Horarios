import { Fragment } from "react";

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
  return (
    <div className="relative text-sm">
      <span className="mb-1.5 block text-white/90">{label}</span>
      <button
        type="button"
        aria-haspopup="true"
        aria-expanded={open}
        onClick={onToggle}
        className="w-full bg-[#2a303a] border border-white/20 rounded px-2.5 py-2 text-left flex items-center justify-between"
      >
        <span>{triggerLabel}</span>
        <span className="text-white/70">▾</span>
      </button>

      {open && (
        <div className="absolute z-10 mt-2 w-full bg-[#222834] border border-white/20 rounded shadow-[0_10px_20px_rgba(0,0,0,0.45)] p-2">
          <input
            value={search}
            onChange={(event) => onSearchChange(event.target.value)}
            placeholder="Pesquisar..."
            className="mb-2 w-full bg-[#2a303a] border border-white/20 rounded px-2.5 py-2"
          />
          <div className={`${listMaxHeightClass} overflow-y-auto space-y-1`}>
            {groups.map((group, groupIndex) => (
              <Fragment key={group.heading ?? `group-${groupIndex}`}>
                {group.heading && group.options.length > 0 ? (
                  <p className="px-2 py-1 text-xs uppercase tracking-wide text-white/60">
                    {group.heading}
                  </p>
                ) : null}
                {group.options.map((option) => {
                  const isSelected = selectedIds.includes(option.id);
                  return (
                    <button
                      key={option.id}
                      type="button"
                      onClick={() => onToggleOption(option.id)}
                      className={`w-full px-2 py-1.5 text-left rounded ${
                        isSelected
                          ? "bg-red-900/40 text-white font-semibold"
                          : "text-white hover:bg-white/10"
                      }`}
                    >
                      {option.label}
                    </button>
                  );
                })}
              </Fragment>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
