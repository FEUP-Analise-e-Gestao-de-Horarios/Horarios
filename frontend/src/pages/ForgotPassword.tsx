export default function ForgotPassword() {
    return (
      <div style={{
        minHeight: "100vh",
        backgroundColor: "var(--bg)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "var(--sans)",
      }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 16, width: 300 }}>
          <h1 style={{ color: "var(--text-h)", margin: 0, lineHeight: "1"}}>
            Esqueci-me da palavra-passe
          </h1>
          <p style={{ color: "var(--text)", fontSize: 14, lineHeight: "1.5" }}>
            Coloque o seu e-mail na caixa abaixo, se o e-mail existir enviaremos um e-mail de confirmação.
          </p>
          <input
            type="email"
            placeholder="exemplo@mail.com"
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
            Enviar email
          </button>
        </div>
      </div>
    );
  }