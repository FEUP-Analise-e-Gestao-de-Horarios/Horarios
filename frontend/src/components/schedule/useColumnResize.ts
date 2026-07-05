import {
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type KeyboardEvent as ReactKeyboardEvent,
  type MouseEvent as ReactMouseEvent,
} from "react";

export const TURMA_COLUMN_MIN_PX = 32;
export const TURMA_COLUMN_MAX_PX = 320;

export type ColumnDragState = {
  colIndex: number;
  width: number;
  othersWidth: number;
};

function clampColumnWidth(width: number): number {
  return Math.min(TURMA_COLUMN_MAX_PX, Math.max(TURMA_COLUMN_MIN_PX, width));
}

/**
 * Encapsulates the turma-column resize interaction for the week grid:
 *
 * - pointer drag (`handleResizeStart` + a document-level move/up listener),
 * - keyboard resize (`handleResizeKeyDown`, arrow keys, Shift = bigger step),
 * - the committed uniform `columnWidthPx`, and
 * - a scroll-position correction so the resized column keeps its on-screen
 *   spot once every column adopts the new width.
 *
 * Attach the returned `gridRef` to the CSS-grid element.
 */
export function useColumnResize() {
  const gridRef = useRef<HTMLDivElement>(null);

  // Uniform width applied to every turma column once a resize finishes
  // (null = use the default flexible layout).
  const [columnWidthPx, setColumnWidthPx] = useState<number | null>(null);
  // While a resize is in progress, only the dragged column changes width;
  // every other column stays frozen at `othersWidth`.
  const [dragState, setDragState] = useState<ColumnDragState | null>(null);
  const dragInfoRef = useRef<{
    colIndex: number;
    startX: number;
    startWidth: number;
    width: number;
  } | null>(null);
  // The resized column's header cell and its viewport-relative left, captured
  // just before a width change commits. Empty columns and days stay compacted,
  // so the post-commit shift is NOT a uniform `colIndex * delta`; we measure the
  // real shift after layout and cancel it via scrollLeft instead of predicting
  // it.
  const resizedCellRef = useRef<HTMLElement | null>(null);
  const anchorLeftRef = useRef<number | null>(null);

  const anchorResizedColumn = (cell: HTMLElement) => {
    resizedCellRef.current = cell;
    // Viewport-relative left of the resized column. The scroll container's own
    // box doesn't move during a resize (only the content width changes), so the
    // cell's viewport shift equals the amount we must undo via scrollLeft.
    anchorLeftRef.current = cell.getBoundingClientRect().left;
  };

  const handleResizeStart = (columnIndex: number, event: ReactMouseEvent<HTMLElement>) => {
    event.preventDefault();
    event.stopPropagation();
    const cell = event.currentTarget.parentElement;
    if (!cell) return;
    const startWidth = Math.round(cell.getBoundingClientRect().width);
    resizedCellRef.current = cell;
    dragInfoRef.current = {
      colIndex: columnIndex,
      startX: event.clientX,
      startWidth,
      width: startWidth,
    };
    setDragState({ colIndex: columnIndex, width: startWidth, othersWidth: startWidth });
  };

  const handleResizeKeyDown = (event: ReactKeyboardEvent<HTMLElement>) => {
    const direction = event.key === "ArrowLeft" ? -1 : event.key === "ArrowRight" ? 1 : 0;
    if (direction === 0) return;
    event.preventDefault();
    const cell = event.currentTarget.parentElement;
    if (!cell) return;
    const step = event.shiftKey ? 32 : 8;
    const currentWidth = Math.round(cell.getBoundingClientRect().width);
    const nextWidth = clampColumnWidth(currentWidth + direction * step);
    anchorResizedColumn(cell);
    setColumnWidthPx(nextWidth);
  };

  const isResizing = dragState !== null;
  useEffect(() => {
    if (!isResizing) return;

    const handleMove = (event: MouseEvent) => {
      const info = dragInfoRef.current;
      if (!info) return;
      const nextWidth = clampColumnWidth(
        Math.round(info.startWidth + (event.clientX - info.startX)),
      );
      info.width = nextWidth;
      setDragState({ colIndex: info.colIndex, width: nextWidth, othersWidth: info.startWidth });
    };

    const handleUp = () => {
      const info = dragInfoRef.current;
      const cell = resizedCellRef.current;
      if (info) {
        // Capture the dragged column's on-screen spot before the compacted
        // layout commits, so the layout effect can scroll it back into place.
        if (cell) anchorResizedColumn(cell);
        setColumnWidthPx(info.width);
      }
      dragInfoRef.current = null;
      setDragState(null);
    };

    const previousCursor = document.body.style.cursor;
    const previousUserSelect = document.body.style.userSelect;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
    document.addEventListener("mousemove", handleMove);
    document.addEventListener("mouseup", handleUp);
    return () => {
      document.body.style.cursor = previousCursor;
      document.body.style.userSelect = previousUserSelect;
      document.removeEventListener("mousemove", handleMove);
      document.removeEventListener("mouseup", handleUp);
    };
  }, [isResizing]);

  // Once the new layout commits, measure how far the resized column actually
  // moved and cancel it via scrollLeft so it stays put on screen. Measuring
  // (rather than computing `colIndex * delta`) keeps it correct when empty
  // columns or days between the edge and the resized column stay compacted.
  useLayoutEffect(() => {
    const anchorLeft = anchorLeftRef.current;
    const cell = resizedCellRef.current;
    if (anchorLeft === null || !cell) return;
    anchorLeftRef.current = null;
    const scrollContainer = gridRef.current?.parentElement;
    if (scrollContainer)
      scrollContainer.scrollLeft += cell.getBoundingClientRect().left - anchorLeft;
  }, [columnWidthPx, dragState]);

  return { gridRef, columnWidthPx, dragState, handleResizeStart, handleResizeKeyDown };
}
