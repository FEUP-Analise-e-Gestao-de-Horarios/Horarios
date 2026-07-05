import { useLayoutEffect, useRef, useState } from "react";

// Blank run between the end of the text and its wrapped-around copy.
const MARQUEE_GAP_PX = 14;

/**
 * One line of text inside an event card. When the text is wider than the
 * available space it scrolls as a circular ticker while the parent card (a
 * `group`) is hovered: the text slides out to the left while a duplicate copy
 * follows it in, so the loop wraps seamlessly instead of snapping back. The
 * cycle duration is a fixed constant in index.css, shared by every line, so
 * all marquees move on the same timeline.
 */
export default function MarqueeText({
  children,
  className = "",
}: {
  children: string;
  className?: string;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const textRef = useRef<HTMLSpanElement>(null);
  const [overflowPx, setOverflowPx] = useState(0);
  const [textWidthPx, setTextWidthPx] = useState(0);

  useLayoutEffect(() => {
    const container = containerRef.current;
    const text = textRef.current;
    if (!container || !text) return;
    const measure = () => {
      const diff = Math.ceil(text.scrollWidth - container.clientWidth);
      setOverflowPx(diff > 1 ? diff : 0);
      setTextWidthPx(Math.ceil(text.scrollWidth));
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(container);
    observer.observe(text);
    return () => observer.disconnect();
  }, [children]);

  const isOverflowing = overflowPx > 0;

  return (
    <div ref={containerRef} className={`overflow-hidden ${className}`}>
      <div
        className={`w-max whitespace-nowrap ${isOverflowing ? "marquee" : ""}`}
        style={
          isOverflowing
            ? // Shifting by one full copy (text + gap) puts the duplicate
              // exactly where the original started, so 100% == 0% visually.
              ({ "--marquee-shift": `-${textWidthPx + MARQUEE_GAP_PX}px` } as React.CSSProperties)
            : undefined
        }
      >
        <span ref={textRef} className="inline-block whitespace-nowrap">
          {children}
        </span>
        {isOverflowing && (
          <span
            aria-hidden="true"
            className="inline-block whitespace-nowrap"
            style={{ paddingLeft: `${MARQUEE_GAP_PX}px` }}
          >
            {children}
          </span>
        )}
      </div>
    </div>
  );
}
