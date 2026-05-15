import type { ReactNode } from "react";
import { useDropdownPosition } from "./useDropdownPosition";

// Classes shared by every schedule filter dropdown panel. Size and overflow
// behaviour vary per dropdown and are passed in via `panelClassName`.
const DROPDOWN_PANEL_BASE =
  "absolute bg-[#1e2028] border border-gray-600 rounded z-[200] shadow-[0_4px_12px_rgba(0,0,0,0.4)]";

interface DropdownShellProps {
  /** Whether the panel is shown. Callers should fold in `!disabled` here. */
  open: boolean;
  /** The trigger button. Rendered inside the positioned wrapper. */
  trigger: ReactNode;
  /** Size/overflow utility classes for the panel (width, max-height, …). */
  panelClassName?: string;
  /** Panel contents. */
  children: ReactNode;
}

/**
 * Shared shell for the schedule filter dropdowns: owns the `relative` wrapper,
 * viewport-aware positioning (via `useDropdownPosition`) and the common panel
 * chrome. Each dropdown supplies its own trigger and panel body.
 */
export default function DropdownShell({
  open,
  trigger,
  panelClassName = "",
  children,
}: DropdownShellProps) {
  const { triggerRef, panelRef, openUpward, horizontalOffset } = useDropdownPosition(open);

  // triggerRef points at the wrapper, not the trigger element. The panel is
  // absolutely positioned, so it does not contribute to the wrapper's
  // bounding rect — measuring the wrapper gives us the trigger's rect
  // without depending on which DOM node the caller passed in.
  return (
    <div ref={triggerRef as React.RefObject<HTMLDivElement>} className="relative">
      {trigger}

      {open && (
        <div
          ref={panelRef}
          className={[
            DROPDOWN_PANEL_BASE,
            panelClassName,
            openUpward ? "bottom-[calc(100%+4px)]" : "top-[calc(100%+4px)]",
          ].join(" ")}
          style={{ left: horizontalOffset }}
        >
          {children}
        </div>
      )}
    </div>
  );
}
