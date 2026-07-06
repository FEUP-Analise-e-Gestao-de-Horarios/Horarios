import { useState } from "react";
import type { WeekGridEvent } from "./WeekGrid";

/**
 * State for the edit-event drawer: which event is currently being edited,
 * whether the drawer is open, and whether it's collapsed against the left
 * edge. `openEditor` deep-clones the event so the drawer's in-flight edits
 * can't reach back into the canonical event arrays (`body`, `classCodes`,
 * `teachers`, …) that the grid keeps rendering from.
 */
export function useEventEditor() {
  const [editingEvent, setEditingEvent] = useState<WeekGridEvent | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);

  const openEditor = (event: WeekGridEvent | null, collapsed = false) => {
    setEditingEvent(event ? structuredClone(event) : null);
    setIsCollapsed(collapsed);
    setIsOpen(true);
  };

  const closeEditor = () => {
    setIsOpen(false);
    setEditingEvent(null);
  };

  return {
    editingEvent,
    isOpen,
    isCollapsed,
    setIsCollapsed,
    openEditor,
    closeEditor,
  };
}
