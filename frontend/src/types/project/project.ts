// -- Base ----------------------------------------------------------------
export interface Project {
  id: number;
  name: string;
  url: string;
  has_selected_parallel_sessions: boolean;
  created_at: string;
  updated_at: string;
  ingestion_started_at: string | null;
  ingestion_finished_at: string | null;
  ingestion_failed_at: string | null;
}

// -- List payload --------------------------------------------------------
export interface ProjectsListPayload {
  projects: Project[];
}

// -- Stats ---------------------------------------------------------------
export interface ProjectStats {
  degrees: number;
  years: number;
  subjects: number;
  classes: number;
  teachers: number;
  rooms: number;
  sessions: number;
}
