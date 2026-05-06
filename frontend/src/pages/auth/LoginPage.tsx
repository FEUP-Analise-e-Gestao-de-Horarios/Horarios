import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { useLogin } from "@/api/hooks/useAuth";
import { ApiError } from "@/types/api";
import AuthPageLayout from "@/components/auth/AuthPageLayout";
import FormCard from "@/components/auth/FormCard";
import FormField from "@/components/auth/FormField";
import PasswordField from "@/components/auth/PasswordField";
import SubmitButton from "@/components/auth/SubmitButton";
import useShake from "@/components/auth/useShake";
import { ROUTES } from "@/routes";

type Field = "username" | "password";

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<Partial<Record<Field, string>>>({});

  const usernameRef = useRef<HTMLInputElement>(null);
  const passwordRef = useRef<HTMLInputElement>(null);

  const login = useLogin();
  const { shake, isShaking } = useShake<Field>();

  useEffect(() => {
    if (!login.isPending && login.isError) {
      passwordRef.current?.focus();
    }
  }, [login.isPending, login.isError]);

  const handleUsernameKeyDown = (e: React.KeyboardEvent) => {
    if (e.key !== "Enter") return;
    e.preventDefault();
    if (!username) {
      setErrors({ username: "Preencha este campo." });
      shake("username");
    } else {
      setErrors({});
      passwordRef.current?.focus();
    }
  };

  const handlePasswordKeyDown = (e: React.KeyboardEvent) => {
    if (e.key !== "Enter") return;
    e.preventDefault();
    passwordRef.current?.closest("form")?.requestSubmit();
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

    login.mutate(
      { username, password },
      {
        onSuccess: () => {
          window.location.href = ROUTES.HOME;
        },
        onError: (err) => {
          if (err.code === ApiError.AUTH_BAD_CREDENTIALS) {
            setErrors({ password: "Credenciais inválidas." });
          } else {
            setErrors({ password: "Ocorreu um erro. Tente novamente." });
          }
          shake("password");
        },
      },
    );
  };

  return (
    <AuthPageLayout>
      <title>Entrar · AGH</title>
      <FormCard onSubmit={handleSubmit}>
        <h1 className="text-[#08060d] text-2xl font-bold m-0">Iniciar Sessão</h1>

        <FormField
          ref={usernameRef}
          id="username"
          label="Nome de utilizador"
          placeholder="Nome de utilizador"
          value={username}
          onChange={setUsername}
          onKeyDown={handleUsernameKeyDown}
          error={errors.username}
          shake={isShaking("username")}
          disabled={login.isPending}
        />

        <PasswordField
          ref={passwordRef}
          id="password"
          label="Palavra-passe"
          value={password}
          onChange={setPassword}
          onKeyDown={handlePasswordKeyDown}
          error={errors.password}
          shake={isShaking("password")}
          disabled={login.isPending}
        />

        <Link
          to={ROUTES.FORGOT_PASSWORD}
          className="text-[#8c2d19] text-[13px] text-left hover:underline"
        >
          Esqueci-me da palavra-passe
        </Link>

        <SubmitButton loading={login.isPending} label="Entrar" loadingLabel="A entrar..." />
      </FormCard>
    </AuthPageLayout>
  );
}
