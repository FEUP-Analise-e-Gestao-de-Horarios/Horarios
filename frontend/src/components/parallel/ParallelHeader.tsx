import MainNavMenu from "@/components/nav/MainNavMenu";

export default function ParallelHeader({
  saving,
  onNavigateHome,
  onNavigateDashboard,
  onBack,
  onReset,
  onFinish,
}: {
  saving: boolean;
  onNavigateHome: () => void;
  onNavigateDashboard: () => void;
  onBack: () => void;
  onReset: () => void;
  onFinish: () => void;
}) {
  return (
    <header className="shrink-0 sticky top-0 z-50 px-6 py-3 bg-[#1e2028] flex items-center gap-2 w-full flex-wrap border-b border-gray-700">
      <MainNavMenu
        items={[
          { key: "paralelas", label: "Aulas em Paralelo", current: true },
          { key: "horario", label: "Horário", onClick: onBack },
          { key: "dados", label: "Dados", onClick: onNavigateDashboard },
          { key: "inicio", label: "Início", onClick: onNavigateHome },
        ]}
      />

      <div className="ml-auto flex items-center gap-2">
        <button
          onClick={onReset}
          disabled={saving}
          className="bg-transparent text-red-400 font-semibold px-3.5 py-2 rounded text-sm whitespace-nowrap border border-red-400 hover:bg-red-400/10 transition-colors disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
        >
          Recomeçar
        </button>
        <button
          type="button"
          onClick={onFinish}
          disabled={saving}
          aria-busy={saving}
          className="bg-emerald-600 text-white font-semibold px-3.5 py-2 rounded text-sm whitespace-nowrap text-center min-w-[110px] hover:bg-emerald-500 transition-colors disabled:opacity-70 disabled:cursor-not-allowed cursor-pointer"
        >
          {saving ? (
            <span className="flex h-5 items-center justify-center gap-1" aria-label="A guardar">
              <span className="w-1.5 h-1.5 rounded-full bg-white animate-bounce [animation-delay:-0.3s]" />
              <span className="w-1.5 h-1.5 rounded-full bg-white animate-bounce [animation-delay:-0.15s]" />
              <span className="w-1.5 h-1.5 rounded-full bg-white animate-bounce" />
            </span>
          ) : (
            "Terminar"
          )}
        </button>
      </div>
    </header>
  );
}
