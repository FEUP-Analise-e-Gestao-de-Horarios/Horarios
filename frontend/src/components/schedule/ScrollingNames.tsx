import { useEffect, useLayoutEffect, useRef, useState } from "react";

interface ScrollingNamesProps {
  names: string[];
  /** When set, each navigable name renders as a button that calls this. */
  onNameClick?: (index: number) => void;
  /** Whether the name at a given index is navigable. Defaults to all. */
  isNameClickable?: (index: number) => boolean;
}

/**
 * Renders a joined list of names in a single overflowing line.
 * When the text is wider than the container it scrolls back and forth
 * while the element is hovered, so the clipped part can still be read.
 */
export default function ScrollingNames({
  names,
  onNameClick,
  isNameClickable,
}: ScrollingNamesProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const textRef = useRef<HTMLSpanElement>(null);
  const [translateX, setTranslateX] = useState(0);
  const [duration, setDuration] = useState(0);
  const [hasOverflow, setHasOverflow] = useState(false);
  const activeRef = useRef(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useLayoutEffect(() => {
    if (!containerRef.current || !textRef.current) return;
    setHasOverflow(textRef.current.scrollWidth > containerRef.current.clientWidth);
  }, [names]);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  function stopLoop() {
    activeRef.current = false;
    if (timerRef.current) clearTimeout(timerRef.current);
  }

  function handleMouseEnter() {
    if (!containerRef.current || !textRef.current) return;
    const overflow = textRef.current.scrollWidth - containerRef.current.clientWidth;
    if (overflow <= 0) return;

    stopLoop();
    activeRef.current = true;

    const forwardMs = Math.max(800, (overflow / 80) * 1000);
    const backwardMs = 500;
    const pauseMs = 350;

    function goForward() {
      if (!activeRef.current) return;
      setTranslateX(-overflow);
      setDuration(forwardMs / 1000);
      timerRef.current = setTimeout(() => goBackward(), forwardMs + pauseMs);
    }

    function goBackward() {
      if (!activeRef.current) return;
      setTranslateX(0);
      setDuration(backwardMs / 1000);
      timerRef.current = setTimeout(() => goForward(), backwardMs + pauseMs);
    }

    goForward();
  }

  function handleMouseLeave() {
    stopLoop();
    setTranslateX(0);
    setDuration(0.4);
  }

  return (
    <div
      ref={containerRef}
      className="overflow-hidden"
      style={
        hasOverflow
          ? { maskImage: "linear-gradient(to right, black calc(100% - 1.5rem), transparent 100%)" }
          : undefined
      }
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      <span
        ref={textRef}
        className="text-sm font-semibold text-white whitespace-nowrap inline-block"
        style={{
          transform: `translateX(${translateX}px)`,
          transition: `transform ${duration}s ease-in-out`,
        }}
      >
        {onNameClick
          ? names.map((name, index) => {
              const clickable = isNameClickable?.(index) ?? true;
              return (
                <span key={index}>
                  {index > 0 && " · "}
                  {clickable ? (
                    <button
                      type="button"
                      onClick={() => onNameClick(index)}
                      className="underline decoration-dotted underline-offset-2 hover:text-white/80 cursor-pointer"
                    >
                      {name}
                    </button>
                  ) : (
                    name
                  )}
                </span>
              );
            })
          : names.join(" · ")}
      </span>
    </div>
  );
}
