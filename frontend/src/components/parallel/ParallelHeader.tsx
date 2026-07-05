export default function ParallelHeader({
  saving,
  onNavigateHome,
  onBack,
  onReset,
  onFinish,
}: {
  saving: boolean;
  onNavigateHome: () => void;
  onBack: () => void;
  onReset: () => void;
  onFinish: () => void;
}) {
  return (
    <header className="shrink-0 sticky top-0 z-50 px-6 py-3 bg-[#1e2028] flex items-center gap-2 w-full flex-wrap border-b border-gray-700">
      <button
        onClick={onNavigateHome}
        className="bg-[#8c2d19] text-white font-semibold px-3.5 py-2 rounded text-sm whitespace-nowrap hover:bg-[#a33520] transition-colors cursor-pointer"
      >
        Início
      </button>
      <button
        onClick={onBack}
        className="bg-transparent text-white font-semibold px-3.5 py-2 rounded text-sm whitespace-nowrap border border-gray-600 transition-colors hover:border-gray-400 hover:bg-white/5 cursor-pointer"
      >
        Horário
      </button>

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
