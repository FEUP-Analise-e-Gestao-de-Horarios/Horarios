import type { UnconfirmedDegree } from "@/types/parallelSessions";

/** Shown on Terminar when some years still have unconfirmed subjects. */
export default function FinishModal({
  unconfirmedByDegree,
  onConfirmAll,
  onContinue,
  onContinueLater,
  onCancel,
}: {
  unconfirmedByDegree: UnconfirmedDegree[];
  onConfirmAll: () => void;
  onContinue: () => void;
  onContinueLater: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-2xl shadow-2xl p-6 w-full max-w-md mx-4">
        <h3 className="font-bold text-[#222] text-base mb-1">Ainda há anos por confirmar</h3>
        <p className="text-sm text-[#666] mb-3">
          As seguintes disciplinas ainda não foram confirmadas:
        </p>
        <div className="mb-6 max-h-56 overflow-y-auto rounded-lg border border-[#eee] bg-[#fafafa] [&::-webkit-scrollbar]:w-1 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-gray-300/60">
          <table className="w-full border-collapse text-left">
            <thead className="sticky top-0 bg-[#f0efec]">
              <tr className="text-[10px] font-semibold uppercase tracking-wide text-[#999]">
                <th className="px-3 py-1.5">Curso</th>
                <th className="px-3 py-1.5">Ano</th>
                <th className="px-3 py-1.5">Disciplinas</th>
              </tr>
            </thead>
            <tbody>
              {unconfirmedByDegree.map(({ degree, years }) =>
                years.map((year, i) => (
                  <tr
                    key={year.id}
                    className={`align-top ${
                      i === 0 ? "border-t border-[#bbb]" : "border-t border-[#eee]"
                    }`}
                  >
                    {i === 0 && (
                      <td
                        rowSpan={years.length}
                        className="border-r border-[#eee] px-3 py-1.5 text-[13px] font-bold text-[#333] whitespace-nowrap align-top"
                      >
                        {degree.acronym}
                      </td>
                    )}
                    <td className="border-r border-[#eee] px-3 py-1.5 text-[13px] text-[#555] whitespace-nowrap">
                      {year.number}º
                    </td>
                    <td className="px-3 py-1.5 text-[13px] text-[#666]">
                      {year.subjects.length > 0
                        ? year.subjects.map((s) => s.acronym).join(", ")
                        : "—"}
                    </td>
                  </tr>
                )),
              )}
            </tbody>
          </table>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <button
            onClick={onContinue}
            className="flex min-h-[3.25rem] items-center justify-center rounded-lg bg-sky-600 px-4 py-2 text-center text-sm font-semibold leading-tight text-white transition-colors hover:bg-sky-500 cursor-pointer"
          >
            Terminar sem confirmar tudo
          </button>
          <button
            onClick={onContinueLater}
            className="flex min-h-[3.25rem] items-center justify-center rounded-lg bg-amber-500 px-4 py-2 text-center text-sm font-semibold leading-tight text-white transition-colors hover:bg-amber-400 cursor-pointer"
          >
            Continuar mais tarde
          </button>
          <button
            onClick={onConfirmAll}
            className="flex min-h-[3.25rem] items-center justify-center rounded-lg bg-emerald-600 px-4 py-2 text-center text-sm font-semibold leading-tight text-white transition-colors hover:bg-emerald-500 cursor-pointer"
          >
            Confirmar tudo e terminar
          </button>
          <button
            onClick={onCancel}
            className="flex min-h-[3.25rem] items-center justify-center rounded-lg bg-gray-200 px-4 py-2 text-center text-sm font-semibold leading-tight text-[#444] transition-colors hover:bg-gray-300 cursor-pointer"
          >
            Cancelar
          </button>
        </div>
      </div>
    </div>
  );
}
