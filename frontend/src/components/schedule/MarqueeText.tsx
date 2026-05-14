import { useLayoutEffect, useRef, useState } from "react";

// Marquee scroll speed in pixels per second. The animation duration is derived
// from this and the overflow distance, so text always scrolls at this exact
// rate regardless of how much it overflows.
const MARQUEE_SPEED_PX_PER_SEC = 9;

/**
 * One line of text inside an event card. When the text is wider than the
 * available space it scrolls back and forth while the parent card (a `group`)
 * is hovered, so the clipped part can still be read.
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

  useLayoutEffect(() => {
    const container = containerRef.current;
    const text = textRef.current;
    if (!container || !text) return;
    const measure = () => {
      const diff = Math.ceil(text.scrollWidth - container.clientWidth);
      setOverflowPx(diff > 1 ? diff : 0);
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
      <span
        ref={textRef}
        className={`inline-block whitespace-nowrap ${isOverflowing ? "marquee" : ""}`}
        style={
          isOverflowing
            ? ({
                "--marquee-shift": `-${overflowPx}px`,
                "--marquee-duration": `${overflowPx / MARQUEE_SPEED_PX_PER_SEC}s`,
              } as React.CSSProperties)
            : undefined
        }
      >
        {children}
      </span>
    </div>
  );
}
