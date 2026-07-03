import type { RefObject } from "react";
import type { GroupView } from "@/api/hooks/useParallelSessions";
import CandidatesLoadingSkeleton from "./CandidatesLoadingSkeleton";
import GroupCard from "./GroupCard";

/**
 * The "Selecionadas" panel (bottom of the right column): one column per subject
 * with formed groups, the active subject's column widened and scrolled into
 * view. The scroll container and active-column refs are owned by the page so it
 * can drive the scroll-into-view and reveal-pulse behaviour.
 */
export default function SelectedGroupsPanel({
  loadingCandidates,
  groupViewsBySubject,
  activeSubject,
  highlightedGroupId,
  onRemoveGroup,
  scrollRef,
  activeColRef,
  registerGroupRef,
}: {
  loadingCandidates: boolean;
  groupViewsBySubject: Map<string, GroupView[]>;
  activeSubject: string | null;
  highlightedGroupId: string | null;
  onRemoveGroup: (groupId: string) => void;
  scrollRef: RefObject<HTMLDivElement | null>;
  activeColRef: RefObject<HTMLDivElement | null>;
  registerGroupRef: (groupId: string, el: HTMLDivElement | null) => void;
}) {
  return (
    <div className="flex-[42] min-h-0 flex flex-col">
      <h2 className="font-bold text-[#333] text-base mb-3 shrink-0">Selecionadas</h2>
      <div className="flex-1 min-h-0">
        {loadingCandidates ? (
          <CandidatesLoadingSkeleton />
        ) : groupViewsBySubject.size === 0 ? (
          <p className="text-xs text-[#aaa] text-center py-8">Nenhum grupo criado ainda.</p>
        ) : (
          <div
            ref={scrollRef}
            className="flex h-full gap-4 overflow-auto pr-1 pb-2 [&::-webkit-scrollbar]:h-1 [&::-webkit-scrollbar]:w-1 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-gray-300/60"
          >
            {[...groupViewsBySubject.entries()]
              .sort(([a], [b]) => a.localeCompare(b))
              .map(([subjName, items]) => {
                const isActive = subjName === activeSubject;
                return (
                  <div
                    key={subjName}
                    ref={isActive ? activeColRef : undefined}
                    className={`parallel-col-enter flex flex-col transition-[flex-grow,min-width] duration-300 ease-out ${
                      isActive ? "flex-[2.75] min-w-[340px]" : "flex-1 min-w-[210px]"
                    }`}
                  >
                    {/* Pinned so the subject stays visible while its cards scroll under it. */}
                    <div className="sticky top-0 z-10 flex items-center gap-2 bg-[#f0eeeb] pb-1.5">
                      <p className="text-[11px] font-bold tracking-widest uppercase text-[#888]">
                        {subjName}
                      </p>
                      <span className="text-[10px] font-semibold text-[#bbb] tabular-nums">
                        {items.length}
                      </span>
                      <div className="flex-1 h-px bg-[#e0e0e0]" />
                    </div>
                    <div className="flex flex-col">
                      {items.map((view) => (
                        <GroupCard
                          key={view.group.id}
                          view={view}
                          highlighted={highlightedGroupId === view.group.id}
                          onRemove={() => onRemoveGroup(view.group.id)}
                          registerRef={(el) => registerGroupRef(view.group.id, el)}
                        />
                      ))}
                    </div>
                  </div>
                );
              })}
          </div>
        )}
      </div>
    </div>
  );
}
