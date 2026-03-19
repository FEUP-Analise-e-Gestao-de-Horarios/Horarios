import { api } from "@/api/client";
import { useState } from "react";

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    api
      .post("/api/auth/login", { username, password })
      .then(() => {
        window.location.href = "/";
      })
      .catch(() => {
        setError("Credenciais inválidas.");
      })
      .finally(() => {
        setLoading(false);
      });
  };

  return (
    <div className="min-h-svh bg-white flex items-center justify-center font-[system-ui,'Segoe_UI',Roboto,sans-serif] text-[#6b6375] text-lg leading-[145%] tracking-[0.18px] antialiased max-lg:text-base">
      <form
        onSubmit={handleSubmit}
        className="flex flex-col gap-5 w-96 p-8 rounded-lg shadow-[rgba(0,0,0,0.1)_0_10px_15px_-3px,rgba(0,0,0,0.05)_0_4px_6px_-2px] border border-[#e5e4e7]"
      >
        <h1 className="text-[#08060d] text-2xl font-bold m-0">Sign In</h1>

        <div className="flex flex-col gap-1.5">
          <label htmlFor="username" className="text-sm text-[#6b6375]">
            Nome de utilizador
          </label>
          <input
            id="username"
            type="text"
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="px-3 py-2 rounded border border-[#e5e4e7] outline-none bg-[#f4f3ec] text-[#08060d] focus:border-[rgba(140,45,25,0.5)] focus:ring-1 focus:ring-[rgba(140,45,25,0.5)]"
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <label htmlFor="password" className="text-sm text-[#6b6375]">
            Palavra-passe
          </label>
          <input
            id="password"
            type="password"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="px-3 py-2 rounded border border-[#e5e4e7] outline-none bg-[#f4f3ec] text-[#08060d] focus:border-[rgba(140,45,25,0.5)] focus:ring-1 focus:ring-[rgba(140,45,25,0.5)]"
          />
        </div>

        <button
          type="button"
          className="text-[#8c2d19] text-[13px] text-left hover:underline cursor-pointer bg-transparent border-none p-0"
        >
          Esqueci-me da palavra-passe
        </button>

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
          {loading ? "A entrar..." : "Sign in"}
        </button>
      </form>
    </div>
  );
}
