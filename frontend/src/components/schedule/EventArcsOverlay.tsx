import { useLayoutEffect, useRef, useState, type RefObject } from "react";
import { buildArcPath } from "./scheduleGrid";

interface EventArcsOverlayProps {
  gridRef: RefObject<HTMLDivElement | null>;
  signature: string;
  /** Content-space y below which arcs must stay (header bottom), so the sticky header never hides them. */
  minPeakY: number;
}

type State = { w: number; h: number; arcs: { d: string; color: string }[] };

export default function EventArcsOverlay({ gridRef, signature, minPeakY }: EventArcsOverlayProps) {
  const [state, setState] = useState<State>({ w: 0, h: 0, arcs: [] });
  const lastSigRef = useRef("");

  useLayoutEffect(() => {
    let raf = 0;
    let retries = 0;
    let observer: ResizeObserver | null = null;

    const schedule = () => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(measure);
    };

    function measure() {
      // The grid div is this overlay's PARENT, whose ref attaches only after
      // this child's layout effect runs — so on first mount gridRef.current is
      // null. The grid may also be mid-layout (zero-size). Retry on later frames
      // until it's ready, instead of bailing (which left arcs undrawn until a
      // resize re-fired the effect).
      const grid = gridRef.current;
      const gridRect = grid?.getBoundingClientRect();
      if (!grid || !gridRect || gridRect.width === 0 || gridRect.height === 0) {
        if (retries < 60) {
          retries += 1;
          raf = requestAnimationFrame(measure);
        }
        return;
      }
      retries = 0;
      if (!observer) {
        observer = new ResizeObserver(schedule);
        observer.observe(grid);
      }

      const groups = new Map<string, HTMLElement[]>();
      grid.querySelectorAll<HTMLElement>("[data-arc-group]").forEach((card) => {
        const id = card.dataset.arcGroup;
        if (!id) return;
        const list = groups.get(id);
        if (list) list.push(card);
        else groups.set(id, [card]);
      });

      const arcs: { d: string; color: string }[] = [];
      groups.forEach((list) => {
        if (list.length < 2) return;
        list.sort((a, b) => Number(a.dataset.arcSeg) - Number(b.dataset.arcSeg));
        for (let i = 0; i < list.length - 1; i += 1) {
          const a = list[i]!.getBoundingClientRect();
          const b = list[i + 1]!.getBoundingClientRect();
          const x1 = (a.left + a.right) / 2 - gridRect.left;
          const y1 = a.top - gridRect.top;
          const x2 = (b.left + b.right) / 2 - gridRect.left;
          const y2 = b.top - gridRect.top;
          arcs.push({
            d: buildArcPath(x1, y1, x2, y2, minPeakY),
            color: list[i]!.dataset.arcColor ?? "#475569",
          });
        }
      });

      const w = grid.scrollWidth;
      const h = grid.scrollHeight;
      // Skip redundant writes — also breaks any ResizeObserver feedback.
      const sig = `${w}x${h}|${arcs.map((arc) => `${arc.d}~${arc.color}`).join(";")}`;
      if (sig === lastSigRef.current) return;
      lastSigRef.current = sig;
      setState({ w, h, arcs });
    }

    schedule();
    return () => {
      cancelAnimationFrame(raf);
      observer?.disconnect();
    };
  }, [gridRef, signature, minPeakY]);

  if (state.arcs.length === 0) return null;
  return (
    <svg
      className="pointer-events-none absolute left-0 top-0 z-10 overflow-visible"
      width={state.w}
      height={state.h}
      aria-hidden="true"
    >
      {state.arcs.map((arc, i) => (
        <path
          key={i}
          d={arc.d}
          fill="none"
          stroke={arc.color}
          strokeWidth={2}
          strokeLinecap="round"
        />
      ))}
    </svg>
  );
}
