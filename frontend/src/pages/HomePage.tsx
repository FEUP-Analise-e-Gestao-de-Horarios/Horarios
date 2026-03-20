import { api } from "@/api/client";
import { useEffect, useState } from "react";
import type { Project, ProjectsResponse } from "@/types/project";
import Navbar from "@/components/layout/Navbar";
import NewProjectCard from "@/components/home/NewProjectCard";
import ProjectCard from "@/components/home/ProjectCard";
import NewProjectModal from "@/components/home/NewProjectModal";

export default function HomePage() {
  const [showNewProject, setShowNewProject] = useState(false);
  const [projects, setProjects] = useState<Project[]>([]);

  useEffect(() => {
    api
      .get<ProjectsResponse>("/api/projects/")
      .then((res) => setProjects(res.data.projects))
      .catch(() => {});
  }, []);

  return (
    <div className="min-h-svh bg-[#f0eeeb] font-[system-ui,'Segoe_UI',Roboto,sans-serif]">
      <Navbar />

      <div className="flex flex-wrap p-6 pt-8 gap-4">
        <NewProjectCard onClick={() => setShowNewProject(true)} />

        {projects.map((project) => (
          <ProjectCard key={project.id} project={project} onProjectsUpdated={setProjects} />
        ))}
      </div>

      {showNewProject && (
        <NewProjectModal onClose={() => setShowNewProject(false)} onProjectsUpdated={setProjects} />
      )}
    </div>
  );
}
