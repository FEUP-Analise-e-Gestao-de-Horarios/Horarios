import { useId } from "react";
import DropdownShell from "./DropdownShell";

const TURNO_TURMA_PANEL_CLASS =
  "w-max max-w-[min(calc(100vw-1rem),48rem)] max-h-[min(60vh,24rem)] overflow-x-hidden overflow-y-auto";

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
  const baseId = useId();
  const panelId = `${baseId}-panel`;
  const totalTurmas = groups.reduce((sum, group) => sum + group.turmas.length, 0);
  const triggerLabel =
    totalTurmas === 0 ? "Turmas" : `Turmas (${selectedTurmas.length}/${totalTurmas})`;
  const isOpen = open && !disabled;

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
    <DropdownShell
      open={isOpen}
      panelClassName={TURNO_TURMA_PANEL_CLASS}
      panelId={panelId}
      panelAriaMultiSelectable
      trigger={
        <button
          type="button"
          aria-haspopup="listbox"
          aria-expanded={isOpen}
          aria-controls={panelId}
          aria-disabled={disabled || undefined}
          aria-label={`Turnos e turmas: ${triggerLabel}`}
          onClick={(e) => {
            e.stopPropagation();
            if (!disabled) onToggle();
          }}
          className={[
            "bg-[#1e2028] rounded px-3.5 py-2 text-sm whitespace-nowrap text-left border transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400/60",
            disabled
              ? "text-gray-500 cursor-not-allowed border-gray-600"
              : "text-white border-gray-600 cursor-pointer hover:border-gray-400",
          ].join(" ")}
        >
          {triggerLabel}
        </button>
      }
    >
      {groups.length === 0 ? (
        <div className="px-3 py-3 text-[13px] text-gray-400">Sem turnos disponíveis.</div>
      ) : (
        <div className="flex flex-row items-stretch">
          {groups.map((group, groupIndex) => {
            const headingId = `${baseId}-group-${groupIndex}`;
            const allSelected =
              group.turmas.length > 0 &&
              group.turmas.every((turma) => selectedTurmas.includes(turma));
            return (
              <div
                key={group.turno}
                role="group"
                aria-labelledby={headingId}
                className="border-r border-gray-700 last:border-r-0"
              >
                <div
                  className={[
                    "px-2 py-1.5 border-b border-gray-700 flex items-center justify-between gap-2",
                    allSelected ? "text-amber-400" : "text-gray-400",
                  ].join(" ")}
                >
                  <span id={headingId} className="text-[11px] uppercase tracking-widest">
                    {group.label}
                  </span>
                  <button
                    type="button"
                    aria-pressed={allSelected}
                    aria-label={`Alternar todas as turmas do ${group.label}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleToggleTurno(group.turno);
                    }}
                    className={[
                      "text-[10px] px-1.5 py-0.5 rounded border cursor-pointer transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400/60",
                      allSelected
                        ? "text-amber-400 border-amber-500/30 bg-amber-400/10 hover:bg-amber-400/20"
                        : "text-gray-300 border-gray-600 hover:border-gray-400 hover:bg-white/5",
                    ].join(" ")}
                  >
                    Todas
                  </button>
                </div>
                <div
                  className="grid gap-1.5 p-2"
                  style={{
                    gridTemplateColumns: `repeat(${Math.max(
                      1,
                      Math.ceil(group.turmas.length / 4),
                    )}, max-content)`,
                  }}
                >
                  {group.turmas.map((turma) => {
                    const turmaSelected = selectedTurmas.includes(turma);
                    return (
                      <button
                        key={turma}
                        type="button"
                        role="option"
                        aria-selected={turmaSelected}
                        onClick={(e) => {
                          e.stopPropagation();
                          handleToggleTurma(turma);
                        }}
                        className={[
                          "rounded px-2 py-1 text-[12px] cursor-pointer text-center border transition-colors whitespace-nowrap focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400/60",
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
    </DropdownShell>
  );
}
