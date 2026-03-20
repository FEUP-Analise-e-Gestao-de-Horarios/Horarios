import { api } from "@/api/client";
import AuthPageLayout from "@/components/auth/AuthPageLayout";
import FormCard from "@/components/auth/FormCard";
import FormField from "@/components/auth/FormField";
import PasswordField from "@/components/auth/PasswordField";
import SubmitButton from "@/components/auth/SubmitButton";
import useShake from "@/components/auth/useShake";
import { ROUTES } from "@/routes";
import { useRef, useState } from "react";
import { Link } from "react-router-dom";

type Field = "username" | "password";

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<Partial<Record<Field, string>>>({});
  const [loading, setLoading] = useState(false);
  const { shake, isShaking } = useShake<Field>();
  const usernameRef = useRef<HTMLInputElement>(null);
  const passwordRef = useRef<HTMLInputElement>(null);

  const handleKeyDown = (field: Field) => (e: React.KeyboardEvent) => {
    if (e.key !== "Enter") return;
    e.preventDefault();
    if (field === "username") {
      if (!username) {
        setErrors({ username: "Preencha este campo." });
        shake("username");
      } else {
        setErrors({});
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
    <AuthPageLayout>
      <FormCard onSubmit={handleSubmit}>
        <h1 className="text-[#08060d] text-2xl font-bold m-0">Iniciar Sessão</h1>

        <FormField
          ref={usernameRef}
          id="username"
          label="Nome de utilizador"
          placeholder="Nome de utilizador"
          value={username}
          onChange={setUsername}
          onKeyDown={handleKeyDown("username")}
          error={errors.username}
          shake={isShaking("username")}
        />

        <PasswordField
          ref={passwordRef}
          id="password"
          label="Palavra-passe"
          value={password}
          onChange={setPassword}
          onKeyDown={handleKeyDown("password")}
          error={errors.password}
          shake={isShaking("password")}
        />

        <Link
          to={ROUTES.FORGOT_PASSWORD}
          className="text-[#8c2d19] text-[13px] text-left hover:underline"
        >
          Esqueci-me da palavra-passe
        </Link>

        <SubmitButton loading={loading} label="Entrar" loadingLabel="A entrar..." />
      </FormCard>
    </AuthPageLayout>
  );
}
