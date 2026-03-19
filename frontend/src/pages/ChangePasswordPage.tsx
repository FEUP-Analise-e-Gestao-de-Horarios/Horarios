export default function ChangePasswordPage() {
  return (
    <div
      style={{
        minHeight: "100vh",
        backgroundColor: "var(--bg)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "var(--sans)",
      }}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 16, width: 320 }}>
        <h1 style={{ color: "var(--text-h)", margin: 0 }}>Mudar palavra-passe</h1>

        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <label style={{ color: "var(--text)", fontSize: 14 }}>Palavra-passe antiga:</label>
          <input
            type="password"
            style={{
              padding: "10px 12px",
              borderRadius: 4,
              border: "1px solid var(--accent)",
              backgroundColor: "white",
              color: "var(--text-h)",
              outline: "none",
              fontSize: 15,
            }}
          />
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <label style={{ color: "var(--text)", fontSize: 14 }}>Palavra-passe nova:</label>
          <input
            type="password"
            style={{
              padding: "10px 12px",
              borderRadius: 4,
              border: "1px solid var(--accent)",
              backgroundColor: "white",
              color: "var(--text-h)",
              outline: "none",
              fontSize: 15,
            }}
          />
          <ul
            style={{
              color: "var(--text)",
              fontSize: 13,
              margin: 0,
              paddingLeft: 20,
              lineHeight: 1.8,
            }}
          >
            <li>A palavra-passe não pode ser muito semelhante às suas informações pessoais.</li>
            <li>A palavra-passe deve ter pelo menos 8 caracteres.</li>
            <li>A palavra-passe não pode ser uma palavra-passe muito comum.</li>
            <li>A palavra-passe não pode ser inteiramente numérica.</li>
          </ul>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <label style={{ color: "var(--text)", fontSize: 14 }}>
            Confirmação da palavra-passe nova:
          </label>
          <input
            type="password"
            style={{
              padding: "10px 12px",
              borderRadius: 4,
              border: "1px solid var(--accent)",
              backgroundColor: "white",
              color: "var(--text-h)",
              outline: "none",
              fontSize: 15,
              width: "100%",
              boxSizing: "border-box",
            }}
          />
        </div>

        <button
          style={{
            backgroundColor: "var(--accent)",
            color: "white",
            fontWeight: 600,
            padding: "10px",
            borderRadius: 4,
            border: "none",
            cursor: "pointer",
            fontSize: 15,
          }}
        >
          Guardar mudanças
        </button>
      </div>
    </div>
  );
}
