import { useNavigate } from "react-router-dom";

export default function Login() {
  const navigate = useNavigate();

  return (
    <div style={{
      minHeight: "100vh",
      backgroundColor: "var(--bg)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      fontFamily: "var(--sans)",
    }}>
      <div style={{ display: "flex", flexDirection: "column", gap: 10, width: 300 }}>
        <h1 style={{ color: "var(--text-h)", margin: 20, textAlign: "center" }}>
          Sign In
        </h1>

        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <input
            type="text"
            placeholder="Username"
            style={{
              padding: "10px 12px",
              borderRadius: 4,
              border: "1px solid var(--border)",
              backgroundColor: "var(--bg)",
              color: "var(--text-h)",
              outline: "none",
              fontSize: 15,
            }}
          />
          <span style={{ color: "var(--text)", fontSize: 13, display: "flex" }}>Nome de utilizador</span>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <input
            type="password"
            placeholder="••••••••"
            style={{
              padding: "10px 12px",
              borderRadius: 4,
              border: "1px solid var(--border)",
              backgroundColor: "var(--bg)",
              color: "var(--text-h)",
              outline: "none",
              fontSize: 15,
            }}
          />
          <span style={{ color: "var(--text)", fontSize: 13, display: "flex" }}>Palavra-passe</span>
        </div>

        <a href="#" 
          onClick={(e) => {e.preventDefault(); navigate("/react-forgot-password");}}
          style={{ color: "var(--accent)", fontSize: 13 }}>
          Esqueci-me da palavra-passe
        </a>

        <button style={{
          backgroundColor: "var(--accent)",
          color: "white",
          fontWeight: "600",
          padding: "10px",
          borderRadius: 4,
          border: "none",
          cursor: "pointer",
          fontSize: 15,
        }}>
          Sign in
        </button>
      </div>
    </div>
  );
}