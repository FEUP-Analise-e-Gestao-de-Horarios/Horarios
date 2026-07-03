export default function ResetModal({
  onConfirm,
  onCancel,
}: {
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-2xl shadow-2xl p-6 w-full max-w-sm mx-4">
        <h3 className="font-bold text-[#222] text-base mb-1">Tens a certeza?</h3>
        <p className="text-sm text-[#666] mb-6">
          Todas as seleções guardadas serão apagadas. Esta ação não pode ser desfeita.
        </p>
        <div className="flex flex-col gap-2">
          <button
            onClick={onConfirm}
            className="bg-red-600 text-white font-semibold px-4 py-2 rounded-lg text-sm hover:bg-red-500 transition-colors cursor-pointer"
          >
            Recomeçar
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
