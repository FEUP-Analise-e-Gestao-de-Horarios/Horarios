import type { ConflictRecord } from "@/types/project/conflicts";

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
  return (
    <div
      className={[
        "fixed inset-0 z-50 transition-opacity",
        open ? "pointer-events-auto opacity-100" : "pointer-events-none opacity-0",
      ].join(" ")}
      aria-hidden={!open}
    >
      <button
        type="button"
        onClick={onClose}
        className="absolute inset-0 bg-black/45"
        aria-label="Fechar painel de conflitos"
      />

      <aside
        role="dialog"
        aria-modal="true"
        aria-labelledby="conflicts-drawer-title"
        className={[
          "absolute right-0 top-0 h-full w-[min(92vw,500px)] bg-[#1d2128] text-white border-l border-white/15 shadow-[-8px_0_24px_rgba(0,0,0,0.45)] transition-transform overflow-y-auto",
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
            conflicts.map((conflict) => (
              <div
                key={conflict.id}
                className="border-l-4 border-white/30 bg-white/5 rounded p-3 space-y-2"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="text-sm font-semibold text-white space-y-1">
                      {conflict.event_names.map((name, idx) => (
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
                  {conflict.conflict_reasons.map((reason, idx) => (
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
