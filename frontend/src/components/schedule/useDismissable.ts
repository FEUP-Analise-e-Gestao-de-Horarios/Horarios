import { useEffect, useRef, type RefObject } from "react";

interface UseDismissableOptions {
  /** Also dismiss when the Escape key is pressed. Defaults to false. */
  escape?: boolean;
  /** A pointer-down whose target matches this selector never dismisses. */
  ignoreSelector?: string;
}

/**
 * Calls `onDismiss` when the user presses the pointer down outside `ref`
 * (and, optionally, when Escape is pressed). No-op while `ref` is unmounted,
 * so it is safe to attach to an element that only exists while open.
 *
 * `onDismiss` is read through a ref, so callers may pass an inline callback
 * without re-subscribing the document listeners every render.
 */
export function useDismissable<T extends HTMLElement>(
  ref: RefObject<T | null>,
  onDismiss: () => void,
  options: UseDismissableOptions = {},
): void {
  const { escape = false, ignoreSelector } = options;
  const onDismissRef = useRef(onDismiss);
  useEffect(() => {
    onDismissRef.current = onDismiss;
  });

  useEffect(() => {
    function handlePointerDown(event: MouseEvent) {
      const element = ref.current;
      if (!element) return;
      const { target } = event;
      if (!(target instanceof Node) || element.contains(target)) return;
      if (ignoreSelector && target instanceof Element && target.closest(ignoreSelector)) return;
      onDismissRef.current();
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onDismissRef.current();
    }

    document.addEventListener("mousedown", handlePointerDown);
    if (escape) document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      if (escape) document.removeEventListener("keydown", handleKeyDown);
    };
  }, [ref, escape, ignoreSelector]);
}
