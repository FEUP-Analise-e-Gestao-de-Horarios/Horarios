/** A selectable option in a schedule filter dropdown. */
export type DropdownOption = {
  value: string;
  label: string;
  secondaryText?: string;
};

/** A degree (curso) option in the curso dropdown. */
export type CourseOption = {
  value: string;
  label: string;
  description?: string;
};

/** A labelled group of degree options (e.g. "Licenciaturas"). */
export type CourseGroup = {
  label: string;
  options: CourseOption[];
};
