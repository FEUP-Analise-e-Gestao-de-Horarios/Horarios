import type { DegreeOption, UUID, YearOption } from "@/types/parallelSessions";

/**
 * The degree → year → subject pill rows in the left column. Each row narrows the
 * candidate list; the year and subject rows only appear once a degree is chosen.
 * A pill is highlighted when active and tinted green once its scope is confirmed.
 */
export default function SubjectSelectors({
  degreesError,
  sortedDegrees,
  loadingDegrees,
  selectedDegree,
  confirmedDegreeIds,
  onDegreeClick,
  yearsWithCandidates,
  activeYearId,
  confirmedYearIds,
  onYearSelect,
  subjectNames,
  activeSubject,
  subjectIdByName,
  subjectAcronyms,
  confirmedSubjectIds,
  onSelectSubject,
}: {
  degreesError: string | null;
  sortedDegrees: DegreeOption[];
  loadingDegrees: boolean;
  selectedDegree: DegreeOption | null;
  confirmedDegreeIds: Set<UUID>;
  onDegreeClick: (degree: DegreeOption) => void;
  yearsWithCandidates: YearOption[];
  activeYearId: UUID | null;
  confirmedYearIds: Set<UUID>;
  onYearSelect: (yearId: UUID) => void;
  subjectNames: string[];
  activeSubject: string | null;
  subjectIdByName: Map<string, UUID>;
  subjectAcronyms: Map<string, string>;
  confirmedSubjectIds: Set<UUID>;
  onSelectSubject: (name: string) => void;
}) {
  return (
    <>
      {/* Degree selector */}
      {degreesError ? (
        <p className="mb-3 shrink-0 text-xs text-red-600">{degreesError}</p>
      ) : (
        sortedDegrees.length > 0 && (
          <div className="mb-3 shrink-0">
            <p className="mb-1.5 text-[10px] font-bold uppercase tracking-widest text-[#999]">
              Curso
            </p>
            <div className="flex flex-wrap gap-2 max-h-28 overflow-y-auto pr-1 [&::-webkit-scrollbar]:w-1 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-gray-300/60">
              {sortedDegrees.map((degree) => {
                const isActive = selectedDegree?.id === degree.id;
                const isConfirmed = confirmedDegreeIds.has(degree.id);
                return (
                  <button
                    key={degree.id}
                    type="button"
                    disabled={loadingDegrees}
                    onClick={() => onDegreeClick(degree)}
                    className={`rounded-full border px-3 py-1.5 text-[12px] font-semibold transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed ${
                      isActive
                        ? "border-[#b45309] bg-[#b45309] text-white"
                        : isConfirmed
                          ? "border-emerald-300 bg-emerald-50 text-emerald-800 hover:bg-emerald-100"
                          : "border-[#e8e8e8] bg-white text-[#555] hover:border-[#d4d4d4] hover:bg-[#faf7f4]"
                    }`}
                  >
                    {degree.acronym}
                  </button>
                );
              })}
            </div>
          </div>
        )
      )}

      {selectedDegree && (
        <>
          <div className="mb-3 shrink-0 border-t border-[#e8e8e8]" />

          {/* Year selector */}
          {yearsWithCandidates.length > 0 && (
            <div className="mb-3 shrink-0">
              <p className="mb-1.5 text-[10px] font-bold uppercase tracking-widest text-[#999]">
                Ano
              </p>
              <div className="flex flex-wrap gap-2">
                {yearsWithCandidates.map((year) => {
                  const isActive = activeYearId === year.id;
                  const isConfirmed = confirmedYearIds.has(year.id);
                  return (
                    <button
                      key={year.id}
                      type="button"
                      onClick={() => onYearSelect(year.id)}
                      className={`rounded-full border px-3 py-1.5 text-[12px] font-semibold transition-colors cursor-pointer ${
                        isActive
                          ? "border-[#1e2028] bg-[#1e2028] text-white"
                          : isConfirmed
                            ? "border-emerald-300 bg-emerald-50 text-emerald-800 hover:bg-emerald-100"
                            : "border-[#e8e8e8] bg-white text-[#555] hover:border-[#d4d4d4] hover:bg-[#faf7f4]"
                      }`}
                    >
                      {year.number}º Ano
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {subjectNames.length > 0 && (
            <>
              <div className="mb-3 shrink-0 border-t border-[#e8e8e8]" />
              <div className="mb-3 shrink-0">
                <p className="mb-1.5 text-[10px] font-bold uppercase tracking-widest text-[#999]">
                  Cadeira
                </p>
                <div className="flex flex-wrap gap-2">
                  {subjectNames.map((name) => {
                    const isActive = activeSubject === name;
                    const subjectId = subjectIdByName.get(name);
                    const isConfirmed = subjectId ? confirmedSubjectIds.has(subjectId) : false;
                    return (
                      <button
                        key={name}
                        type="button"
                        onClick={() => onSelectSubject(name)}
                        className={`rounded-full border px-3 py-1.5 text-[12px] font-semibold transition-colors cursor-pointer ${
                          isActive
                            ? "border-[#8c2d19] bg-[#8c2d19] text-white"
                            : isConfirmed
                              ? "border-emerald-300 bg-emerald-50 text-emerald-800 hover:bg-emerald-100"
                              : "border-[#e8e8e8] bg-white text-[#555] hover:border-[#d4d4d4] hover:bg-[#faf7f4]"
                        }`}
                      >
                        {subjectAcronyms.get(name) ?? name}
                      </button>
                    );
                  })}
                </div>
              </div>
            </>
          )}

          <div className="mb-3 shrink-0 border-t border-[#e8e8e8]" />
        </>
      )}
    </>
  );
}
