import type { Weekday } from "./weekday";

export interface RedBlockBase {
  id: string;
  hour: number;
  weekday: Weekday;
}
