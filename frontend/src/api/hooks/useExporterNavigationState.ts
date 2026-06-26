import { useEffect, useRef, useState } from "react";

function readSessionBoolean(key: string, fallback: boolean): boolean {
  if (typeof window === "undefined") return fallback;
  const savedValue = window.sessionStorage.getItem(key);
  if (savedValue === null) return fallback;
  return savedValue === "true";
}

export default function useExporterNavigationState(projectId: string) {
  const conflictsOpenStorageKey = `exporter-conflicts-open:${projectId}`;
  const selectedConflictStorageKey = `exporter-selected-conflict:${projectId}`;
  const [highlightedAnchor, setHighlightedAnchor] = useState<string | null>(null);
  const [highlightedConflictAnchor, setHighlightedConflictAnchor] = useState<string | null>(null);
  const [isConflictsOpen, setIsConflictsOpen] = useState(() =>
    readSessionBoolean(
      conflictsOpenStorageKey,
      typeof window !== "undefined" &&
        window.sessionStorage.getItem(selectedConflictStorageKey) !== null,
    ),
  );
  const highlightTimeoutRef = useRef<number | null>(null);
  const conflictHighlightTimeoutRef = useRef<number | null>(null);
  const restoredConflictAnchorRef = useRef<string | null>(null);

  function handleDependencyClick(anchor: string) {
    setHighlightedAnchor(anchor);
    document.getElementById(anchor)?.scrollIntoView({
      behavior: "smooth",
      block: "center",
    });

    if (highlightTimeoutRef.current !== null) {
      window.clearTimeout(highlightTimeoutRef.current);
    }

    highlightTimeoutRef.current = window.setTimeout(() => {
      setHighlightedAnchor(null);
      highlightTimeoutRef.current = null;
    }, 2400);
  }

  function handleConflictsOpenChange(open: boolean) {
    setIsConflictsOpen(open);
    window.sessionStorage.setItem(conflictsOpenStorageKey, String(open));
  }

  function handleConflictReferenceClick(anchor: string) {
    setIsConflictsOpen(true);
    window.sessionStorage.setItem(conflictsOpenStorageKey, "true");
    setHighlightedConflictAnchor(anchor);

    window.requestAnimationFrame(() => {
      window.requestAnimationFrame(() => {
        document.getElementById(anchor)?.scrollIntoView({
          behavior: "smooth",
          block: "center",
        });
      });
    });

    if (conflictHighlightTimeoutRef.current !== null) {
      window.clearTimeout(conflictHighlightTimeoutRef.current);
    }

    conflictHighlightTimeoutRef.current = window.setTimeout(() => {
      setHighlightedConflictAnchor(null);
      conflictHighlightTimeoutRef.current = null;
    }, 2400);
  }

  function handleConflictCardClick(anchor: string) {
    window.sessionStorage.setItem(conflictsOpenStorageKey, "true");
    window.sessionStorage.setItem(selectedConflictStorageKey, anchor);
  }

  useEffect(() => {
    const selectedConflictAnchor = window.sessionStorage.getItem(selectedConflictStorageKey);
    if (!selectedConflictAnchor || restoredConflictAnchorRef.current === selectedConflictAnchor) {
      return;
    }
    if (!isConflictsOpen) return;

    window.requestAnimationFrame(() => {
      const selectedCard = document.getElementById(selectedConflictAnchor);
      selectedCard?.scrollIntoView({ block: "center" });
      restoredConflictAnchorRef.current = selectedConflictAnchor;
      window.sessionStorage.removeItem(selectedConflictStorageKey);
    });
  }, [conflictsOpenStorageKey, isConflictsOpen, selectedConflictStorageKey]);

  return {
    highlightedAnchor,
    highlightedConflictAnchor,
    isConflictsOpen,
    handleDependencyClick,
    handleConflictsOpenChange,
    handleConflictReferenceClick,
    handleConflictCardClick,
  };
}
