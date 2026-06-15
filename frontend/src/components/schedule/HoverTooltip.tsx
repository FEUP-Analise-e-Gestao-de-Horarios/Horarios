import { useCallback, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";

const HOVER_DELAY_MS = 180;
const MARGIN_PX = 8;
const GAP_PX = 6;

interface HoverTooltipProps {
  /** Rendered (and mounted) only while the tooltip is open — so any fetch in
   *  here runs on hover, not on mount. */
  content: ReactNode;
  children: ReactNode;
  /** Classes for the inline wrapper around `children` (e.g. flex sizing). */
  className?: string;
}

/**
 * Lightweight hover/focus tooltip (PI ToDo #4): shows `content` in a body
 * portal after a short intent delay, placed just below the trigger (left-
 * aligned), flipping above and clamping horizontally to stay on screen.
 */
export default function HoverTooltip({ content, children, className }: HoverTooltipProps) {
  const triggerRef = useRef<HTMLSpanElement>(null);
  const tipRef = useRef<HTMLDivElement>(null);
  const timerRef = useRef<number | undefined>(undefined);
  const [anchor, setAnchor] = useState<DOMRect | null>(null);
  const [pos, setPos] = useState<{ left: number; top: number }>({ left: 0, top: 0 });

  const show = useCallback(() => {
    window.clearTimeout(timerRef.current);
    timerRef.current = window.setTimeout(() => {
      const el = triggerRef.current;
      if (el) setAnchor(el.getBoundingClientRect());
    }, HOVER_DELAY_MS);
  }, []);

  const hide = useCallback(() => {
    window.clearTimeout(timerRef.current);
    setAnchor(null);
  }, []);

  // Place below the trigger (left-aligned); measured so it never spills off.
  useLayoutEffect(() => {
    if (!anchor || !tipRef.current) return;
    const { width, height } = tipRef.current.getBoundingClientRect();
    let left = anchor.left;
    if (left + width > window.innerWidth - MARGIN_PX) left = window.innerWidth - MARGIN_PX - width;
    left = Math.max(MARGIN_PX, left);
    let top = anchor.bottom + GAP_PX;
    if (top + height > window.innerHeight - MARGIN_PX) {
      const above = anchor.top - height - GAP_PX;
      top =
        above >= MARGIN_PX ? above : Math.max(MARGIN_PX, window.innerHeight - MARGIN_PX - height);
    }
    setPos({ left, top });
  }, [anchor]);

  return (
    <span
      ref={triggerRef}
      className={className}
      onMouseEnter={show}
      onMouseLeave={hide}
      onFocus={show}
      onBlur={hide}
    >
      {children}
      {anchor &&
        createPortal(
          <div
            ref={tipRef}
            role="tooltip"
            className="pointer-events-none fixed z-[100] max-w-[90vw] rounded border border-[#e5e4e7] bg-white px-2 py-1.5 text-xs text-[#08060d] shadow-xl"
            style={{ left: pos.left, top: pos.top }}
          >
            {content}
          </div>,
          document.body,
        )}
    </span>
  );
}
