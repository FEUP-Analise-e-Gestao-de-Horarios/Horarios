import { useState } from "react";
import { useNavigate } from "react-router-dom";

interface Project {
  id: number;
  nome: string;
  finished: boolean;
}

export default function DashboardPage() {
  const navigate = useNavigate();
  const [showNewProject, setShowNewProject] = useState(false);
  const [projectName, setProjectName] = useState("");
  const [scheduleLink, setScheduleLink] = useState("");

  const projects: Project[] = [];

  return (
    <div style={{ minHeight: "100vh", backgroundColor: "#f0eeeb", fontFamily: "var(--sans)" }}>
      {/* Navbar */}
      <header
        style={{
          padding: "12px 24px",
          backgroundColor: "#1e2028",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          width: "100%",
          boxSizing: "border-box",
        }}
      >
        <div style={{ display: "flex", gap: 8 }}>
          <button onClick={() => navigate(0)} style={btnYellow}>
            Início
          </button>
          <button style={btnOutlineRed}>Grupos</button>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button onClick={() => navigate("/react-change-password")} style={btnYellow}>
            Mudar palavra-passe
          </button>
          <button onClick={() => navigate("/react-login")} style={btnYellow}>
            Logout
          </button>
        </div>
      </header>

      {/* Content */}
      <div style={{ display: "flex", flexWrap: "wrap", padding: "32px 24px", gap: 16 }}>
        {/* New Project Card */}
        <div style={card} onClick={() => setShowNewProject(true)}>
          <span style={{ fontSize: 90, color: "var(--accent)", lineHeight: 1 }}>+</span>
          <span style={{ color: "var(--text-h)", fontWeight: 500, marginTop: 8 }}>
            Novo Projeto
          </span>
        </div>

        {/* Project Cards */}
        {projects.map((project) => (
          <div
            key={project.id}
            style={{ ...card, cursor: project.finished ? "pointer" : "default" }}
            onClick={() => project.finished && navigate(`/editturnos/${project.id}`)}
          >
            <div
              style={{
                width: "100%",
                flex: 1,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                backgroundColor: "#f9f7f4",
                borderRadius: "8px 8px 0 0",
                fontSize: 64,
              }}
            >
              🗄️
            </div>
            <div
              style={{
                width: "100%",
                padding: "10px 14px",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                boxSizing: "border-box",
              }}
            >
              <span
                style={{
                  color: "var(--text-h)",
                  fontWeight: 500,
                  maxWidth: 150,
                  wordWrap: "break-word",
                  fontSize: 14,
                }}
              >
                {project.nome}
              </span>
              <span
                style={{ fontSize: 20, cursor: "pointer", color: "var(--text)", letterSpacing: 2 }}
              >
                ···
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* New Project Popup */}
      {showNewProject && (
        <div
          onClick={() => setShowNewProject(false)}
          style={{
            position: "fixed",
            inset: 0,
            backgroundColor: "rgba(0,0,0,0.4)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 100,
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              backgroundColor: "var(--bg)",
              borderRadius: 8,
              padding: 32,
              width: 460,
              display: "flex",
              flexDirection: "column",
              gap: 16,
              boxShadow: "var(--shadow)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h2 style={{ margin: 0, color: "var(--text-h)", fontSize: 20 }}>Novo Projeto</h2>
              <span
                onClick={() => setShowNewProject(false)}
                style={{ cursor: "pointer", fontSize: 20, color: "var(--text)" }}
              >
                ✕
              </span>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <label style={{ color: "var(--text-h)", fontSize: 14 }}>Nome do Projeto:</label>
              <input
                type="text"
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
                style={{
                  padding: "10px 12px",
                  borderRadius: 4,
                  border: "1px solid var(--accent)",
                  fontSize: 15,
                  outline: "none",
                  backgroundColor: "white",
                  color: "#08060d",
                }}
              />
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <label style={{ color: "var(--text-h)", fontSize: 14 }}>Link do Horário:</label>
              <input
                type="text"
                value={scheduleLink}
                onChange={(e) => setScheduleLink(e.target.value)}
                style={{
                  padding: "10px 12px",
                  borderRadius: 4,
                  border: "1px solid var(--accent)",
                  fontSize: 15,
                  outline: "none",
                  backgroundColor: "white",
                  color: "#08060d",
                }}
              />
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
              <button
                onClick={() => setShowNewProject(false)}
                style={{
                  padding: "8px 20px",
                  borderRadius: 4,
                  border: "none",
                  backgroundColor: "#6b7280",
                  color: "white",
                  cursor: "pointer",
                  fontSize: 14,
                }}
              >
                Cancelar
              </button>
              <button
                onClick={() => {
                  // TODO: ligar à API
                  setShowNewProject(false);
                  setProjectName("");
                  setScheduleLink("");
                }}
                style={{
                  padding: "8px 20px",
                  borderRadius: 4,
                  border: "none",
                  backgroundColor: "var(--accent)",
                  color: "white",
                  cursor: "pointer",
                  fontSize: 14,
                  fontWeight: 600,
                }}
              >
                Criar Projeto
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const btnYellow: React.CSSProperties = {
  backgroundColor: "var(--accent)",
  color: "white",
  fontWeight: 600,
  padding: "8px 14px",
  borderRadius: 4,
  border: "none",
  cursor: "pointer",
  fontSize: 14,
};

const btnOutlineRed: React.CSSProperties = {
  backgroundColor: "transparent",
  color: "white",
  fontWeight: 600,
  padding: "8px 14px",
  borderRadius: 4,
  border: "1px solid var(--accent)",
  cursor: "pointer",
  fontSize: 14,
};

const card: React.CSSProperties = {
  width: 220,
  height: 220,
  backgroundColor: "white",
  border: "1px solid var(--border)",
  borderRadius: 8,
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  justifyContent: "center",
  cursor: "pointer",
  boxShadow: "0 2px 8px rgba(0,0,0,0.08)",
  overflow: "hidden",
};
