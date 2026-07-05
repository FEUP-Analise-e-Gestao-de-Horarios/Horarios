/** Shown when a confirm was rejected because the candidates changed underneath. */
export default function StaleConfirmModal({
  scope,
  onDismiss,
}: {
  scope: "subject" | "all";
  onDismiss: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-2xl shadow-2xl p-6 w-full max-w-sm mx-4">
        <h3 className="font-bold text-[#222] text-base mb-1">Os candidatos mudaram</h3>
        <p className="text-sm text-[#666] mb-6">
          {scope === "all"
            ? "Os candidatos a paralelas mudaram desde que a lista foi carregada, por isso não foi possível confirmar tudo. A lista foi atualizada, revê e confirma novamente."
            : "Os candidatos a paralelas desta cadeira mudaram desde que a lista foi carregada, por isso a confirmação foi cancelada. A lista foi atualizada, verifica novamente e confirma."}
        </p>
        <button
          onClick={onDismiss}
          className="w-full bg-[#1e2028] text-white font-semibold px-4 py-2 rounded-lg text-sm hover:bg-[#2a2d37] transition-colors cursor-pointer"
        >
          Entendido
        </button>
      </div>
    </div>
  );
}
