export interface Project {
  id: string;
  name: string;
  url: string;
  finished_ingestion_at: string | null;
  failed_ingestion_at: string | null;
}

export interface ProjectsResponse {
  data: {
    projects: Project[];
  };
}
