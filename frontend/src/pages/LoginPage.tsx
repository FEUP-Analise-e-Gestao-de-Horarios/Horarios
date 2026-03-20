import { api } from "@/api/client";
import { ROUTES } from "@/routes";
import { useRef, useState } from "react";
import { Link } from "react-router-dom";

type FieldErrors = {
  username?: string;
  password?: string;
};

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<FieldErrors>({});
  const [shakeField, setShakeField] = useState<keyof FieldErrors | null>(null);
  const [loading, setLoading] = useState(false);
  const usernameRef = useRef<HTMLInputElement>(null);
  const passwordRef = useRef<HTMLInputElement>(null);

  const shake = (field: keyof FieldErrors) => {
    setShakeField(field);
    setTimeout(() => setShakeField(null), 500);
  };

  const shakeClass = (field: keyof FieldErrors) => (shakeField === field ? "animate-shake" : "");

  const fieldClass = (field: keyof FieldErrors) =>
    `px-3 py-2 rounded border outline-none bg-[#f4f3ec] text-[#08060d] focus:border-[rgba(140,45,25,0.5)] focus:ring-1 focus:ring-[rgba(140,45,25,0.5)] placeholder:text-[#c5c1ca] ${
      errors[field] ? "border-[#8c2d19]" : "border-[#e5e4e7]"
    }`;

  const handleKeyDown = (field: "username" | "password") => (e: React.KeyboardEvent) => {
    if (e.key !== "Enter") return;
    e.preventDefault();
    if (field === "username") {
      if (!username) {
        setErrors({ username: "Preencha este campo." });
        shake("username");
      } else {
        setErrors((prev) => {
          const { username: _u, ...rest } = prev;
          void _u;
          return rest;
        });
        passwordRef.current?.focus();
      }
    } else {
      const form = passwordRef.current?.closest("form");
      form?.requestSubmit();
    }
  };

  const handleSubmit = (e: React.SyntheticEvent) => {
    e.preventDefault();
    setErrors({});

    if (!username) {
      setErrors({ username: "Preencha este campo." });
      shake("username");
      return;
    }

    if (!password) {
      setErrors({ password: "Preencha este campo." });
      shake("password");
      return;
    }

    setLoading(true);
    api
      .post("/api/auth/login", { username, password })
      .then(() => {
        window.location.href = ROUTES.HOME;
      })
      .catch(() => {
        setErrors({ password: "Credenciais inválidas." });
        shake("password");
      })
      .finally(() => {
        setLoading(false);
      });
  };

  return (
    <div className="min-h-svh bg-white flex items-center justify-center font-[system-ui,'Segoe_UI',Roboto,sans-serif] text-[#6b6375] text-lg leading-[145%] tracking-[0.18px] antialiased max-lg:text-base">
      <style>{`
        @keyframes shake {
          0%, 100% { transform: translateX(0); }
          20% { transform: translateX(-6px); }
          40% { transform: translateX(6px); }
          60% { transform: translateX(-4px); }
          80% { transform: translateX(4px); }
        }
        .animate-shake { animation: shake 0.4s ease-in-out; }
      `}</style>
      <form
        onSubmit={handleSubmit}
        className="flex flex-col gap-5 w-96 p-8 rounded-lg shadow-[rgba(0,0,0,0.1)_0_10px_15px_-3px,rgba(0,0,0,0.05)_0_4px_6px_-2px] border border-[#e5e4e7]"
      >
        <h1 className="text-[#08060d] text-2xl font-bold m-0">Iniciar Sessão</h1>

        <div className={`flex flex-col gap-1.5 ${shakeClass("username")}`}>
          <label htmlFor="username" className="text-sm text-[#6b6375]">
            Nome de utilizador
          </label>
          <input
            ref={usernameRef}
            id="username"
            type="text"
            placeholder="Nome de utilizador"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            onKeyDown={handleKeyDown("username")}
            className={fieldClass("username")}
          />
          {errors.username && <p className="text-[#8c2d19] text-[13px] m-0">{errors.username}</p>}
        </div>

        <div className={`flex flex-col gap-1.5 ${shakeClass("password")}`}>
          <label htmlFor="password" className="text-sm text-[#6b6375]">
            Palavra-passe
          </label>
          <input
            ref={passwordRef}
            id="password"
            type="password"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            onKeyDown={handleKeyDown("password")}
            className={fieldClass("password")}
          />
          {errors.password && <p className="text-[#8c2d19] text-[13px] m-0">{errors.password}</p>}
        </div>

        <Link
          to={ROUTES.FORGOT_PASSWORD}
          className="text-[#8c2d19] text-[13px] text-left hover:underline"
        >
          Esqueci-me da palavra-passe
        </Link>

        <button
          type="submit"
          disabled={loading}
          className="bg-[#8c2d19] text-white font-semibold py-2.5 rounded border-none cursor-pointer text-[15px] hover:bg-[#722415] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? "A entrar..." : "Entrar"}
        </button>
      </form>
    </div>
  );
}
