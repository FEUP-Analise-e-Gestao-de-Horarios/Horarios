export interface Project {
  id: string;
  name: string;
  url: string;
  ingestion_started_at: string | null;
  ingestion_finished_at: string | null;
  ingestion_failed_at: string | null;
}

export interface ProjectsResponse {
  data: {
    projects: Project[];
  };
}
