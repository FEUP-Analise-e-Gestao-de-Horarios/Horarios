import { useState } from "react";
import type { ReactNode } from "react";
import { createPortal } from "react-dom";

export default function StyledTooltip({
  content,
  children,
}: {
  content?: string;
  children: ReactNode;
}) {
  const [position, setPosition] = useState<{ x: number; y: number } | null>(null);

  if (!content) return children;

  function showTooltip(target: EventTarget | null) {
    if (!(target instanceof HTMLElement)) return;
    const rect = target.getBoundingClientRect();
    setPosition({ x: rect.left + rect.width / 2, y: rect.top });
  }

  const lines = content.split("\n").filter(Boolean);

  return (
    <span
      className="inline-flex max-w-full"
      onMouseEnter={(event) => showTooltip(event.currentTarget)}
      onMouseLeave={() => setPosition(null)}
      onFocus={(event) => showTooltip(event.currentTarget)}
      onBlur={() => setPosition(null)}
    >
      {children}
      {position &&
        createPortal(
          <div
            role="tooltip"
            className="pointer-events-none fixed z-50 max-w-xs -translate-x-1/2 -translate-y-full rounded-md border border-[#2f3037] bg-[#1e2028] px-3 py-2 text-left text-xs leading-5 text-white shadow-[0_10px_30px_rgba(0,0,0,0.25)]"
            style={{ left: position.x, top: position.y - 8 }}
          >
            {lines.map((line, index) => {
              const [label, ...rest] = line.split(": ");
              const value = rest.join(": ");

              return (
                <div key={`${line}-${index}`} className="grid grid-cols-[auto_1fr] gap-x-2">
                  {value ? (
                    <>
                      <span className="font-semibold text-[#f1c9bc]">{label}:</span>
                      <span className="break-words text-white">{value}</span>
                    </>
                  ) : (
                    <span className="col-span-2 break-words text-white">{line}</span>
                  )}
                </div>
              );
            })}
          </div>,
          document.body,
        )}
    </span>
  );
}
