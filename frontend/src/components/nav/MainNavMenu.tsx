import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ChevronDown } from "lucide-react";
import { useDismissable } from "@/components/schedule/useDismissable";

export interface MainNavItem {
  /** Stable key for the list. */
  key: string;
  label: string;
  /** Router destination. Mutually exclusive with `onClick`. */
  to?: string;
  /** Imperative action (e.g. programmatic navigation). */
  onClick?: () => void;
  /** The page we are currently on: renders as the trigger, not in the panel. */
  current?: boolean;
  /** Reachable but temporarily unavailable (e.g. schedule not generated yet). */
  disabled?: boolean;
  /** Tooltip shown on a disabled item. */
  disabledTitle?: string;
}

const ITEM_BASE =
  "block w-full rounded px-3 py-2 text-left text-sm font-medium whitespace-nowrap transition-colors";

/**
 * Collapses the primary cross-page navigation into a single hover dropdown.
 *
 * The trigger is the most relevant destination for the current page (the "you
 * are here" anchor); it navigates on click, and hovering or focusing it reveals
 * every other destination stacked underneath. Shared by the dashboard, schedule
 * and parallel-sessions headers so the main navigation looks and behaves
 * identically on every page.
 *
 * The trigger and panel live inside one wrapper with a padded (not margined)
 * gap, so the pointer never leaves the hover region while travelling from the
 * button to the menu.
 */
export default function MainNavMenu({ items }: { items: MainNavItem[] }) {
  const [open, setOpen] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);

  useDismissable(wrapperRef, () => setOpen(false), { escape: true });

  const trigger = items.find((i) => i.current) ?? items[0];
  const others = items.filter((i) => i !== trigger);

  if (!trigger) return null;

  const triggerClass =
    "flex items-center gap-1.5 bg-[#8C2C19] text-white font-semibold pl-3.5 pr-2.5 py-2 rounded text-sm whitespace-nowrap hover:bg-[#A9361E] transition-colors cursor-pointer";
  const chevron = (
    <ChevronDown
      className={`h-4 w-4 transition-transform duration-200 ${open ? "rotate-180" : ""}`}
    />
  );

  return (
    <div
      ref={wrapperRef}
      className="relative"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      {trigger.to ? (
        <Link
          to={trigger.to}
          aria-haspopup="menu"
          aria-expanded={open}
          onFocus={() => setOpen(true)}
          onClick={() => setOpen(false)}
          className={triggerClass}
        >
          {trigger.label}
          {chevron}
        </Link>
      ) : (
        <button
          type="button"
          aria-haspopup="menu"
          aria-expanded={open}
          onFocus={() => setOpen(true)}
          onClick={() => {
            setOpen(false);
            trigger.onClick?.();
          }}
          className={triggerClass}
        >
          {trigger.label}
          {chevron}
        </button>
      )}

      {open && others.length > 0 && (
        <div className="absolute left-0 top-full z-50 pt-1.5">
          <div
            role="menu"
            className="min-w-[11rem] flex flex-col rounded-lg border border-gray-700 bg-[#282a33] p-1 shadow-[0_8px_24px_rgba(0,0,0,0.4)]"
          >
            {others.map((item) => {
              if (item.disabled) {
                return (
                  <span
                    key={item.key}
                    role="menuitem"
                    aria-disabled
                    title={item.disabledTitle}
                    className={`${ITEM_BASE} text-gray-500 cursor-not-allowed`}
                  >
                    {item.label}
                  </span>
                );
              }
              if (item.to) {
                return (
                  <Link
                    key={item.key}
                    to={item.to}
                    role="menuitem"
                    onClick={() => setOpen(false)}
                    className={`${ITEM_BASE} text-gray-200 hover:bg-white/10 hover:text-white`}
                  >
                    {item.label}
                  </Link>
                );
              }
              return (
                <button
                  key={item.key}
                  type="button"
                  role="menuitem"
                  onClick={() => {
                    setOpen(false);
                    item.onClick?.();
                  }}
                  className={`${ITEM_BASE} text-gray-200 hover:bg-white/10 hover:text-white cursor-pointer`}
                >
                  {item.label}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
