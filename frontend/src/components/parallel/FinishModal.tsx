import type { DegreeOption, YearOption } from "@/types/parallelSessions";

/** Shown on Terminar when some years still have unconfirmed subjects. */
export default function FinishModal({
  unconfirmedByDegree,
  onConfirmAll,
  onContinue,
  onCancel,
}: {
  unconfirmedByDegree: { degree: DegreeOption; years: YearOption[] }[];
  onConfirmAll: () => void;
  onContinue: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-2xl shadow-2xl p-6 w-full max-w-md mx-4">
        <h3 className="font-bold text-[#222] text-base mb-1">Ainda há anos por confirmar</h3>
        <p className="text-sm text-[#666] mb-3">Os seguintes anos ainda não foram confirmados:</p>
        <div className="mb-6 max-h-56 overflow-y-auto rounded-lg border border-[#eee] bg-[#fafafa] px-3 py-2 [&::-webkit-scrollbar]:w-1 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-gray-300/60">
          {unconfirmedByDegree.map(({ degree, years }) => (
            <div key={degree.id} className="py-1">
              <span className="text-[13px] font-bold text-[#333]">{degree.acronym}</span>
              <span className="text-[13px] text-[#666]">
                {" — "}
                {years.map((y) => `${y.number}º`).join(", ")} ano
              </span>
            </div>
          ))}
        </div>
        <div className="flex flex-col gap-2">
          <button
            onClick={onConfirmAll}
            className="bg-emerald-600 text-white font-semibold px-4 py-2 rounded-lg text-sm hover:bg-emerald-500 transition-colors cursor-pointer"
          >
            Confirmar tudo e terminar
          </button>
          <button
            onClick={onContinue}
            className="border border-[#ddd] text-[#444] font-semibold px-4 py-2 rounded-lg text-sm hover:bg-gray-100 transition-colors cursor-pointer"
          >
            Continuar sem confirmar
          </button>
          <button
            onClick={onCancel}
            className="text-[#666] font-semibold px-4 py-2 rounded-lg text-sm hover:bg-gray-100 transition-colors cursor-pointer"
          >
            Cancelar
          </button>
        </div>
      </div>
    </div>
  );
}
