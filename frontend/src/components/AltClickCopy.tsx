import { useEffect, useRef, useState } from "react";

/**
 * Global helper: Alt+click any element carrying a `data-copy-id` attribute to
 * copy that id to the clipboard instead of following its link. Mounted once at
 * the app root; entities opt in by adding `data-copy-id={entity.id}`.
 */
export default function AltClickCopy() {
  const [visible, setVisible] = useState(false);
  const timeout = useRef<ReturnType<typeof setTimeout>>(undefined);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (!e.altKey || e.button !== 0) return;
      const target = e.target as HTMLElement | null;
      const el = target?.closest<HTMLElement>("[data-copy-id]");
      const id = el?.dataset.copyId;
      if (!id) return;

      // Runs in the capture phase, so preventDefault here stops react-router's
      // <Link> from navigating (it bails when the event is defaultPrevented).
      e.preventDefault();
      void navigator.clipboard?.writeText(id);

      setVisible(true);
      clearTimeout(timeout.current);
      timeout.current = setTimeout(() => setVisible(false), 1200);
    }

    document.addEventListener("click", handleClick, true);
    return () => {
      document.removeEventListener("click", handleClick, true);
      clearTimeout(timeout.current);
    };
  }, []);

  return (
    <div
      role="status"
      aria-live="polite"
      className={`fixed bottom-6 left-1/2 -translate-x-1/2 z-[100] rounded-md bg-[#08060d] px-3 py-1.5 text-sm font-medium text-white shadow-lg transition-opacity duration-200 ${
        visible ? "opacity-100" : "pointer-events-none opacity-0"
      }`}
    >
      ID copiado
    </div>
  );
}
