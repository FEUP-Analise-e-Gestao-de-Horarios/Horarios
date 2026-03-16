export default function Login() {
  return (
    <div style={{
      minHeight: "100vh",
      backgroundColor: "#2b2b2b",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      fontFamily: "sans-serif",
    }}>
      <div style={{ display: "flex", flexDirection: "column", gap: 16, width: 280 }}>
        <h1 style={{ color: "white", fontSize: 32, fontWeight: "bold", margin: 0 }}>
          Sign In
        </h1>

        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <input
            type="text"
            placeholder="Username"
            style={{ padding: "8px 12px", borderRadius: 4, border: "none", outline: "none" }}
          />
          <span style={{ color: "d1d5db", fontSize: 13, display: "flex" }}>Nome de utilizador</span>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <input
            type="password"
            placeholder="••••••••"
            style={{ padding: "8px 12px", borderRadius: 4, border: "none", outline: "none" }}
          />
          <span style={{ color: "#d1d5db", fontSize: 13, display: "flex" }}>Palavra-passe</span>
        </div>

        <a href="#" style={{ color: "#60a5fa", fontSize: 13 }}>
          Esqueci-me da palavra-passe
        </a>

        <button style={{
          backgroundColor: "#facc15",
          color: "black",
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