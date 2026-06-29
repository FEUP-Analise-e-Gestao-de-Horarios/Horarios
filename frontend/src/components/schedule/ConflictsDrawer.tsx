import { useEffect, useMemo, useRef, useState } from "react";
import type { ConflictRecord } from "@/types/project/conflicts";
import { CONFLICT_TAGS } from "@/types/project/conflicts";
import {
  useDeleteConflictTag,
  useProjectConflictTags,
  useUpdateConflictTags,
} from "@/api/hooks/project/year";
import { WEEKDAY_LABELS_SHORT } from "@/utils/weekdays";
import { hhmmToMinutes, minutesToTime } from "@/utils/time";
import DrawerMultiSelect, { type DrawerSelectOption } from "./DrawerMultiSelect";
import ScrollingNames from "./ScrollingNames";

// ------------------------------------------------------------------
// Helpers
// ------------------------------------------------------------------

// TODO: Degrees the current user is allowed to manage. Hardcoded for now; the
// "Meus cursos" tab is scoped to conflicts touching any of these degrees.
const PERMITTED_DEGREES: string[] = [
  "LEIC",
  "CINF",
  "MEIC",
  "MIA",
  "MESW",
  "MECD",
  "MCI",
  "MM",
  "PRODEI",
];

type ConflictTab = "current" | "permitted" | "all";

// Sentinel option id for the tag dropdown that matches conflicts with no tag.
const UNTAGGED = "__untagged__";

const TAG_ORDER: string[] = [CONFLICT_TAGS.PRE_EXISTING, CONFLICT_TAGS.IGNORED];

const TAG_BADGE_LABELS: Record<string, string> = {
  [CONFLICT_TAGS.PRE_EXISTING]: "Pré-existente",
  [CONFLICT_TAGS.IGNORED]: "Ignorado",
};

function tagBadgeLabel(tag: string): string {
  return TAG_BADGE_LABELS[tag] ?? tag.charAt(0).toUpperCase() + tag.slice(1);
}

// Shared chip styling so tag badges, the "Ignorar" button and the "+" button
// all share the same height and padding.
const CHIP_BASE =
  "inline-flex items-center h-6 px-1.5 rounded border text-[11px] leading-none transition-colors";
const CHIP_ACTION =
  `${CHIP_BASE} text-white/50 hover:text-white/90 border-white/15 hover:border-white/30 ` +
  "cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed";

// ------------------------------------------------------------------
// TagPicker
// ------------------------------------------------------------------

interface TagPickerProps {
  anchorRect: DOMRect;
  selectedTags: string[];
  availableTags: string[];
  onToggle: (tag: string) => void;
  onClose: () => void;
  onAddCustomTag: (tag: string) => void;
}

function TagPicker({
  anchorRect,
  selectedTags,
  availableTags,
  onToggle,
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
    if (!selectedTags.includes(tag)) onToggle(tag);
    setInput("");
  }

  const tagsToShow = availableTags.filter(
    (t) => t !== CONFLICT_TAGS.PRE_EXISTING && t !== CONFLICT_TAGS.IGNORED,
  );

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
          {tagsToShow.map((tag) => {
            const isSelected = selectedTags.includes(tag);
            return (
              <button
                key={tag}
                type="button"
                onClick={() => onToggle(tag)}
                className="w-full text-left text-xs px-3 py-1.5 hover:bg-white/10 transition-colors flex items-center gap-2 cursor-pointer"
              >
                <span
                  className={["flex-1 truncate", isSelected ? "text-white" : "text-white/60"].join(
                    " ",
                  )}
                >
                  {tagBadgeLabel(tag)}
                </span>
                {isSelected && (
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
            );
          })}
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
            className="text-sm px-2 py-1 rounded bg-white/10 hover:bg-white/20 text-white/60 hover:text-white cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed transition-colors leading-none"
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
  onSetTags: (conflictId: string, nextTags: string[]) => void;
  onAddCustomTag: (tag: string) => void;
  isPending: boolean;
}

function ConflictCard({
  conflict,
  availableTags,
  onSetTags,
  onAddCustomTag,
  isPending,
}: ConflictCardProps) {
  const [pickerAnchorRect, setPickerAnchorRect] = useState<DOMRect | null>(null);
  const plusButtonRef = useRef<HTMLButtonElement>(null);

  const isIgnored = conflict.tags.includes(CONFLICT_TAGS.IGNORED);
  const isPreExisting = conflict.tags.includes(CONFLICT_TAGS.PRE_EXISTING);
  // Custom (user-defined) tags, excluding the system-managed pre-existing/ignored ones.
  const customTags = conflict.tags.filter((t) => !TAG_ORDER.includes(t));

  function toggleTag(tag: string) {
    const next = conflict.tags.includes(tag)
      ? conflict.tags.filter((t) => t !== tag)
      : [...conflict.tags, tag];
    onSetTags(conflict.id, next);
  }

  function removeTag(tag: string) {
    onSetTags(
      conflict.id,
      conflict.tags.filter((t) => t !== tag),
    );
  }

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

        <div className="shrink-0 flex items-center flex-wrap justify-end gap-1.5">
          {isPreExisting && (
            <span className={`${CHIP_BASE} text-white/40 bg-white/[0.06] border-white/10`}>
              {tagBadgeLabel(CONFLICT_TAGS.PRE_EXISTING)}
            </span>
          )}

          {customTags.map((tag) => (
            <span
              key={tag}
              className={`${CHIP_BASE} gap-1 max-w-[8rem] text-white/50 bg-white/10 border-white/15`}
            >
              <span className="truncate">{tagBadgeLabel(tag)}</span>
              <button
                type="button"
                onClick={() => removeTag(tag)}
                disabled={isPending}
                className="shrink-0 text-white/40 hover:text-white/80 transition-colors cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
                aria-label={`Remover etiqueta ${tagBadgeLabel(tag)}`}
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
          ))}

          {isIgnored ? (
            <button
              type="button"
              onClick={() => removeTag(CONFLICT_TAGS.IGNORED)}
              disabled={isPending}
              className={`${CHIP_ACTION} gap-1`}
              aria-label="Restaurar conflito"
            >
              {tagBadgeLabel(CONFLICT_TAGS.IGNORED)}
              <svg className="w-2.5 h-2.5" viewBox="0 0 10 10" fill="none">
                <path
                  d="M2 2l6 6M8 2l-6 6"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                />
              </svg>
            </button>
          ) : (
            <button
              type="button"
              onClick={() => toggleTag(CONFLICT_TAGS.IGNORED)}
              disabled={isPending}
              className={CHIP_ACTION}
              aria-label="Ignorar conflito"
            >
              Ignorar
            </button>
          )}

          <button
            ref={plusButtonRef}
            type="button"
            onClick={handlePlusClick}
            disabled={isPending}
            className={`${CHIP_ACTION} justify-center font-light`}
            aria-label="Adicionar etiqueta"
          >
            +
          </button>
          {pickerAnchorRect && (
            <TagPicker
              anchorRect={pickerAnchorRect}
              selectedTags={conflict.tags}
              availableTags={availableTags}
              onToggle={toggleTag}
              onClose={() => setPickerAnchorRect(null)}
              onAddCustomTag={onAddCustomTag}
            />
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
  displayedBlockIds?: Set<string>;
}

const TAB_LABELS: Record<ConflictTab, string> = {
  current: "Horário atual",
  permitted: "Meus cursos",
  all: "Todos",
};

export default function ConflictsDrawer({
  open,
  onClose,
  projectId,
  conflicts = [],
  isLoading = false,
  onRefresh,
  displayedBlockIds,
}: ConflictsDrawerProps) {
  const asideRef = useRef<HTMLElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  const { mutate: updateTags, isPending: isTagPending } = useUpdateConflictTags(projectId);
  const { mutate: deleteTag } = useDeleteConflictTag(projectId);
  const { data: dbTags = [] } = useProjectConflictTags(projectId, open);
  const [activeTab, setActiveTab] = useState<ConflictTab>("current");
  // Which filter dropdown (if any) is currently expanded.
  const [openDropdown, setOpenDropdown] = useState<"filter" | "tag" | null>(null);
  const [filterSearch, setFilterSearch] = useState("");
  const [tagSearch, setTagSearch] = useState("");
  // Active selections in each filter dropdown. Empty means "show all". The
  // subject/degree dropdown holds subject acronyms on the "current" tab and
  // degree acronyms elsewhere; the tag dropdown holds tag names (or UNTAGGED).
  const [selectedFilters, setSelectedFilters] = useState<string[]>([]);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [customTags, setCustomTags] = useState<string[]>([]);

  // Conflicts scoped to each tab (before the secondary subject/degree filter).
  const tabConflicts = useMemo<Record<ConflictTab, ConflictRecord[]>>(() => {
    const permitted = new Set(PERMITTED_DEGREES);
    return {
      current: displayedBlockIds
        ? conflicts.filter((c) => c.block_ids.some((id) => displayedBlockIds.has(id)))
        : [],
      permitted: conflicts.filter((c) => c.degrees.some((d) => permitted.has(d))),
      all: conflicts,
    };
  }, [conflicts, displayedBlockIds]);

  const baseConflicts = tabConflicts[activeTab];
  const filterKind: "subject" | "degree" = activeTab === "current" ? "subject" : "degree";

  // Subject/degree dropdown options for the active tab, each with a count.
  const filterOptions = useMemo<DrawerSelectOption[]>(() => {
    const counts = new Map<string, number>();
    for (const conflict of baseConflicts) {
      const values = filterKind === "subject" ? conflict.subjects : conflict.degrees;
      for (const value of values) {
        if (
          filterKind === "degree" &&
          activeTab === "permitted" &&
          !PERMITTED_DEGREES.includes(value)
        ) {
          continue;
        }
        counts.set(value, (counts.get(value) ?? 0) + 1);
      }
    }
    const keys = [...counts.keys()];
    if (filterKind === "degree" && activeTab === "permitted") {
      keys.sort((a, b) => PERMITTED_DEGREES.indexOf(a) - PERMITTED_DEGREES.indexOf(b));
    } else {
      keys.sort((a, b) => a.localeCompare(b));
    }
    return keys.map((value) => ({ id: value, label: `${value} (${counts.get(value) ?? 0})` }));
  }, [baseConflicts, filterKind, activeTab]);

  // Tag dropdown options: every known tag (even with no match in this tab),
  // plus an "untagged" bucket, each with a count scoped to the active tab.
  const tagOptions = useMemo<DrawerSelectOption[]>(() => {
    const counts = new Map<string, number>();
    let untagged = 0;
    for (const conflict of baseConflicts) {
      if (conflict.tags.length === 0) untagged += 1;
      else for (const tag of conflict.tags) counts.set(tag, (counts.get(tag) ?? 0) + 1);
    }
    for (const tag of dbTags) if (!counts.has(tag)) counts.set(tag, 0);

    const makeOption = (tag: string, deletable = false) => ({
      id: tag,
      label: `${tagBadgeLabel(tag)} (${counts.get(tag) ?? 0})`,
      deletable,
    });

    // Custom tags first, alphabetically; the three system buckets stay last in
    // a fixed sequence: pré-existentes, sem etiqueta, then ignorados. Only
    // custom tags are user-deletable — the system buckets are not.
    const customTags = [...counts.keys()]
      .filter((tag) => !TAG_ORDER.includes(tag))
      .sort((a, b) => a.localeCompare(b));

    const options = customTags.map((tag) => makeOption(tag, true));
    if (counts.has(CONFLICT_TAGS.PRE_EXISTING))
      options.push(makeOption(CONFLICT_TAGS.PRE_EXISTING));
    options.push({ id: UNTAGGED, label: `Sem etiqueta (${untagged})`, deletable: false });
    if (counts.has(CONFLICT_TAGS.IGNORED)) options.push(makeOption(CONFLICT_TAGS.IGNORED));
    return options;
  }, [baseConflicts, dbTags]);

  const displayedConflicts = useMemo(() => {
    let result = baseConflicts;
    if (selectedFilters.length > 0) {
      result = result.filter((conflict) =>
        (filterKind === "subject" ? conflict.subjects : conflict.degrees).some((value) =>
          selectedFilters.includes(value),
        ),
      );
    }
    if (selectedTags.length > 0) {
      result = result.filter((conflict) =>
        conflict.tags.length > 0
          ? conflict.tags.some((tag) => selectedTags.includes(tag))
          : selectedTags.includes(UNTAGGED),
      );
    } else {
      // Ignored conflicts stay hidden until "Ignorados" is explicitly selected.
      result = result.filter((conflict) => !conflict.tags.includes(CONFLICT_TAGS.IGNORED));
    }
    return result;
  }, [baseConflicts, selectedFilters, selectedTags, filterKind]);

  const hasActiveFilter = selectedFilters.length > 0 || selectedTags.length > 0;

  // Pre-existing conflicts that aren't already ignored — the targets of the
  // "ignore all pre-existing" bulk action.
  const preExistingToIgnore = useMemo(
    () =>
      conflicts.filter(
        (c) =>
          c.tags.includes(CONFLICT_TAGS.PRE_EXISTING) && !c.tags.includes(CONFLICT_TAGS.IGNORED),
      ),
    [conflicts],
  );

  function ignoreAllPreExisting() {
    for (const conflict of preExistingToIgnore) {
      updateTags({ conflictId: conflict.id, tags: [...conflict.tags, CONFLICT_TAGS.IGNORED] });
    }
  }

  const pickerTags = dbTags.filter((t) => t !== CONFLICT_TAGS.PRE_EXISTING);
  const allAvailableTags = [...new Set([...pickerTags, ...customTags])];

  function addCustomTag(tag: string) {
    setCustomTags((prev) => (prev.includes(tag) ? prev : [...prev, tag]));
  }

  // Delete a tag from the database and strip it off every conflict that has it.
  function handleDeleteTag(tag: string) {
    const confirmed = window.confirm(
      `Eliminar a etiqueta "${tagBadgeLabel(tag)}" de todos os conflitos? Esta ação não pode ser desfeita.`,
    );
    if (!confirmed) return;
    deleteTag(tag);
    setSelectedTags((prev) => prev.filter((t) => t !== tag));
    setCustomTags((prev) => prev.filter((t) => t !== tag));
  }

  function toggleSelection(setter: typeof setSelectedFilters, id: string) {
    setter((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }

  function selectTab(tab: ConflictTab) {
    setActiveTab(tab);
    // The subject/degree selection is tab-specific, so clear it on switch.
    setSelectedFilters([]);
    setFilterSearch("");
    setOpenDropdown(null);
  }

  const normalizedFilterSearch = filterSearch.toLowerCase().trim();
  const filterDropdownOptions = filterOptions.filter((option) =>
    option.label.toLowerCase().includes(normalizedFilterSearch),
  );
  const normalizedTagSearch = tagSearch.toLowerCase().trim();
  const tagDropdownOptions = tagOptions.filter((option) =>
    option.label.toLowerCase().includes(normalizedTagSearch),
  );

  const filterTriggerLabel =
    selectedFilters.length === 0
      ? filterKind === "subject"
        ? "Todas as disciplinas"
        : "Todos os cursos"
      : selectedFilters.length === 1
        ? (selectedFilters[0] ?? "")
        : `${selectedFilters.length} selecionados`;

  const tagTriggerLabel =
    selectedTags.length === 0
      ? "Todas as etiquetas"
      : selectedTags.length === 1
        ? selectedTags[0] === UNTAGGED
          ? "Sem etiqueta"
          : tagBadgeLabel(selectedTags[0] ?? "")
        : `${selectedTags.length} selecionadas`;

  useEffect(() => {
    if (!open) return;
    previousFocusRef.current = document.activeElement as HTMLElement | null;
    asideRef.current?.focus();

    function handleKeyDown(event: KeyboardEvent) {
      // Let an open filter dropdown swallow Escape instead of closing the drawer.
      if (event.key === "Escape" && !openDropdown) onClose();
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      previousFocusRef.current?.focus();
    };
  }, [open, onClose, openDropdown]);

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
                className="text-white/80 hover:text-white border border-white/20 rounded px-2 py-1 text-sm flex items-center gap-2 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
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
              className="text-white/80 hover:text-white border border-white/20 rounded px-2 py-1 text-sm cursor-pointer"
            >
              Fechar
            </button>
          </div>
        </div>

        {/* Tabs + secondary filter */}
        {!isLoading && (
          <div className="shrink-0 border-b border-white/10 px-5 pt-3">
            <div className="flex gap-1 bg-white/5 rounded-lg p-1">
              {(["current", "permitted", "all"] as ConflictTab[]).map((tab) => (
                <button
                  key={tab}
                  type="button"
                  onClick={() => selectTab(tab)}
                  className={[
                    "flex-1 text-[11px] px-2 py-1.5 rounded-md transition-colors flex items-center justify-center gap-1.5 cursor-pointer",
                    activeTab === tab
                      ? "bg-white/15 text-white"
                      : "text-white/50 hover:text-white/80",
                  ].join(" ")}
                >
                  <span className="truncate">{TAB_LABELS[tab]}</span>
                  <span className="text-white/35">
                    {
                      tabConflicts[tab].filter((c) => !c.tags.includes(CONFLICT_TAGS.IGNORED))
                        .length
                    }
                  </span>
                </button>
              ))}
            </div>

            {conflicts.length > 0 && (
              <div className="grid grid-cols-2 gap-2 py-2.5">
                <DrawerMultiSelect
                  label={filterKind === "subject" ? "Disciplina" : "Curso"}
                  triggerLabel={filterTriggerLabel}
                  open={openDropdown === "filter"}
                  onToggle={() => setOpenDropdown((prev) => (prev === "filter" ? null : "filter"))}
                  search={filterSearch}
                  onSearchChange={setFilterSearch}
                  listMaxHeightClass="max-h-52"
                  groups={[{ options: filterDropdownOptions }]}
                  selectedIds={selectedFilters}
                  onToggleOption={(id) => toggleSelection(setSelectedFilters, id)}
                />
                <DrawerMultiSelect
                  label="Etiqueta"
                  triggerLabel={tagTriggerLabel}
                  open={openDropdown === "tag"}
                  onToggle={() => setOpenDropdown((prev) => (prev === "tag" ? null : "tag"))}
                  search={tagSearch}
                  onSearchChange={setTagSearch}
                  listMaxHeightClass="max-h-52"
                  groups={[{ options: tagDropdownOptions }]}
                  selectedIds={selectedTags}
                  onToggleOption={(id) => toggleSelection(setSelectedTags, id)}
                  onDeleteOption={handleDeleteTag}
                />
              </div>
            )}

            {preExistingToIgnore.length > 0 && (
              <div className="flex justify-end pb-2.5">
                <button
                  type="button"
                  onClick={ignoreAllPreExisting}
                  disabled={isTagPending}
                  className="text-[11px] px-2.5 py-1.5 rounded border border-white/15 text-white/60 hover:text-white hover:border-white/30 transition-colors cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  Ignorar pré-existentes ({preExistingToIgnore.length})
                </button>
              </div>
            )}
          </div>
        )}

        {/* Body */}
        <div className="flex-1 overflow-hidden flex flex-col px-5 py-4">
          {isLoading ? (
            <p className="mt-auto text-white/60 text-center py-8">A carregar conflitos…</p>
          ) : displayedConflicts.length === 0 ? (
            <p className="mt-auto text-white/60 text-center py-8">
              {hasActiveFilter
                ? "Sem conflitos para este filtro"
                : activeTab === "current"
                  ? "Sem conflitos no horário apresentado"
                  : activeTab === "permitted"
                    ? "Sem conflitos nos teus cursos"
                    : "Sem conflitos"}
            </p>
          ) : (
            <div className="flex-1 min-h-0 overflow-y-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
              <div className="flex flex-col gap-3 pb-2">
                {displayedConflicts.map((conflict) => (
                  <ConflictCard
                    key={conflict.id}
                    conflict={conflict}
                    availableTags={allAvailableTags}
                    isPending={isTagPending}
                    onSetTags={(id, tags) => updateTags({ conflictId: id, tags })}
                    onAddCustomTag={addCustomTag}
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
