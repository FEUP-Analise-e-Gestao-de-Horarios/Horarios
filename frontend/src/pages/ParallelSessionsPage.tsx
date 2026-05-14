import { useParallelSessions } from "@/api/hooks/useParallelSessions";
import type { DisplayCandidate } from "@/types/parallelSessions";

const DAY_CONFIG: Record<string, { short: string; bg: string; text: string }> = {
  monday: { short: "SEG", bg: "bg-blue-500", text: "text-white" },
  tuesday: { short: "TER", bg: "bg-emerald-500", text: "text-white" },
  wednesday: { short: "QUA", bg: "bg-violet-500", text: "text-white" },
  thursday: { short: "QUI", bg: "bg-orange-500", text: "text-white" },
  friday: { short: "SEX", bg: "bg-rose-500", text: "text-white" },
};

const SESSION_TYPE_CONFIG: Record<string, { bg: string; text: string }> = {
  TP: { bg: "bg-blue-100", text: "text-blue-700" },
  OT: { bg: "bg-violet-100", text: "text-violet-700" },
  PL: { bg: "bg-emerald-100", text: "text-emerald-700" },
  T: { bg: "bg-orange-100", text: "text-orange-700" },
  S: { bg: "bg-rose-100", text: "text-rose-700" },
};
const SESSION_TYPE_DEFAULT = { bg: "bg-gray-100", text: "text-gray-600" };

function formatWeekDate(dateStr: string): string {
  const parts = dateStr.split("-");
  return `${parts[2]}/${parts[1]}`;
}

function formatTime(t: number): string {
  const s = String(t).padStart(4, "0");
  return `${s.slice(0, 2)}:${s.slice(2)}`;
}

interface DarkPillProps {
  label: string;
  active: boolean;
  onClick: () => void;
}

function DarkPill({ label, active, onClick }: DarkPillProps) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-1.5 rounded-full text-sm font-semibold border cursor-pointer transition-all whitespace-nowrap ${
        active
          ? "bg-[#ffc107] border-[#b8860b] text-[#222]"
          : "bg-transparent border-gray-600 text-gray-300 hover:border-gray-400 hover:bg-white/5"
      }`}
    >
      {label}
    </button>
  );
}

function HeaderPillSkeleton() {
  return (
    <>
      {[1, 2, 3].map((i) => (
        <div key={i} className="h-8 w-16 rounded-full bg-gray-700 animate-pulse" />
      ))}
    </>
  );
}

function CandidatesLoadingSkeleton() {
  return (
    <div className="flex flex-col gap-3">
      {[1, 2, 3].map((i) => (
        <div key={i} className="h-12 rounded-xl bg-[#e8e8e8] animate-pulse" />
      ))}
    </div>
  );
}

export default function ParallelClassesPage() {
  const {
    loadingDegrees,
    degreesError,
    selectedDegree,
    showAllDegrees,
    setShowAllDegrees,
    priorityDegrees,
    otherDegrees,
    loadingYears,
    yearsError,
    selectedYearIds,
    yearsWithCandidates,
    loadingCandidates,
    candidatesError,
    filteredCandidates,
    candidatesBySubject,
    groupsBySubject,
    pendingSelection,
    saving,
    saveStatus,
    showUnsavedModal,
    setShowUnsavedModal,
    showResetModal,
    setShowResetModal,
    handleDegreeClick,
    handleYearToggle,
    handleSessionPendingToggle,
    handleSelectAllForCandidate,
    handleCreateGroup,
    handleRemoveGroup,
    handleBack,
    handleSave,
    handleSaveAndExit,
    handleExitWithoutSaving,
    handleReset,
    confirmReset,
  } = useParallelSessions();

  const renderRow = (candidate: DisplayCandidate, rowIdx: number, hasWeeks: boolean) => {
    const sessions = candidate.sessions ?? [];
    const selectedInRow = sessions
      .map((s) => s.original_block_id)
      .filter((id) => pendingSelection.has(id));
    const day = DAY_CONFIG[candidate.session_weekday ?? ""] ?? {
      short: "?",
      bg: "bg-gray-400",
      text: "text-white",
    };
    return (
      <tr
        key={candidate.id}
        className={`bg-white hover:bg-[#fffdf5] transition-colors ${rowIdx > 0 ? "border-t border-[#f0f0f0]" : ""}`}
      >
        <td className="px-3 py-3 align-top">
          <div className="flex flex-col items-start gap-0.5">
            <span
              className={`text-[10px] font-bold tracking-wider px-2 py-0.5 rounded-md ${day.bg} ${day.text}`}
            >
              {day.short}
            </span>
            {!hasWeeks && candidate.showWeek && candidate.displayWeeks.length > 0 && (
              <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded bg-gray-200 text-gray-600 whitespace-nowrap tabular-nums">
                {candidate.displayWeeks.length > 1
                  ? candidate.displayWeeks.map(formatWeekDate).join(", ")
                  : formatWeekDate(candidate.displayWeeks[0] ?? "")}
              </span>
            )}
          </div>
        </td>
        <td className="px-3 py-3 align-top font-bold text-[#333] tabular-nums whitespace-nowrap">
          {candidate.session_start_time != null ? formatTime(candidate.session_start_time) : "—"}
        </td>
        <td className="px-4 py-3">
          <div className="flex flex-col gap-1.5">
            {sessions.map((session) => {
              const checked = pendingSelection.has(session.original_block_id);
              const typeLabel = session.session_type ?? null;
              const typeStyle = typeLabel
                ? (SESSION_TYPE_CONFIG[typeLabel] ?? SESSION_TYPE_DEFAULT)
                : null;
              const pills = (
                <div className="flex items-center gap-1">
                  {typeLabel && typeStyle && (
                    <span
                      className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${typeStyle.bg} ${typeStyle.text}`}
                    >
                      {typeLabel}
                    </span>
                  )}
                  {session.class_codes.map((code: string) => (
                    <span
                      key={`${session.original_block_id}-${code}`}
                      className={`rounded px-2 py-0.5 text-[12px] font-semibold transition-colors ${
                        checked ? "bg-[#ffc107] text-[#222]" : "bg-[#f0f0f0] text-[#666]"
                      }`}
                    >
                      {code}
                    </span>
                  ))}
                </div>
              );
              return sessions.length > 1 ? (
                <label
                  key={session.original_block_id}
                  className="flex items-center gap-1.5 cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => handleSessionPendingToggle(session.original_block_id)}
                    className="w-3.5 h-3.5 accent-[#ffc107] cursor-pointer shrink-0"
                  />
                  {pills}
                </label>
              ) : (
                <div key={session.original_block_id}>{pills}</div>
              );
            })}
            {sessions.length > 1 && (
              <div className="flex items-center justify-between mt-0.5">
                <label className="flex items-center gap-1.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={
                      sessions.length > 0 &&
                      sessions.every((s) => pendingSelection.has(s.original_block_id))
                    }
                    onChange={() => handleSelectAllForCandidate(sessions)}
                    className="w-3.5 h-3.5 accent-[#ffc107] cursor-pointer shrink-0"
                  />
                  <span className="text-[11px] text-[#999] font-semibold whitespace-nowrap">
                    selecionar todas
                  </span>
                </label>
                {selectedInRow.length >= 2 && (
                  <button
                    onClick={() => handleCreateGroup(selectedInRow, candidate)}
                    className="ml-3 bg-[#1e2028] text-white font-semibold px-3 py-1 rounded-lg text-[11px] hover:bg-[#2a2d37] transition-colors whitespace-nowrap cursor-pointer"
                  >
                    Criar Grupo
                  </button>
                )}
              </div>
            )}
          </div>
        </td>
      </tr>
    );
  };

  return (
    <div className="h-screen flex flex-col bg-[#f0eeeb]">
      <header className="shrink-0 sticky top-0 z-50 px-6 py-3 bg-[#1e2028] flex items-center gap-2 w-full flex-wrap border-b border-gray-700">
        <button
          onClick={handleBack}
          className="bg-[#8c2d19] text-white font-semibold px-3.5 py-2 rounded text-sm whitespace-nowrap hover:bg-[#a33520] transition-colors cursor-pointer"
        >
          ← Voltar
        </button>

        <div className="w-px h-6 bg-gray-600 mx-1" />

        <span className="text-[11px] font-bold tracking-widest uppercase text-gray-400 whitespace-nowrap">
          Curso
        </span>

        {loadingDegrees ? (
          <HeaderPillSkeleton />
        ) : degreesError ? (
          <span className="text-xs text-red-400">{degreesError}</span>
        ) : (
          <>
            {priorityDegrees.map((d) => (
              <DarkPill
                key={d.id}
                label={d.acronym}
                active={selectedDegree?.id === d.id}
                onClick={() => handleDegreeClick(d)}
              />
            ))}
            {showAllDegrees &&
              otherDegrees.map((d) => (
                <DarkPill
                  key={d.id}
                  label={d.acronym}
                  active={selectedDegree?.id === d.id}
                  onClick={() => handleDegreeClick(d)}
                />
              ))}
            {otherDegrees.length > 0 && (
              <button
                onClick={() => setShowAllDegrees((prev) => !prev)}
                className="px-3 py-1.5 rounded-full text-sm font-semibold border cursor-pointer transition-all whitespace-nowrap bg-transparent border-gray-600 text-gray-300 hover:border-gray-400 hover:bg-white/5"
              >
                {showAllDegrees ? "Menos ▲" : `+${otherDegrees.length} ▼`}
              </button>
            )}
          </>
        )}

        {selectedDegree && (
          <>
            <div className="w-px h-6 bg-gray-600 mx-1" />
            <span className="text-[11px] font-bold tracking-widests uppercase text-gray-400 whitespace-nowrap">
              Ano
            </span>
            {loadingYears ? (
              <HeaderPillSkeleton />
            ) : yearsError ? (
              <span className="text-xs text-red-400">{yearsError}</span>
            ) : (
              yearsWithCandidates.map((y) => (
                <DarkPill
                  key={y.id}
                  label={`${y.number}º Ano`}
                  active={selectedYearIds.has(y.id)}
                  onClick={() => handleYearToggle(y.id)}
                />
              ))
            )}
          </>
        )}

        <div className="ml-auto flex items-center gap-2">
          {saveStatus && (
            <span
              className={`text-xs font-semibold ${saveStatus.type === "success" ? "text-green-400" : "text-red-400"}`}
            >
              {saveStatus.message}
            </span>
          )}
          <button
            onClick={handleReset}
            disabled={saving}
            className="bg-transparent text-red-400 font-semibold px-3.5 py-2 rounded text-sm whitespace-nowrap border border-red-400 hover:bg-red-400/10 transition-colors disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
          >
            Recomeçar
          </button>
          <button
            onClick={() => void handleSave()}
            disabled={saving}
            className="bg-[#ffc107] text-[#222] font-semibold px-3.5 py-2 rounded text-sm whitespace-nowrap hover:bg-[#e6ad06] transition-colors disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
          >
            {saving ? "A guardar..." : "Guardar"}
          </button>
        </div>
      </header>

      <div className="flex-1 overflow-hidden">
        {!selectedDegree ? (
          <p className="text-sm text-[#aaa] text-center mt-16">
            Seleciona um curso para ver as sessões em paralelo.
          </p>
        ) : (
          <div className="h-full max-w-6xl mx-auto px-6 pt-6 flex gap-6">
            {/* Left column: Por selecionar */}
            <div className="flex-1 min-w-0 flex flex-col min-h-0">
              <h2 className="font-bold text-[#333] text-base mb-3 shrink-0">Por selecionar</h2>
              <div className="flex-1 overflow-y-auto pb-6 [&::-webkit-scrollbar]:w-1 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-gray-300/60">
                {loadingCandidates ? (
                  <CandidatesLoadingSkeleton />
                ) : candidatesError ? (
                  <p className="text-sm text-red-600">{candidatesError}</p>
                ) : !filteredCandidates.length ? (
                  <p className="text-sm text-[#aaa]">Sem sessões em paralelo.</p>
                ) : candidatesBySubject.size === 0 ? (
                  <p className="text-xs text-[#aaa] text-center py-8">
                    Todas as sessões foram atribuídas a grupos.
                  </p>
                ) : (
                  <div className="flex flex-col gap-4">
                    {[...candidatesBySubject.entries()]
                      .sort(([a], [b]) => a.localeCompare(b))
                      .map(([subjectName, candidates]) => {
                        const hasWeeks = candidates.some((c) => c.showWeek);

                        const weekMap = new Map<string, DisplayCandidate[]>();
                        for (const c of candidates) {
                          const weekKey = c.displayWeeks[0] ?? "";
                          const list = weekMap.get(weekKey);
                          if (list) list.push(c);
                          else weekMap.set(weekKey, [c]);
                        }
                        const sortedWeeks = [...weekMap.keys()].sort();

                        return (
                          <div
                            key={subjectName}
                            className="overflow-hidden rounded-2xl border border-[#e8e8e8] shadow-sm"
                          >
                            <div className="px-4 py-2.5 bg-[#fafafa] border-b border-[#e8e8e8]">
                              <p className="font-semibold text-[#222] text-sm">{subjectName}</p>
                            </div>
                            <div className="overflow-x-auto [&::-webkit-scrollbar]:h-1 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-gray-300/60">
                              <table className="min-w-full text-sm border-collapse">
                                <thead>
                                  <tr className="bg-white border-b border-[#e8e8e8]">
                                    <th className="text-left px-3 py-2 text-[11px] font-bold tracking-widest uppercase text-[#999] w-[52px]">
                                      Dia
                                    </th>
                                    <th className="text-left px-3 py-2 text-[11px] font-bold tracking-widest uppercase text-[#999] w-[64px]">
                                      Hora
                                    </th>
                                    <th className="text-left px-4 py-2 text-[11px] font-bold tracking-widest uppercase text-[#999]">
                                      Turmas em paralelo
                                    </th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {hasWeeks
                                    ? sortedWeeks.flatMap((weekKey, weekIdx) => [
                                        <tr
                                          key={`whdr-${weekKey}`}
                                          className="bg-[#f5f4f1] border-t border-[#e8e8e8]"
                                        >
                                          <td colSpan={3} className="px-3 py-1.5">
                                            <span className="text-[10px] font-bold tracking-widest uppercase text-[#888]">
                                              Semana {weekIdx + 1}
                                              {weekKey ? ` · ${formatWeekDate(weekKey)}` : ""}
                                            </span>
                                          </td>
                                        </tr>,
                                        ...(weekMap.get(weekKey) ?? []).map((c, i) =>
                                          renderRow(c, i, hasWeeks),
                                        ),
                                      ])
                                    : candidates.map((c, i) => renderRow(c, i, hasWeeks))}
                                </tbody>
                              </table>
                            </div>
                          </div>
                        );
                      })}
                  </div>
                )}
              </div>
            </div>

            {/* Right column: Selecionadas */}
            <div className="w-80 shrink-0 flex flex-col min-h-0">
              <h2 className="font-bold text-[#333] text-base mb-3 shrink-0">Selecionadas</h2>
              <div className="flex-1 overflow-y-auto pb-6 [&::-webkit-scrollbar]:w-1 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-gray-300/60">
                {loadingCandidates ? (
                  <CandidatesLoadingSkeleton />
                ) : groupsBySubject.size === 0 ? (
                  <p className="text-xs text-[#aaa] text-center py-8">Nenhum grupo criado ainda.</p>
                ) : (
                  <div className="flex flex-col gap-5">
                    {[...groupsBySubject.entries()]
                      .sort(([a], [b]) => a.localeCompare(b))
                      .map(([subjName, items]) => (
                        <div
                          key={subjName}
                          className="overflow-hidden rounded-2xl border border-[#d4d4d4] shadow-sm"
                        >
                          <div className="px-3 py-2 bg-[#e8e8e8] border-b border-[#d4d4d4]">
                            <p className="text-[11px] font-bold tracking-widest uppercase text-[#444]">
                              {subjName}
                            </p>
                          </div>
                          <div className="flex flex-col gap-2 p-2">
                            {items.map(({ group, weekday, start_time, session_week, sessions }) => {
                              const day = DAY_CONFIG[weekday] ?? {
                                short: "?",
                                bg: "bg-gray-400",
                                text: "text-white",
                              };
                              return (
                                <div
                                  key={group.id}
                                  className="overflow-hidden rounded-xl border border-[#e8e8e8] shadow-sm bg-white"
                                >
                                  <div className="px-3 py-1.5 bg-[#1e2028] flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                      <span
                                        className={`text-[10px] font-bold tracking-wider px-1.5 py-0.5 rounded ${day.bg} ${day.text}`}
                                      >
                                        {day.short}
                                      </span>
                                      {session_week && (
                                        <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-gray-600 text-gray-300 tabular-nums whitespace-nowrap">
                                          {formatWeekDate(session_week)}
                                        </span>
                                      )}
                                      <span className="text-[11px] font-bold text-gray-300 tabular-nums">
                                        {formatTime(start_time)}
                                      </span>
                                    </div>
                                    <button
                                      onClick={() => handleRemoveGroup(group.id)}
                                      className="flex items-center justify-center w-5 h-5 rounded bg-red-600 hover:bg-red-500 transition-colors text-white text-xs font-bold leading-none cursor-pointer"
                                      title="Remover grupo"
                                    >
                                      ×
                                    </button>
                                  </div>
                                  <div className="px-3 py-2 flex flex-col gap-1 overflow-x-auto [&::-webkit-scrollbar]:h-1 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-gray-300/60">
                                    {sessions.map((meta, i) => {
                                      const typeLabel = meta.session_type ?? null;
                                      const typeStyle = typeLabel
                                        ? (SESSION_TYPE_CONFIG[typeLabel] ?? SESSION_TYPE_DEFAULT)
                                        : null;
                                      return (
                                        <div key={i} className="flex items-center gap-1 w-max">
                                          {typeLabel && typeStyle && (
                                            <span
                                              className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${typeStyle.bg} ${typeStyle.text}`}
                                            >
                                              {typeLabel}
                                            </span>
                                          )}
                                          {meta.class_codes.map((code: string) => (
                                            <span
                                              key={`${group.id}-${i}-${code}`}
                                              className="rounded px-1.5 py-0.5 text-[11px] font-semibold bg-[#ffc107] text-[#222]"
                                            >
                                              {code}
                                            </span>
                                          ))}
                                        </div>
                                      );
                                    })}
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {showResetModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white rounded-2xl shadow-2xl p-6 w-full max-w-sm mx-4">
            <h3 className="font-bold text-[#222] text-base mb-1">Tens a certeza?</h3>
            <p className="text-sm text-[#666] mb-6">
              Todas as seleções guardadas serão apagadas. Esta ação não pode ser desfeita.
            </p>
            <div className="flex flex-col gap-2">
              <button
                onClick={confirmReset}
                className="bg-red-600 text-white font-semibold px-4 py-2 rounded-lg text-sm hover:bg-red-500 transition-colors cursor-pointer"
              >
                Recomeçar
              </button>
              <button
                onClick={() => setShowResetModal(false)}
                className="text-[#666] font-semibold px-4 py-2 rounded-lg text-sm hover:bg-gray-100 transition-colors cursor-pointer"
              >
                Cancelar
              </button>
            </div>
          </div>
        </div>
      )}

      {showUnsavedModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white rounded-2xl shadow-2xl p-6 w-full max-w-sm mx-4">
            <h3 className="font-bold text-[#222] text-base mb-1">Tens mudanças por guardar</h3>
            <p className="text-sm text-[#666] mb-6">
              Se saíres sem guardar, as alterações feitas serão perdidas.
            </p>
            <div className="flex flex-col gap-2">
              <button
                onClick={() => void handleSaveAndExit()}
                disabled={saving}
                className="bg-[#ffc107] text-[#222] font-semibold px-4 py-2 rounded-lg text-sm hover:bg-[#e6ad06] transition-colors disabled:opacity-50 cursor-pointer"
              >
                {saving ? "A guardar..." : "Guardar e sair"}
              </button>
              <button
                onClick={handleExitWithoutSaving}
                disabled={saving}
                className="border border-red-400 text-red-500 font-semibold px-4 py-2 rounded-lg text-sm hover:bg-red-50 transition-colors disabled:opacity-50 cursor-pointer"
              >
                Sair sem guardar
              </button>
              <button
                onClick={() => setShowUnsavedModal(false)}
                disabled={saving}
                className="text-[#666] font-semibold px-4 py-2 rounded-lg text-sm hover:bg-gray-100 transition-colors disabled:opacity-50 cursor-pointer"
              >
                Cancelar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
