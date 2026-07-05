import { useRef, useState } from "react";

/** In-flight save controls shared across group CRUD, confirmations, and finish. */
export interface SavingControls {
  /** True while any create/delete/confirm request is in flight. */
  saving: boolean;
  beginRequest: () => void;
  endRequest: () => void;
}

/** Drives the `saving` flag off a counter of outstanding save requests, so
 * concurrent writes only clear it once every one of them settles. */
export function useSaving(): SavingControls {
  const [saving, setSaving] = useState(false);
  // Count of outstanding save requests, to drive the `saving` flag.
  const inFlight = useRef(0);

  const beginRequest = () => {
    inFlight.current += 1;
    setSaving(true);
  };
  const endRequest = () => {
    inFlight.current = Math.max(0, inFlight.current - 1);
    if (inFlight.current === 0) setSaving(false);
  };

  return { saving, beginRequest, endRequest };
}
