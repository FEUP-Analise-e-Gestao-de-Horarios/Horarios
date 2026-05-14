import {
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type KeyboardEvent as ReactKeyboardEvent,
  type MouseEvent as ReactMouseEvent,
} from "react";

const TURMA_COLUMN_MIN_PX = 32;
const TURMA_COLUMN_MAX_PX = 320;

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
  // Pending horizontal scroll correction so a resized column keeps its
  // on-screen position once every column adopts the new width.
  const scrollAdjustRef = useRef(0);

  const handleResizeStart = (columnIndex: number, event: ReactMouseEvent<HTMLButtonElement>) => {
    event.preventDefault();
    event.stopPropagation();
    const cell = event.currentTarget.parentElement;
    if (!cell) return;
    const startWidth = Math.round(cell.getBoundingClientRect().width);
    dragInfoRef.current = {
      colIndex: columnIndex,
      startX: event.clientX,
      startWidth,
      width: startWidth,
    };
    setDragState({ colIndex: columnIndex, width: startWidth, othersWidth: startWidth });
  };

  const handleResizeKeyDown = (
    columnIndex: number,
    event: ReactKeyboardEvent<HTMLButtonElement>,
  ) => {
    const direction = event.key === "ArrowLeft" ? -1 : event.key === "ArrowRight" ? 1 : 0;
    if (direction === 0) return;
    event.preventDefault();
    const cell = event.currentTarget.parentElement;
    if (!cell) return;
    const step = event.shiftKey ? 32 : 8;
    const currentWidth = Math.round(cell.getBoundingClientRect().width);
    const nextWidth = clampColumnWidth(currentWidth + direction * step);
    scrollAdjustRef.current = columnIndex * (nextWidth - currentWidth);
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
      if (info) {
        // Once every column adopts the new width, the dragged column's left
        // edge shifts by colIndex * (newWidth - oldWidth); cancel it out via
        // scrollLeft.
        scrollAdjustRef.current = info.colIndex * (info.width - info.startWidth);
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

  // After a resize commits the new column width, shift the scroll position so
  // the resized column stays exactly where it was on screen.
  useLayoutEffect(() => {
    const adjustment = scrollAdjustRef.current;
    if (adjustment === 0) return;
    scrollAdjustRef.current = 0;
    const scrollContainer = gridRef.current?.parentElement;
    if (scrollContainer) scrollContainer.scrollLeft += adjustment;
  }, [columnWidthPx]);

  return { gridRef, columnWidthPx, dragState, handleResizeStart, handleResizeKeyDown };
}
