import { useEffect, useRef, useState } from "react";

const DROPDOWN_MAX_WIDTH_PX = 768;
const DROPDOWN_CLASSES =
  "absolute left-0 bg-[#1e2028] border border-gray-600 rounded z-[200] w-max max-w-[min(calc(100vw-1rem),48rem)] max-h-[min(60vh,24rem)] overflow-x-hidden overflow-y-auto shadow-[0_4px_12px_rgba(0,0,0,0.4)]";

export type TurnoTurmaGroup = {
  turno: string;
  label: string;
  turmas: string[];
};

interface TurnoTurmaDropdownProps {
  groups: TurnoTurmaGroup[];
  selectedTurnos: string[];
  selectedTurmas: string[];
  onSelectTurnos: (turnos: string[]) => void;
  onSelectTurmas: (turmas: string[]) => void;
  open: boolean;
  onToggle: () => void;
  disabled?: boolean;
}

export default function TurnoTurmaDropdown({
  groups,
  selectedTurnos,
  selectedTurmas,
  onSelectTurnos,
  onSelectTurmas,
  open,
  onToggle,
  disabled,
}: TurnoTurmaDropdownProps) {
  const wrapperRef = useRef<HTMLDivElement>(null);
  const [openUpward, setOpenUpward] = useState(false);
  const [openLeftward, setOpenLeftward] = useState(false);

  useEffect(() => {
    if (!open || disabled) return;

    const updateDirection = () => {
      const wrapper = wrapperRef.current;
      const trigger = wrapper?.querySelector("button");
      if (!wrapper || !trigger) return;

      const rect = trigger.getBoundingClientRect();
      const spaceBelow = window.innerHeight - rect.bottom;
      const spaceAbove = rect.top;
      const dropdownWidth = Math.min(window.innerWidth - 16, DROPDOWN_MAX_WIDTH_PX);
      const spaceRight = window.innerWidth - rect.left;
      const spaceLeft = rect.right;
      setOpenUpward(spaceBelow < 280 && spaceAbove > spaceBelow);
      setOpenLeftward(spaceRight < dropdownWidth && spaceLeft > spaceRight);
    };

    updateDirection();
    window.addEventListener("resize", updateDirection);
    window.addEventListener("scroll", updateDirection, true);
    return () => {
      window.removeEventListener("resize", updateDirection);
      window.removeEventListener("scroll", updateDirection, true);
    };
  }, [disabled, open]);

  const triggerLabel = "Turmas";

  const handleToggleTurno = (turno: string) => {
    const next = selectedTurnos.includes(turno)
      ? selectedTurnos.filter((value) => value !== turno)
      : [...selectedTurnos, turno];
    onSelectTurnos(next);
  };

  const handleToggleTurma = (turma: string) => {
    const next = selectedTurmas.includes(turma)
      ? selectedTurmas.filter((value) => value !== turma)
      : [...selectedTurmas, turma];
    onSelectTurmas(next);
  };

  return (
    <div ref={wrapperRef} className="relative">
      <button
        onClick={(e) => {
          e.stopPropagation();
          if (!disabled) onToggle();
        }}
        className={[
          "bg-[#1e2028] rounded px-3.5 py-2 text-sm whitespace-nowrap text-left border transition-colors",
          disabled
            ? "text-gray-500 cursor-not-allowed border-gray-600"
            : "text-white border-gray-600 cursor-pointer hover:border-gray-400",
        ].join(" ")}
      >
        {triggerLabel}
      </button>

      {open && !disabled && (
        <div
          className={[
            DROPDOWN_CLASSES,
            openLeftward ? "right-0 left-auto" : "left-0 right-auto",
            openUpward ? "bottom-[calc(100%+4px)]" : "top-[calc(100%+4px)]",
          ].join(" ")}
        >
          {groups.length === 0 ? (
            <div className="px-3 py-3 text-[13px] text-gray-400">Sem turnos disponíveis.</div>
          ) : (
            <div className="flex flex-row items-stretch">
              {groups.map((group) => {
                const allSelected =
                  group.turmas.length > 0 &&
                  group.turmas.every((turma) => selectedTurmas.includes(turma));
                return (
                  <div
                    key={group.turno}
                    className="w-[300px] border-r border-gray-700 last:border-r-0"
                  >
                    <div
                      className={[
                        "px-2 py-1.5 border-b border-gray-700 flex items-center justify-between gap-2",
                        allSelected ? "text-amber-400" : "text-gray-400",
                      ].join(" ")}
                    >
                      <span className="text-[11px] uppercase tracking-widest">{group.label}</span>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleToggleTurno(group.turno);
                        }}
                        className={[
                          "text-[10px] px-1.5 py-0.5 rounded border cursor-pointer transition-colors",
                          allSelected
                            ? "text-amber-400 border-amber-500/30 bg-amber-400/10 hover:bg-amber-400/20"
                            : "text-gray-300 border-gray-600 hover:border-gray-400 hover:bg-white/5",
                        ].join(" ")}
                      >
                        Todas
                      </button>
                    </div>
                    <div className="grid grid-cols-4 gap-1.5 p-2">
                      {group.turmas.map((turma) => {
                        const turmaSelected = selectedTurmas.includes(turma);
                        return (
                          <button
                            key={turma}
                            onClick={(e) => {
                              e.stopPropagation();
                              handleToggleTurma(turma);
                            }}
                            className={[
                              "rounded px-2 py-1 text-[12px] cursor-pointer text-center border transition-colors whitespace-nowrap",
                              turmaSelected
                                ? "text-amber-400 bg-amber-400/10 border-amber-500/20"
                                : "text-white bg-transparent border-transparent hover:bg-white/5",
                            ].join(" ")}
                          >
                            {turma}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
