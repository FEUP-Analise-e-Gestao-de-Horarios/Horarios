import { api } from "@/api/client";
import { useEffect, useState } from "react";
import type { Project, ProjectsResponse } from "@/types/project";
import Navbar from "@/components/layout/Navbar";
import NewProjectCard from "@/components/home/NewProjectCard";
import ProjectCard from "@/components/home/ProjectCard";
import NewProjectModal from "@/components/home/NewProjectModal";
import RenameProjectModal from "@/components/home/RenameProjectModal";
import DeleteProjectModal from "@/components/home/DeleteProjectModal";

export default function HomePage() {
  const [showNewProject, setShowNewProject] = useState(false);
  const [projects, setProjects] = useState<Project[]>([]);
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);
  const [renameProject, setRenameProject] = useState<Project | null>(null);
  const [deleteProject, setDeleteProject] = useState<Project | null>(null);

  useEffect(() => {
    api
      .get<ProjectsResponse>("/api/projects/")
      .then((res) => setProjects(res.data.projects))
      .catch(() => {});
  }, []);

  return (
    <div
      className="min-h-svh bg-[#f0eeeb] font-[system-ui,'Segoe_UI',Roboto,sans-serif]"
      onClick={() => setOpenMenuId(null)}
    >
      <Navbar />

      <div className="flex flex-wrap p-6 pt-8 gap-4">
        <NewProjectCard onClick={() => setShowNewProject(true)} />

        {projects.map((project) => (
          <ProjectCard
            key={project.id}
            project={project}
            isMenuOpen={openMenuId === project.id}
            onToggleMenu={() => setOpenMenuId(openMenuId === project.id ? null : project.id)}
            onRename={() => {
              setRenameProject(project);
              setOpenMenuId(null);
            }}
            onDelete={() => {
              setDeleteProject(project);
              setOpenMenuId(null);
            }}
          />
        ))}
      </div>

      {showNewProject && (
        <NewProjectModal onClose={() => setShowNewProject(false)} onProjectsUpdated={setProjects} />
      )}

      {renameProject && (
        <RenameProjectModal
          project={renameProject}
          onClose={() => setRenameProject(null)}
          onProjectsUpdated={setProjects}
        />
      )}

      {deleteProject && (
        <DeleteProjectModal
          project={deleteProject}
          onClose={() => setDeleteProject(null)}
          onProjectsUpdated={setProjects}
        />
      )}
    </div>
  );
}
