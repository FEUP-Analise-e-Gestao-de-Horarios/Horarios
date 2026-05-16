import { useState } from "react";
import type { WeekGridEvent } from "./WeekGrid";

/**
 * State for the edit-event drawer: which event is currently being edited,
 * whether the drawer is open, and whether it's collapsed against the left
 * edge. `openEditor` clones the event so the drawer can edit a local copy
 * without mutating the WeekGrid's source data.
 */
export function useEventEditor() {
  const [editingEvent, setEditingEvent] = useState<WeekGridEvent | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);

  const openEditor = (event: WeekGridEvent | null) => {
    setEditingEvent(event ? { ...event } : null);
    setIsCollapsed(false);
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
