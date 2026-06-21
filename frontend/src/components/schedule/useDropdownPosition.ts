import { useLayoutEffect, useRef, useState } from "react";

const VIEWPORT_MARGIN_PX = 8;
const OPEN_UPWARD_THRESHOLD_PX = 280;

/**
 * Positions an absolutely-positioned dropdown panel so it stays inside the
 * viewport. The panel is aligned to its trigger's left edge, then the offset is
 * clamped so the panel never overflows either viewport edge. It also decides
 * whether the panel should open upward when there isn't enough room below.
 *
 * Attach `triggerRef` to the trigger element (the thing the panel should
 * align against), `panelRef` to the panel, and apply
 * `style={{ left: horizontalOffset }}` plus the `openUpward` class.
 */
export function useDropdownPosition(open: boolean) {
  const triggerRef = useRef<HTMLElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const [openUpward, setOpenUpward] = useState(false);
  const [horizontalOffset, setHorizontalOffset] = useState(0);

  useLayoutEffect(() => {
    if (!open) return;

    const updatePosition = () => {
      const trigger = triggerRef.current;
      const panel = panelRef.current;
      if (!trigger || !panel) return;

      const rect = trigger.getBoundingClientRect();
      const spaceBelow = window.innerHeight - rect.bottom;
      const spaceAbove = rect.top;
      const panelWidth = panel.getBoundingClientRect().width;

      // Align to the trigger's left edge, then clamp so the panel stays on screen.
      const maxLeft = window.innerWidth - panelWidth - VIEWPORT_MARGIN_PX;
      const clampedLeft = Math.max(VIEWPORT_MARGIN_PX, Math.min(rect.left, maxLeft));

      setOpenUpward(spaceBelow < OPEN_UPWARD_THRESHOLD_PX && spaceAbove > spaceBelow);
      setHorizontalOffset(clampedLeft - rect.left);
    };

    updatePosition();
    window.addEventListener("resize", updatePosition);
    window.addEventListener("scroll", updatePosition, true);
    return () => {
      window.removeEventListener("resize", updatePosition);
      window.removeEventListener("scroll", updatePosition, true);
    };
  }, [open]);

  return { triggerRef, panelRef, openUpward, horizontalOffset };
}
