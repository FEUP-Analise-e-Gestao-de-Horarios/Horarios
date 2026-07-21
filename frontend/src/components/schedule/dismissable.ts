/**
 * Implicit DOM contract between writers (WeekGrid event cards, ScheduleNavbar)
 * and the readers that consult them (useDismissable's ignoreSelector option in
 * EditEventDrawer): elements marked with these attributes never count as
 * "clicked outside" — clicking a grid event retargets the drawer rather than
 * closing it, and clicks on the navbar keep the drawer open.
 */
export const SCHEDULE_EVENT_DATA_ATTR = "data-schedule-event";
export const SCHEDULE_NAVBAR_DATA_ATTR = "data-schedule-navbar";
export const SCHEDULE_PLACEMENT_DATA_ATTR = "data-schedule-placement";

export const DRAWER_DISMISS_IGNORE_SELECTOR = `[${SCHEDULE_EVENT_DATA_ATTR}],[${SCHEDULE_NAVBAR_DATA_ATTR}],[${SCHEDULE_PLACEMENT_DATA_ATTR}]`;
