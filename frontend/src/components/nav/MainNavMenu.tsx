import { Link } from "react-router-dom";

export interface MainNavItem {
  /** Stable key for the list. */
  key: string;
  label: string;
  /** Router destination. Mutually exclusive with `onClick`. */
  to?: string;
  /** Imperative action (e.g. programmatic navigation). */
  onClick?: () => void;
  /** The page we are currently on: omitted from the rendered row entirely. */
  current?: boolean;
  /** Reachable but temporarily unavailable (e.g. schedule not generated yet). */
  disabled?: boolean;
  /** Tooltip shown on a disabled item. */
  disabledTitle?: string;
  /** Solid brand-color button instead of the bordered default (e.g. "Início"). */
  primary?: boolean;
}

const ITEM_BASE = "px-3.5 py-2 rounded text-sm font-semibold whitespace-nowrap transition-colors";
const PRIMARY_CLASS = `${ITEM_BASE} bg-[#8C2C19] text-white hover:bg-[#A9361E] cursor-pointer`;
// Red border (not the neutral gray other buttons in the header use) so the
// nav row reads as one group, distinct from feature buttons like Exportar.
const SECONDARY_CLASS = `${ITEM_BASE} bg-transparent text-white border border-[#8C2C19] hover:border-[#A9361E] hover:bg-white/5 cursor-pointer`;
const DISABLED_CLASS = `${ITEM_BASE} bg-transparent text-white border border-[#8C2C19] opacity-40 cursor-not-allowed`;

/**
 * Renders every destination except the current page as its own always-visible
 * button — "Início" first (solid), the rest after in whatever order they
 * were given (their relative order doesn't matter). Reverted from a hover
 * dropdown (#43) — Ana found the dropdown harder to scan than a plain row of
 * buttons. Shared by the dashboard, schedule and parallel-sessions headers so
 * the buttons look and behave identically on every page.
 */
export default function MainNavMenu({ items }: { items: MainNavItem[] }) {
  const visible = items.filter((item) => !item.current);
  const ordered = [
    ...visible.filter((item) => item.primary),
    ...visible.filter((item) => !item.primary),
  ];
  return (
    <>
      {ordered.map((item) => {
        const className = item.disabled
          ? DISABLED_CLASS
          : item.primary
            ? PRIMARY_CLASS
            : SECONDARY_CLASS;

        if (item.disabled) {
          return (
            <button
              key={item.key}
              type="button"
              disabled
              title={item.disabledTitle}
              className={className}
            >
              {item.label}
            </button>
          );
        }

        if (item.to) {
          return (
            <Link key={item.key} to={item.to} className={className}>
              {item.label}
            </Link>
          );
        }

        return (
          <button key={item.key} type="button" onClick={item.onClick} className={className}>
            {item.label}
          </button>
        );
      })}
    </>
  );
}
