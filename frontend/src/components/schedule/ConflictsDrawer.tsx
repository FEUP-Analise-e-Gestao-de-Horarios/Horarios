import { useEffect, useRef } from "react";
import type { ConflictRecord } from "@/types/project/conflicts";
import ConflictCard from "./ConflictCard";

interface ConflictsDrawerProps {
  open: boolean;
  onClose: () => void;
  conflicts?: ConflictRecord[];
  isLoading?: boolean;
  onRefresh?: () => void;
}

export default function ConflictsDrawer({
  open,
  onClose,
  conflicts = [],
  isLoading = false,
  onRefresh,
}: ConflictsDrawerProps) {
  const asideRef = useRef<HTMLElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!open) return;
    // Save the focused element so we can restore focus when the drawer
    // closes, and move focus into the dialog now that it's visible.
    previousFocusRef.current = document.activeElement as HTMLElement | null;
    asideRef.current?.focus();

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      previousFocusRef.current?.focus();
    };
  }, [open, onClose]);

  return (
    <div
      // `inert` excludes the subtree from the focus and accessibility trees
      // while the drawer is closed, so the close button etc. don't sit inside
      // an `aria-hidden` ancestor with focusable descendants (an axe
      // violation) and aren't reachable via Tab when the drawer is hidden.
      inert={!open}
      className={[
        "fixed inset-0 z-50 transition-opacity",
        open ? "pointer-events-auto opacity-100" : "pointer-events-none opacity-0",
      ].join(" ")}
    >
      <div aria-hidden="true" onClick={onClose} className="absolute inset-0 bg-black/45" />

      <aside
        ref={asideRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="conflicts-drawer-title"
        tabIndex={-1}
        className={[
          "absolute right-0 top-0 h-full w-[min(92vw,500px)] bg-[#1d2128] text-white border-l border-white/15 shadow-[-8px_0_24px_rgba(0,0,0,0.45)] transition-transform overflow-y-auto focus:outline-none",
          open ? "translate-x-0" : "translate-x-full",
        ].join(" ")}
      >
        <div className="sticky top-0 bg-[#1d2128] border-b border-white/10 px-5 py-4 flex items-center justify-between">
          <h2 id="conflicts-drawer-title" className="text-lg font-semibold">
            Conflitos
          </h2>
          <div className="flex items-center gap-2">
            {onRefresh ? (
              <button
                type="button"
                onClick={onRefresh}
                disabled={isLoading}
                className="text-white/80 hover:text-white border border-white/20 rounded px-2 py-1 text-sm flex items-center gap-2"
              >
                {isLoading ? (
                  <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
                    <circle
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                      strokeOpacity="0.2"
                    />
                    <path
                      d="M22 12a10 10 0 00-10-10"
                      stroke="currentColor"
                      strokeWidth="4"
                      strokeLinecap="round"
                    />
                  </svg>
                ) : null}
                <span>{isLoading ? "A atualizar" : "Atualizar"}</span>
              </button>
            ) : null}

            <button
              type="button"
              onClick={onClose}
              className="text-white/80 hover:text-white border border-white/20 rounded px-2 py-1 text-sm"
            >
              Fechar
            </button>
          </div>
        </div>

        <div className="px-5 py-4 space-y-4">
          {isLoading ? (
            <p className="text-white/60 text-center py-8">A carregar conflitos…</p>
          ) : conflicts.length === 0 ? (
            <p className="text-white/60 text-center py-8">Sem conflitos</p>
          ) : (
            conflicts.map((conflict) => <ConflictCard key={conflict.id} conflict={conflict} />)
          )}
        </div>
      </aside>
    </div>
  );
}
