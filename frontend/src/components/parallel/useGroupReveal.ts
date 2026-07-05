import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { GroupView } from "@/api/hooks/parallel/sessions";

/**
 * Owns the "reveal a group card" choreography for the selected-groups panel: the
 * scroll container + active-column refs, per-card ref registration, the one-shot
 * "look here" highlight pulse, and scrolling a card (or the active subject's
 * column) into view. The page wires the returned handlers to node taps, group
 * creation, and subject changes.
 */
export function useGroupReveal(
  activeSubject: string | null,
  groupViewsBySubject: Map<string, GroupView[]>,
) {
  // The selected-groups scroll container (scrolls both axes: columns sideways,
  // cards vertically under their pinned headers) and the active subject's column
  // within it, so selecting a subject scrolls it into view.
  const groupsScrollRef = useRef<HTMLDivElement | null>(null);
  const activeGroupColRef = useRef<HTMLDivElement | null>(null);

  // The group card currently playing its "look here" pulse, plus per-card refs
  // so we can scroll the matching card into view.
  const [highlightedGroupId, setHighlightedGroupId] = useState<string | null>(null);
  const groupCardRefs = useRef(new Map<string, HTMLDivElement>());
  const highlightTimer = useRef<number | null>(null);
  useEffect(() => () => window.clearTimeout(highlightTimer.current ?? undefined), []);

  // On subject change, jump the panel back to the top and bring the active
  // subject's column into horizontal view.
  useEffect(() => {
    const container = groupsScrollRef.current;
    if (!container) return;
    const col = activeGroupColRef.current;
    if (!col) {
      container.scrollTo({ top: 0, behavior: "smooth" });
      return;
    }
    const cRect = container.getBoundingClientRect();
    const colRect = col.getBoundingClientRect();
    const delta = colRect.left - cRect.left;
    const target = container.scrollLeft + delta - (container.clientWidth - colRect.width) / 2;
    container.scrollTo({ top: 0, left: Math.max(0, target), behavior: "smooth" });
  }, [activeSubject]);

  // Block id -> the id of the (shown) group it belongs to, for reveal-on-tap.
  const groupIdByBlock = useMemo(() => {
    const map = new Map<string, string>();
    for (const items of groupViewsBySubject.values())
      for (const view of items) for (const b of view.blocks) map.set(b.blockId, view.group.id);
    return map;
  }, [groupViewsBySubject]);

  // Register/unregister a group card's element so it can be scrolled into view.
  const registerGroupRef = useCallback((groupId: string, el: HTMLDivElement | null) => {
    if (el) groupCardRefs.current.set(groupId, el);
    else groupCardRefs.current.delete(groupId);
  }, []);

  // Scroll a group card into view and play its one-shot "look here" pulse.
  // Deferred a frame so a just-opened candidate's card is registered and laid
  // out before we scroll to it — callers can invoke this synchronously.
  const revealGroup = useCallback((groupId: string) => {
    requestAnimationFrame(() => {
      const el = groupCardRefs.current.get(groupId);
      if (!el) return;
      el.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
      window.clearTimeout(highlightTimer.current ?? undefined);
      // Clear any current highlight, then start the pulse only after the smooth
      // scroll has had time to land — otherwise it can finish before the card is
      // on screen. Clearing first also restarts the CSS animation on a repeat.
      setHighlightedGroupId(null);
      highlightTimer.current = window.setTimeout(() => {
        setHighlightedGroupId(groupId);
        highlightTimer.current = window.setTimeout(() => setHighlightedGroupId(null), 800);
      }, 380);
    });
  }, []);

  // Scroll a group card into view without the pulse — used on create, where the
  // card's own enter/shift animation is the feedback (and a pulse would fight
  // its rightward shift transform). Deferred a frame so the freshly-created card
  // has mounted before we scroll to it.
  const scrollGroupIntoView = useCallback((groupId: string) => {
    requestAnimationFrame(() =>
      groupCardRefs.current
        .get(groupId)
        ?.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" }),
    );
  }, []);

  // Tap on an already-grouped node reveals the group it belongs to.
  const handleRevealGroup = useCallback(
    (blockId: string) => {
      const groupId = groupIdByBlock.get(blockId);
      if (groupId) revealGroup(groupId);
    },
    [groupIdByBlock, revealGroup],
  );

  return {
    groupsScrollRef,
    activeGroupColRef,
    highlightedGroupId,
    registerGroupRef,
    revealGroup,
    scrollGroupIntoView,
    handleRevealGroup,
  };
}
