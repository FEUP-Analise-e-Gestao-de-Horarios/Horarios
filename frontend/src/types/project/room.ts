import type { RedBlockBase } from "./red_block";
import type { WeekBlockResponse } from "./sessions";

// -- Base ----------------------------------------------------------------
export interface RoomBase {
  id: string;
  name: string;
  type: string | null;
  size: string | null;
  seats: string | null;
}

// -- Stats ---------------------------------------------------------------
export interface RoomStats extends RoomBase {
  sessions: number;
  red_blocks: number;
}

// -- List payload --------------------------------------------------------
export interface RoomsListPayload {
  rooms: RoomStats[];
  count: number;
}

// -- Detail --------------------------------------------------------------
export interface RoomDetail extends RoomBase {
  blocks: WeekBlockResponse[];
  red_blocks: RedBlockBase[];
}
