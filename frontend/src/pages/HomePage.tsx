import { useProjects } from "@/api/hooks/useProjects";
import { useState } from "react";
import Navbar from "@/components/layout/Navbar";
import NewProjectCard from "@/components/home/NewProjectCard";
import ProjectCard from "@/components/home/ProjectCard";
import NewProjectModal from "@/components/home/NewProjectModal";

export default function HomePage() {
  const [showNewProject, setShowNewProject] = useState(false);
  const { data: projects = [] } = useProjects();

  return (
    <div className="min-h-svh bg-[#f0eeeb] font-[system-ui,'Segoe_UI',Roboto,sans-serif]">
      <Navbar />

      <div className="flex flex-wrap p-6 pt-8 gap-4">
        <NewProjectCard onClick={() => setShowNewProject(true)} />

        {projects.map((project) => (
          <ProjectCard key={project.id} project={project} />
        ))}
      </div>

      {showNewProject && <NewProjectModal onClose={() => setShowNewProject(false)} />}
    </div>
  );
}
