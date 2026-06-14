import { useEffect, useRef, useState } from "react";
import type { ConflictRecord } from "@/types/project/conflicts";
import { CONFLICT_TAGS } from "@/types/project/conflicts";
import { useUpdateConflictTag } from "@/api/hooks/project/year";
import { WEEKDAY_LABELS_SHORT } from "@/utils/weekdays";
import { hhmmToMinutes, minutesToTime } from "@/utils/time";
import ScrollingNames from "./ScrollingNames";

// ------------------------------------------------------------------
// Helpers
// ------------------------------------------------------------------

const TAG_ORDER: string[] = [CONFLICT_TAGS.PRE_EXISTING, CONFLICT_TAGS.IGNORED];

const TAG_SECTION_LABELS: Record<string, string> = {
  [CONFLICT_TAGS.PRE_EXISTING]: "Pré-existentes",
  [CONFLICT_TAGS.IGNORED]: "Ignorados",
};

const TAG_BADGE_LABELS: Record<string, string> = {
  [CONFLICT_TAGS.IGNORED]: "Ignorado",
};

function tagSectionLabel(tag: string): string {
  return TAG_SECTION_LABELS[tag] ?? tag.charAt(0).toUpperCase() + tag.slice(1);
}

function tagBadgeLabel(tag: string): string {
  return TAG_BADGE_LABELS[tag] ?? tag.charAt(0).toUpperCase() + tag.slice(1);
}

function sortedTags(tags: string[]): string[] {
  return [...tags].sort((a, b) => {
    const ia = TAG_ORDER.indexOf(a);
    const ib = TAG_ORDER.indexOf(b);
    if (ia !== -1 && ib !== -1) return ia - ib;
    if (ia !== -1) return -1;
    if (ib !== -1) return 1;
    return a.localeCompare(b);
  });
}

// ------------------------------------------------------------------
// Sub-components
// ------------------------------------------------------------------

interface SectionHeaderProps {
  label: string;
  count: number;
  collapsed: boolean;
  onToggle: () => void;
}

function SectionHeader({ label, count, collapsed, onToggle }: SectionHeaderProps) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className="w-full flex items-center gap-2 pt-1 pb-2 bg-[#1d2128] group cursor-pointer"
    >
      <span className="text-[11px] font-semibold uppercase tracking-widest text-white/50 group-hover:text-white/70 transition-colors shrink-0">
        {label}
      </span>
      <span className="flex-1 h-px bg-white/10 group-hover:bg-white/20 transition-colors" />
      <span className="text-[11px] text-white/35 tabular-nums shrink-0">{count}</span>
      <svg
        className={[
          "w-3 h-3 text-white/35 group-hover:text-white/60 shrink-0",
          collapsed ? "" : "rotate-180",
        ].join(" ")}
        viewBox="0 0 12 12"
        fill="none"
      >
        <path
          d="M2 4l4 4 4-4"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </button>
  );
}

// ------------------------------------------------------------------
// TagPicker
// ------------------------------------------------------------------

interface TagPickerProps {
  anchorRect: DOMRect;
  currentTag: string;
  availableTags: string[];
  onSelect: (tag: string) => void;
  onClose: () => void;
  onAddCustomTag: (tag: string) => void;
}

function TagPicker({
  anchorRect,
  currentTag,
  availableTags,
  onSelect,
  onClose,
  onAddCustomTag,
}: TagPickerProps) {
  const [input, setInput] = useState("");
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handlePointerDown(e: PointerEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose();
    }
    document.addEventListener("pointerdown", handlePointerDown);
    return () => document.removeEventListener("pointerdown", handlePointerDown);
  }, [onClose]);

  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [onClose]);

  function handleAdd() {
    const tag = input.trim();
    if (!tag) return;
    onAddCustomTag(tag);
    onSelect(tag);
    onClose();
  }

  const tagsToShow = availableTags.filter((t) => t !== CONFLICT_TAGS.PRE_EXISTING);

  return (
    <div
      ref={ref}
      style={{
        position: "fixed",
        top: anchorRect.bottom + 4,
        right: window.innerWidth - anchorRect.right,
      }}
      className="z-[200] bg-[#282d37] border border-white/20 rounded-md shadow-xl w-48 overflow-hidden"
    >
      {tagsToShow.length > 0 && (
        <div className="py-1">
          {tagsToShow.map((tag) => (
            <button
              key={tag}
              type="button"
              onClick={() => {
                onSelect(tag === currentTag ? CONFLICT_TAGS.PRE_EXISTING : tag);
                onClose();
              }}
              className="w-full text-left text-xs px-3 py-1.5 hover:bg-white/10 transition-colors flex items-center gap-2"
            >
              <span
                className={[
                  "flex-1 truncate",
                  tag === currentTag ? "text-white" : "text-white/60",
                ].join(" ")}
              >
                {tagBadgeLabel(tag)}
              </span>
              {tag === currentTag && (
                <svg className="w-3 h-3 shrink-0 text-white/50" viewBox="0 0 12 12" fill="none">
                  <path
                    d="M2 6l3 3 5-5"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              )}
            </button>
          ))}
        </div>
      )}
      <div
        className={[
          "px-2 pb-2",
          tagsToShow.length > 0 ? "border-t border-white/10 pt-1.5" : "pt-2",
        ].join(" ")}
      >
        <div className="flex gap-1">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleAdd();
              e.stopPropagation();
            }}
            placeholder="Nova etiqueta…"
            className="flex-1 text-[11px] bg-white/10 rounded px-2 py-1 text-white placeholder:text-white/30 outline-none border border-transparent focus:border-white/20 min-w-0"
            ref={(el) => el?.focus()}
          />
          <button
            type="button"
            onClick={handleAdd}
            disabled={!input.trim()}
            className="text-sm px-2 py-1 rounded bg-white/10 hover:bg-white/20 text-white/60 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors leading-none"
          >
            +
          </button>
        </div>
      </div>
    </div>
  );
}

// ------------------------------------------------------------------
// ConflictCard
// ------------------------------------------------------------------

interface ConflictCardProps {
  conflict: ConflictRecord;
  availableTags: string[];
  onTagToggle: (conflictId: string, nextTag: string | null) => void;
  onAddCustomTag: (tag: string) => void;
  isPending: boolean;
}

function ConflictCard({
  conflict,
  availableTags,
  onTagToggle,
  onAddCustomTag,
  isPending,
}: ConflictCardProps) {
  const [pickerAnchorRect, setPickerAnchorRect] = useState<DOMRect | null>(null);
  const plusButtonRef = useRef<HTMLButtonElement>(null);

  const isIgnored = conflict.tag === CONFLICT_TAGS.IGNORED;
  const hasCustomTag = !!conflict.tag && !TAG_ORDER.includes(conflict.tag);

  function handlePlusClick() {
    if (pickerAnchorRect) {
      setPickerAnchorRect(null);
    } else {
      const rect = plusButtonRef.current?.getBoundingClientRect();
      if (rect) setPickerAnchorRect(rect);
    }
  }

  return (
    <div
      className={[
        "border-l-4 rounded p-3 space-y-2 transition-opacity",
        isIgnored ? "border-white/15 bg-white/[0.03] opacity-60" : "border-white/30 bg-white/5",
      ].join(" ")}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <ScrollingNames names={conflict.event_names} />
          <p className="text-xs text-white/70 mt-1">
            {(WEEKDAY_LABELS_SHORT as Record<string, string>)[conflict.day] ?? conflict.day} às{" "}
            {minutesToTime(hhmmToMinutes(conflict.time))} — Turma: {conflict.turma.join(", ")}
          </p>
        </div>

        <div className="shrink-0 flex items-center gap-1.5">
          {hasCustomTag && (
            <span className="flex items-center gap-1 text-[11px] text-white/50 bg-white/10 border border-white/15 rounded px-1.5 py-0.5 max-w-[8rem]">
              <span className="truncate">{tagBadgeLabel(conflict.tag!)}</span>
              <button
                type="button"
                onClick={() => onTagToggle(conflict.id, null)}
                disabled={isPending}
                className="shrink-0 text-white/40 hover:text-white/80 transition-colors disabled:opacity-40"
                aria-label="Remover etiqueta"
              >
                <svg className="w-2.5 h-2.5" viewBox="0 0 10 10" fill="none">
                  <path
                    d="M2 2l6 6M8 2l-6 6"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                  />
                </svg>
              </button>
            </span>
          )}

          {isIgnored && (
            <button
              type="button"
              onClick={() => onTagToggle(conflict.id, null)}
              disabled={isPending}
              className="text-white/50 hover:text-white/90 border border-white/15 hover:border-white/30 rounded px-1.5 py-0.5 leading-none transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              aria-label="Restaurar"
            >
              <svg className="w-3 h-3" viewBox="0 0 10 10" fill="none">
                <path
                  d="M2 2l6 6M8 2l-6 6"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                />
              </svg>
            </button>
          )}

          {hasCustomTag && (
            <>
              <button
                ref={plusButtonRef}
                type="button"
                onClick={handlePlusClick}
                disabled={isPending}
                className="text-white/50 hover:text-white/90 border border-white/15 hover:border-white/30 rounded px-1.5 py-0.5 text-sm font-light leading-none transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                aria-label="Adicionar etiqueta"
              >
                +
              </button>
              {pickerAnchorRect && (
                <TagPicker
                  anchorRect={pickerAnchorRect}
                  currentTag={conflict.tag!}
                  availableTags={availableTags}
                  onSelect={(tag) => onTagToggle(conflict.id, tag)}
                  onClose={() => setPickerAnchorRect(null)}
                  onAddCustomTag={onAddCustomTag}
                />
              )}
            </>
          )}
        </div>
      </div>

      <div className="space-y-1 pt-2 border-t border-white/10">
        {conflict.conflict_reasons.map((reason, idx) => (
          <p key={idx} className="text-xs text-white/80 flex items-start gap-2">
            <span className="text-white/60 mt-0.5">•</span>
            <span>{reason}</span>
          </p>
        ))}
      </div>
    </div>
  );
}

// ------------------------------------------------------------------
// Drawer
// ------------------------------------------------------------------

interface ConflictsDrawerProps {
  open: boolean;
  onClose: () => void;
  projectId: string;
  conflicts?: ConflictRecord[];
  isLoading?: boolean;
  onRefresh?: () => void;
}

export default function ConflictsDrawer({
  open,
  onClose,
  projectId,
  conflicts = [],
  isLoading = false,
  onRefresh,
}: ConflictsDrawerProps) {
  const asideRef = useRef<HTMLElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);
  const { mutate: updateTag, isPending: isTagPending } = useUpdateConflictTag(projectId);
  const [collapsedTags, setCollapsedTags] = useState<Set<string>>(new Set(TAG_ORDER));
  const [customTags, setCustomTags] = useState<string[]>([]);

  const knownTagsFromConflicts = [
    ...new Set(
      conflicts
        .map((c) => c.tag)
        .filter((t): t is string => !!t && t !== CONFLICT_TAGS.PRE_EXISTING),
    ),
  ];
  const allAvailableTags = [
    ...new Set([CONFLICT_TAGS.IGNORED, ...knownTagsFromConflicts, ...customTags]),
  ];

  function addCustomTag(tag: string) {
    setCustomTags((prev) => (prev.includes(tag) ? prev : [...prev, tag]));
  }

  function toggleSection(tag: string) {
    setCollapsedTags((prev) => {
      if (!prev.has(tag)) {
        return new Set([...prev, tag]);
      }
      return new Set(headerTags.filter((t) => t !== tag));
    });
  }

  useEffect(() => {
    if (!open) return;
    previousFocusRef.current = document.activeElement as HTMLElement | null;
    asideRef.current?.focus();

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      previousFocusRef.current?.focus();
    };
  }, [open, onClose]);

  const untaggedConflicts = conflicts.filter((c) => !c.tag);
  const byTag = new Map<string, ConflictRecord[]>();
  for (const conflict of conflicts) {
    if (!conflict.tag) continue;
    const existing = byTag.get(conflict.tag) ?? [];
    byTag.set(conflict.tag, [...existing, conflict]);
  }
  const orderedTags = sortedTags([...byTag.keys()]);
  const headerTags = sortedTags([...new Set([...byTag.keys(), CONFLICT_TAGS.IGNORED])]);
  const hasNewConflicts =
    untaggedConflicts.length > 0 || orderedTags.some((t) => !TAG_ORDER.includes(t));
  const showUntagged =
    untaggedConflicts.length > 0 && orderedTags.every((t) => collapsedTags.has(t));

  return (
    <div
      inert={!open}
      className={[
        "fixed inset-0 z-50 transition-opacity",
        open ? "pointer-events-auto opacity-100" : "pointer-events-none opacity-0",
      ].join(" ")}
    >
      <div aria-hidden="true" onClick={onClose} className="absolute inset-0 bg-black/45" />

      <aside
        ref={asideRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="conflicts-drawer-title"
        tabIndex={-1}
        className={[
          "absolute right-0 top-0 h-full w-[min(92vw,500px)] bg-[#1d2128] text-white border-l border-white/15 shadow-[-8px_0_24px_rgba(0,0,0,0.45)] transition-transform flex flex-col overflow-hidden focus:outline-none",
          open ? "translate-x-0" : "translate-x-full",
        ].join(" ")}
      >
        {/* Header */}
        <div className="shrink-0 bg-[#1d2128] border-b border-white/10 px-5 py-4 flex items-center justify-between z-20">
          <h2 id="conflicts-drawer-title" className="text-lg font-semibold">
            Conflitos
            {conflicts.length > 0 && (
              <span className="ml-2 text-sm font-normal text-white/50">{conflicts.length}</span>
            )}
          </h2>
          <div className="flex items-center gap-2">
            {onRefresh ? (
              <button
                type="button"
                onClick={onRefresh}
                disabled={isLoading}
                className="text-white/80 hover:text-white border border-white/20 rounded px-2 py-1 text-sm flex items-center gap-2"
              >
                {isLoading ? (
                  <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
                    <circle
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                      strokeOpacity="0.2"
                    />
                    <path
                      d="M22 12a10 10 0 00-10-10"
                      stroke="currentColor"
                      strokeWidth="4"
                      strokeLinecap="round"
                    />
                  </svg>
                ) : null}
                <span>{isLoading ? "A atualizar" : "Atualizar"}</span>
              </button>
            ) : null}

            <button
              type="button"
              onClick={onClose}
              className="text-white/80 hover:text-white border border-white/20 rounded px-2 py-1 text-sm"
            >
              Fechar
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-hidden flex flex-col px-5 py-4">
          {isLoading ? (
            <p className="mt-auto text-white/60 text-center py-8">A carregar conflitos…</p>
          ) : conflicts.length === 0 ? (
            <p className="mt-auto text-white/60 text-center py-8">Sem conflitos</p>
          ) : (
            <div className="flex-1 min-h-0 flex flex-col">
              {/* Scrollable conflict cards */}
              <div className="flex-1 min-h-0 overflow-y-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
                {!hasNewConflicts && orderedTags.every((t) => collapsedTags.has(t)) ? (
                  <div className="h-full flex items-center justify-center">
                    <p className="text-white/60 text-sm">Sem novos conflitos</p>
                  </div>
                ) : (
                  <div className="flex flex-col gap-4 pb-2">
                    {showUntagged && (
                      <div className="space-y-3">
                        {[...untaggedConflicts].reverse().map((conflict) => (
                          <ConflictCard
                            key={conflict.id}
                            conflict={conflict}
                            availableTags={allAvailableTags}
                            isPending={isTagPending}
                            onTagToggle={(id, next) => updateTag({ conflictId: id, tag: next })}
                            onAddCustomTag={addCustomTag}
                          />
                        ))}
                      </div>
                    )}
                    {orderedTags.map((tag) => {
                      const group = byTag.get(tag) ?? [];
                      if (collapsedTags.has(tag)) return null;
                      return (
                        <div key={tag} className="space-y-3">
                          {[...group].reverse().map((conflict) => (
                            <ConflictCard
                              key={conflict.id}
                              conflict={conflict}
                              availableTags={allAvailableTags}
                              isPending={isTagPending}
                              onTagToggle={(id, next) => updateTag({ conflictId: id, tag: next })}
                              onAddCustomTag={addCustomTag}
                            />
                          ))}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Static section headers pinned at the bottom */}
              <div className="shrink-0 flex flex-col pt-1">
                {headerTags.map((tag) => (
                  <SectionHeader
                    key={tag}
                    label={tagSectionLabel(tag)}
                    count={(byTag.get(tag) ?? []).length}
                    collapsed={collapsedTags.has(tag)}
                    onToggle={() => toggleSection(tag)}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      </aside>
    </div>
  );
}
