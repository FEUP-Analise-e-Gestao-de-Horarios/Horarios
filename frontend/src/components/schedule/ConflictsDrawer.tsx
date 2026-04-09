import { ALL_CONFLICTS } from "@/components/schedule/data";
import { useEffect, useRef } from "react";

interface ConflictsDrawerProps {
  open: boolean;
  onClose: () => void;
}

export default function ConflictsDrawer({ open, onClose }: ConflictsDrawerProps) {
  const drawerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleOutsideClick(event: MouseEvent) {
      if (drawerRef.current?.contains(event.target as Node)) return;
      onClose();
    }

    if (open) {
      document.addEventListener("mousedown", handleOutsideClick);
      return () => document.removeEventListener("mousedown", handleOutsideClick);
    }
  }, [open, onClose]);

  return (
    <div
      className={[
        "fixed inset-0 z-50 transition-opacity",
        open ? "pointer-events-auto opacity-100" : "pointer-events-none opacity-0",
      ].join(" ")}
      aria-hidden={!open}
    >
      <button
        onClick={onClose}
        className="absolute inset-0 bg-black/45"
        aria-label="Fechar painel de conflitos"
      />

      <aside
        ref={drawerRef}
        className={[
          "absolute right-0 top-0 h-full w-[min(92vw,500px)] bg-[#1d2128] text-white border-l border-white/15 shadow-[-8px_0_24px_rgba(0,0,0,0.45)] transition-transform overflow-y-auto",
          open ? "translate-x-0" : "translate-x-full",
        ].join(" ")}
      >
        <div className="sticky top-0 bg-[#1d2128] border-b border-white/10 px-5 py-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Conflitos</h2>
          <button
            onClick={onClose}
            className="text-white/80 hover:text-white border border-white/20 rounded px-2 py-1 text-sm"
          >
            Fechar
          </button>
        </div>

        <div className="px-5 py-4 space-y-4">
          {ALL_CONFLICTS.length === 0 ? (
            <p className="text-white/60 text-center py-8">Sem conflitos</p>
          ) : (
            ALL_CONFLICTS.map((conflict) => (
              <div
                key={conflict.id}
                className="border-l-4 border-white/30 bg-white/5 rounded p-3 space-y-2"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="text-sm font-semibold text-white space-y-1">
                      {conflict.eventNames.map((name, idx) => (
                        <p key={idx} className="line-clamp-1">
                          {name}
                        </p>
                      ))}
                    </div>
                    <p className="text-xs text-white/70 mt-1">
                      {conflict.day} às {conflict.time} — Turma: {conflict.turma}
                    </p>
                  </div>
                </div>

                <div className="space-y-1 pt-2 border-t border-white/10">
                  {conflict.conflictReasons.map((reason, idx) => (
                    <p key={idx} className="text-xs text-white/80 flex items-start gap-2">
                      <span className="text-white/60 mt-0.5">•</span>
                      <span>{reason}</span>
                    </p>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
      </aside>
    </div>
  );
}
