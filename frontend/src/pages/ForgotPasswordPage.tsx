import { api } from "@/api/client";
import { useState } from "react";
import { Link } from "react-router-dom";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = (e: React.SyntheticEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    api
      .post("/api/auth/forgot_password", { email })
      .then(() => {
        setSubmitted(true);
      })
      .catch(() => {
        setError("Ocorreu um erro. Tente novamente mais tarde.");
      })
      .finally(() => {
        setLoading(false);
      });
  };

  return (
    <div className="min-h-svh bg-white flex items-center justify-center font-[system-ui,'Segoe_UI',Roboto,sans-serif] text-[#6b6375] text-lg leading-[145%] tracking-[0.18px] antialiased max-lg:text-base">
      <div className="flex flex-col gap-5 w-96 p-8 rounded-lg shadow-[rgba(0,0,0,0.1)_0_10px_15px_-3px,rgba(0,0,0,0.05)_0_4px_6px_-2px] border border-[#e5e4e7]">
        <h1 className="text-[#08060d] text-2xl font-bold m-0">Recuperar palavra-passe</h1>

        {submitted ? (
          <>
            <p className="text-[#6b6375] text-sm leading-normal m-0">
              Se o e-mail introduzido estiver associado a uma conta, receberá uma mensagem com
              instruções para redefinir a sua palavra-passe.
            </p>
            <Link to="/login" className="text-[#8c2d19] text-sm font-semibold hover:underline">
              Voltar ao início de sessão
            </Link>
          </>
        ) : (
          <form onSubmit={handleSubmit} className="flex flex-col gap-5">
            <p className="text-[#6b6375] text-sm leading-normal m-0">
              Introduza o seu e-mail e enviaremos instruções para redefinir a sua palavra-passe.
            </p>

            <div className="flex flex-col gap-1.5">
              <label htmlFor="email" className="text-sm text-[#6b6375]">
                E-mail
              </label>
              <input
                id="email"
                type="email"
                required
                placeholder="exemplo@mail.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="px-3 py-2 rounded border border-[#e5e4e7] outline-none bg-[#f4f3ec] text-[#08060d] focus:border-[rgba(140,45,25,0.5)] focus:ring-1 focus:ring-[rgba(140,45,25,0.5)]"
              />
            </div>

            {error && (
              <p className="text-[#8c2d19] text-sm m-0 bg-[rgba(140,45,25,0.1)] px-3 py-2 rounded">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="bg-[#8c2d19] text-white font-semibold py-2.5 rounded border-none cursor-pointer text-[15px] hover:bg-[#722415] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? "A enviar..." : "Enviar e-mail"}
            </button>

            <Link to="/login" className="text-[#8c2d19] text-[13px] text-center hover:underline">
              Voltar ao início de sessão
            </Link>
          </form>
        )}
      </div>
    </div>
  );
}
