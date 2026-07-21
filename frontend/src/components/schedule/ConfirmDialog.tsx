import { useEffect, useRef } from "react";

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  messages: string[];
  confirmLabel?: string;
  cancelLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
}

/** Blocking yes/no dialog confirming a move or an edit warning. */
export default function ConfirmDialog({
  open,
  title,
  messages,
  confirmLabel = "Confirmar",
  cancelLabel = "Cancelar",
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const confirmRef = useRef<HTMLButtonElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!open) return;
    previousFocusRef.current = document.activeElement as HTMLElement | null;
    confirmRef.current?.focus();

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onCancel();
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      previousFocusRef.current?.focus();
    };
  }, [open, onCancel]);

  return (
    <div
      inert={!open}
      className={[
        "fixed inset-0 z-[60] flex items-center justify-center transition-opacity",
        open ? "pointer-events-auto opacity-100" : "pointer-events-none opacity-0",
      ].join(" ")}
    >
      <div aria-hidden="true" onClick={onCancel} className="absolute inset-0 bg-black/55" />

      <div
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-dialog-title"
        className="relative w-[min(92vw,400px)] rounded-lg border border-white/15 bg-[#1d2128] text-white shadow-[0_8px_32px_rgba(0,0,0,0.5)]"
      >
        <div className="border-b border-white/10 px-5 py-4">
          <h2 id="confirm-dialog-title" className="text-base font-semibold">
            {title}
          </h2>
        </div>
        <div className="px-5 py-4 space-y-2 text-sm text-white/85">
          {messages.map((message) => (
            <p key={message} className="flex items-start gap-2">
              <span aria-hidden="true">⚠</span>
              <span>{message}</span>
            </p>
          ))}
        </div>
        <div className="flex justify-end gap-2 border-t border-white/10 px-5 py-4">
          <button
            type="button"
            onClick={onCancel}
            className="rounded border border-white/20 px-3 py-1.5 text-sm text-white/80 hover:text-white"
          >
            {cancelLabel}
          </button>
          <button
            ref={confirmRef}
            type="button"
            onClick={onConfirm}
            className="rounded bg-[#c73f24] px-3 py-1.5 text-sm font-semibold text-white hover:bg-[#b3361f] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#c73f24]"
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
